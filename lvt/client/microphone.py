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
# "идеальное" значение громкости в алгоритме выбора канала "rms"

audio = None

class Microphone:
    def __init__( self ):
        global audio

        self.__rms = 50
        self.__maxpp = 50
        self.channel = 0
        self.__noiseLevel = 1000

        self.vad = webrtcvad.Vad(config.vadSelectivity)
        self.buffer = []
        self.__muted = False
        self.ignoreFirstFrame = False
        self.__active = False
        self.audioStream = None
        self.channels = config.channels
        self.vadLevel = 0
        self.__ratecvState = None

        # Init audio subsystem
        self.sampleSize = audio.get_sample_size( pyaudio.paInt16 )
        deviceInfo = audio.get_device_info_by_index( config.audioInputDevice )

        try: self.channels = int(deviceInfo.get( "maxInputChannels" ))
        except: self.channels = 128

        try: self.sampleRate = int(deviceInfo.get( "defaultSampleRate" ))
        except: self.sampleRate = VOICE_SAMPLING_RATE

        #print(f"Device sample rate={self.sampleRate}")

        self.inputFramesPerChunk = int( self.sampleRate / CHUNKS_PER_SECOND)
        self.framesPerChunk = int( VOICE_SAMPLING_RATE / CHUNKS_PER_SECOND)
        if self.channels>config.channels: self.channels = config.channels 

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

        if self.audioStream != None:
            try: self.audioStream.close()
            except:pass
            self.audioStream = None

        if self.vad != None:
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

    def _callback( self, data, frame_count, time_info, status):
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

        data = numpy.fromstring( data, dtype='int16')

        if self.sampleRate != VOICE_SAMPLING_RATE:
            data, self.__ratecvState = audioop.ratecv( data.tobytes(), 2, self.channels, self.sampleRate, VOICE_SAMPLING_RATE, self.__ratecvState )
            data = numpy.fromstring( data, dtype='int16')

        #print(f"channels:")

        # Раскидываем на каналы
        channels = [0]*self.channels
        for ch in range(self.channels):
            channels[ch] = data[ch::self.channels].tobytes()
            #print(numpy.fromstring(channels[ch], dtype='int16'))


        # "Оптимальный уровень громкости"
        if config.micSelection == "rms":

            # Вариант 2: "наибольший RMS, но без искажений".
            chBest = -1
            rmsBest = 0
            maxBest = 0
            chGood = -1
            rmsGood = 100000
            maxGood = 0

            for ch in config.microphones:
                __rms = audioop.rms( channels[ch], self.sampleSize )
                __maxpp = audioop.maxpp( channels[ch], self.sampleSize )

                if (__rms>rmsBest) and (__rms<5000) and (__maxpp<64000) :
                    rmsBest = __rms
                    maxBest = __maxpp
                    chBest = ch
                if (chGood<0) or (__rms < rmsGood) :
                    rmsGood = __rms
                    rmsBest = __maxpp
                    chGood = ch

            #print(f'rms:[{__rms[0]},{__rms[1]}], maxpp:[{__maxpp[0]},{__maxpp[1]}], rmsBest={rmsBest}({chBest}), rmsGood={rmsGood}({chGood})')
            #print(f'rmsBest={rmsBest}({chBest}), rmsGood={rmsGood}({chGood})')
            if chBest>=0:
                self.channel = chBest
                self.__rms = rmsBest
                self.__maxpp = maxBest
            else:
                self.channel = chGood
                self.__rms = rmsGood
                self.__maxpp = maxGood

            data = channels[self.channel]

        # "Среднее по микрофонным каналам":
        else :
            self.channel = "avg"
            factor = 1.0 / len(config.microphones)
            #print(f'factor={factor} ')
            data = None
            for ch in config.microphones :
                if data==None :
                    data = audioop.mul( channels[ch], 2, factor )
                else :
                    data = audioop.add( data, audioop.mul( channels[ch], 2, factor ), 2 )

            self.__rms = audioop.rms( data, self.sampleSize )
            self.__maxpp = audioop.maxpp( data, self.sampleSize )

        #print(f"Final data: channel={self.channel}, rms={self.rms}, maxpp={self.maxpp} ")
        #print(numpy.fromstring(data, dtype='int16'))

        # Сохранить фрагмент в буфере:
        self.buffer.append( data )

        if not self.active:
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

        return None, pyaudio.paContinue

    def read(self, wait: bool = False):
        n = 0
        # Немного подождем если в буфере нет данных
        while wait and len( self.buffer ) <= 0 and n <= 3 :
            time.sleep( (1 / CHUNKS_PER_SECOND) / 2 )
            n += 1

        # Если в буфере есть данные - возвращаем их
        if len( self.buffer ) > 0: 
            data = self.buffer[0]
            self.buffer.pop( 0 )
            return data
        else:
            return None

    def init( gAudio ):
        global audio
        audio = gAudio
