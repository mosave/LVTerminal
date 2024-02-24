import time
import pyaudio
import audioop
import webrtcvad
import numpy
from lvt.const import *
from lvt.logger import *
import lvt.client.config as config

# Допустимые значения - 10, 20 или 30 мс
VAD_FRAME = 30 # ms
# Обрабатываем звук полусекундными интервалами
CHUNKS_PER_SECOND = 2

# Параметры эхоподавления sppedxdsp 

AEC_BLOCKSIZE = 256
AEC_BUFFERSIZE = 2048

# Создаем SpeexDSP Echo Canceller (если соответствующая библиотека доступна)
try:
    from speexdsp import EchoCanceller
    echoCanceller = EchoCanceller.create( AEC_BLOCKSIZE, AEC_BUFFERSIZE, VOICE_SAMPLING_RATE )
except:
    echoCanceller = None
    pass



audio = None

class Microphone:
    global echoCanceller
    aecAvailable = echoCanceller is not None

    def __init__( self ):
        global audio

        self.__rms = 50
        self.__maxpp = 1000
        self.channel = 0
        self.__noiseLevel = 1000
        self.__tmLastFrame = time.time()
        self.dbgInfo = ""

        self.vad = webrtcvad.Vad(config.vadSelectivity)
        self.buffer = []
        self.__muted = False
        self.voiceVolume = 100
        self.playerVolume = 100
        self.ignoreFirstFrame = False
        self.__active = False
        self.__lastSpeak = 0
        self.__lastPlay = 0
        self.audioStream = None
        self.vadLevel = 0
        self.__ratecvState = None


        # Init audio subsystem
        self.sampleSize = audio.get_sample_size( pyaudio.paInt16 )
        deviceInfo = audio.get_device_info_by_index( config.audioInputDevice )

        try: self.channels = int(deviceInfo.get( "maxInputChannels" ))
        except: self.channels = config.channels

        if self.channels>config.channels: self.channels = config.channels 

        try: self.sampleRate = int(deviceInfo.get( "defaultSampleRate" ))
        except: self.sampleRate = VOICE_SAMPLING_RATE

        #print(f"Device sample rate={self.sampleRate}")

        self.inputFramesPerChunk = int( self.sampleRate / CHUNKS_PER_SECOND)
        self.framesPerChunk = int( VOICE_SAMPLING_RATE / CHUNKS_PER_SECOND)

            
        #chunkSize = int( self.framesPerChunk * self.sampleSize * self.channels )
        #print(f"Channels={self.channels}, rate={VOICE_SAMPLING_RATE} ")
        # Открываем аудиопоток, читаем его полусекундными кусками
        self.audioStream = audio.open( 
            format = pyaudio.paInt16, 
            channels = self.channels,
            rate = self.sampleRate,
            input = True,
            output = False,
            input_device_index=config.audioInputDevice,
            frames_per_buffer = self.inputFramesPerChunk,
            stream_callback=self._callback,
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):

        if self.audioStream is not None:
            try: self.audioStream.close()
            except:pass
            self.audioStream = None

        if self.vad is not None:
            try: del(self.vad)
            except:pass
            self.vad = None

    @property
    def muted(self)->bool:
        return self.__muted

    @muted.setter
    def muted(self, mute ) :
        if self.__muted != mute:
            self.__muted = mute
            if mute : 
                self.ignoreFirstFrame = True
            self.buffer.clear()

    @property
    def rms(self)->int:
        return self.__rms

    @property
    def maxpp(self)->int:
        return self.__maxpp

    @property 
    def noiseLevel(self)->int:
        return self.__noiseLevel

    @property
    def triggerLevel(self)->int :
        return self.__noiseLevel + config.noiseThreshold

    @property
    def active(self)->bool:
        return self.__active

    @active.setter
    def active(self, newValue):
        if not newValue : self.buffer.clear()
        self.__active = newValue

    @property
    def alive(self)->bool:
        return time.time() - self.__tmLastFrame < 5

    @property
    def speaking(self)->bool:
        return (time.time() - self.__lastSpeak < 1) and (config.volumeControlVoice is None or (self.voiceVolume != 0 ))

    @property
    def playing(self)->bool:
        return (time.time() - self.__lastPlay < 1) and (config.volumeControlPlayer is None or (self.playerVolume !=0 ))

    def _callback( self, data, frame_count, time_info, status):
        global echoCanceller
        global AEC_BLOCKSIZE
        global AEC_BUFFERSIZE

        self.__tmLastFrame = time.time()
        # print( '0' )

        if status:
            print( f'STATUS FLAGS: {status} ')
            return None, pyaudio.paContinue
        
        if self.sampleRate != VOICE_SAMPLING_RATE:
            data, self.__ratecvState = audioop.ratecv( data, 2, self.channels, self.sampleRate, VOICE_SAMPLING_RATE, self.__ratecvState )

        data = numpy.frombuffer( data, dtype='int16')

        # Если микрофон замьючен - ничего не делаем
        if self.muted :
            self.buffer.clear()
            self.ignoreFirstFrame = True
            return None, pyaudio.paContinue
        
        # А еще игнорируем первый фрейм после unmute:
        if self.ignoreFirstFrame :
            self.ignoreFirstFrame = False
            return None, pyaudio.paContinue

        # Контролируем размер буфера. В режиме ожидания 1с, в активном режиме 3с
        maxBufferSize = int(CHUNKS_PER_SECOND * (3 if self.active else 1) )

        while len(self.buffer)>maxBufferSize : 
            self.buffer.pop(0)
        # print( '1' )

        # Раскидываем на каналы
        channels = [0]*self.channels
        for ch in range(self.channels):
            channels[ch] = data[ch::self.channels].tobytes()
            #print(numpy.fromstring(channels[ch], dtype='int16'))


        # Наибольший RMS, но без искажений
        if config.micSelection == "rms":
            # Выбираем лучший канал только в режиме ожидания:
            if not self.active:
                chBest = -1
                rmsBest = 0
                chGood = -1
                rmsGood = 100000

                for ch in config.microphones:
                    __rms = audioop.rms( channels[ch], self.sampleSize )
                    __maxpp = audioop.maxpp( channels[ch], self.sampleSize )

                    if (__rms>rmsBest) and (__rms<30000) and (__maxpp<31000) :
                        rmsBest = __rms
                        chBest = ch
                    if (chGood<0) or (__rms < rmsGood) :
                        rmsGood = __rms
                        rmsBest = __maxpp
                        chGood = ch

                if chBest>=0:
                    self.channel = chBest
                    self.__rms = rmsBest
                else:
                    self.channel = chGood
                    self.__rms = rmsGood

                data = channels[self.channel]
            else:
                # В активном режиме по каналам не прыгаем, используем последний выбранный 
                data = channels[self.channel]
                self.__rms = audioop.rms( data, self.sampleSize )

        # "Среднее по микрофонным каналам":
        else:
            self.channel = "AVG"
            factor = 1.0 / len(config.microphones)
            data = None
            for ch in config.microphones :
                if data is None :
                    data = audioop.mul( channels[ch], 2, factor )
                else :
                    data = audioop.add( data, audioop.mul( channels[ch], 2, factor ), 2 )

            self.__rms = audioop.rms( data, self.sampleSize )

        # print( '2' )

        loopbackData = None
        fVoice = 0
        fPlayer = 0

        if config.loopbackVoice>=0 and audioop.rms( channels[config.loopbackVoice], self.sampleSize ) > 100:
            self.__lastSpeak = time.time()
            fVoice = self.voiceVolume

        if config.loopbackPlayer>=0 and audioop.rms( channels[config.loopbackPlayer], self.sampleSize ) > 100:
            self.__lastPlay = time.time()
            fPlayer = self.playerVolume

        if fVoice + fPlayer > 5 and echoCanceller is not None:
            if fVoice > 0:
                loopbackData = audioop.mul( channels[config.loopbackVoice], 2, fVoice / (fVoice + fPlayer) )
            if fPlayer:
                ldPlayer = audioop.mul( channels[config.loopbackPlayer], 2, fPlayer / (fVoice + fPlayer) )
                loopbackData = ldPlayer if loopbackData is None else audioop.add( loopbackData, ldPlayer, 2 )
            

        if self.speaking:
            # Всегда игнорируем микрофонный вход если озвучивается голосовое сообщение.
            # 
            self.__rms = 0
            self.vadLevel = 0
            self.buffer.clear()
            self.ignoreFirstFrame = True
            return None, pyaudio.paContinue

        if self.playing:
            # Без эхоподавления звук на колонке перегружает микрофоны, ухудшая качество распознавания голоса.
            # Поэтому если эходав отсутствует - будем игнорировать микрофон во время проигрывания звука
            if echoCanceller is None:
                self.__rms = 0
                self.vadLevel = 0
                self.buffer.clear()
                self.ignoreFirstFrame = True
                return None, pyaudio.paContinue

            # loopbackData = None
            # И наконец - если на колонку выводится звук - вычтем его из микрофонного входа:
            if loopbackData is not None:
                filtered = bytearray()
                blockSize = AEC_BLOCKSIZE*2
                p = 0
                while p<len(data):
                    if p+blockSize >= len(data): blockSize = len(data) - p
                    filtered += bytearray( echoCanceller.process( data[p:p+blockSize], loopbackData[p:p+blockSize ] ) )[:blockSize]
                    p += blockSize

                # print( f' {len(filtered)} / { len(data)} bytes  ')
                data = bytes(filtered)
                self.__rms = audioop.rms( data, self.sampleSize )

        # print( '3' )
        #print(f"Final data: channel={self.channel}, rms={self.rms} ")
        #print(numpy.fromstring(data, dtype='int16'))

        if not self.active:
            self.__maxpp = audioop.maxpp( data, 2 )

            # Если уровень звука "немного меньше" фонового шума - снизить значение порогового шума
            if self.__rms + config.noiseThreshold < self.__noiseLevel:
                self.__noiseLevel = self.__rms + int( config.noiseThreshold / 4 )

            # Посчитать VAD index (self.vadLevel)
            vadFrameSize = int(VOICE_SAMPLING_RATE*self.sampleSize/1000 * VAD_FRAME)
            p = 0
            voiceFrames = 0
            totalFrames = 0
            while p+vadFrameSize <= len(data):
                totalFrames += 1
                if self.vad.is_speech( data[p:p+vadFrameSize], VOICE_SAMPLING_RATE ): voiceFrames += 1
                p += vadFrameSize

            self.vadLevel = int(voiceFrames*100/totalFrames)

            isVoice = (totalFrames>0) and (self.vadLevel>=config.vadConfidence)

            if isVoice and (self.rms > self.triggerLevel):
                self.active = True
        else:
            if self.__rms + config.noiseThreshold > self.__noiseLevel :
                self.__noiseLevel = self.__rms


        # print( '4' )
        
        # Сохранить фрагмент в буфере:
        self.buffer.append( data )

        # self.dbgInfo =  f'{int((time.time()-tmStart)*1000)}ms, {audioop.maxpp(data,self.sampleSize) }'

        return None, pyaudio.paContinue

    def read(self, wait: bool = False):
        # Если в буфере есть данные - возвращаем их
        if len( self.buffer ) > 0: 
            data = self.buffer[0]
            self.buffer.pop( 0 )
            if self.maxpp < 15000:
                data = audioop.mul( data, 2, 15000/self.maxpp  )
            return data
        else:
            return None

    def init( gAudio ):
        global audio
        audio = gAudio
