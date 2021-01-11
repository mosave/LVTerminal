import sys
import time
import os
import pyaudio
import audioop
import webrtcvad
import numpy as np
from lvt.const import *
from lvt.logger import *
# Допустимые значения - 10, 20 или 30 мс
VAD_FRAME = 20 # ms
# Обрабатываем звук полусекундными интервалами
CHUNKS_PER_SECOND = 2

config = None

class Microphone:
    def initialize( gConfig ):
        global config
        config = gConfig

    def __init__( this ):
        this._rms = [50]*16
        this.channel = 0
        this._noiseLevel = [1000]*16

        this.vad = webrtcvad.Vad(config.vadSelectivity)
        this.buffer = []
        this._muted = False
        this.ignoreFirstFrame = False
        this._active = False
        this.audioStream = None
        this.channels = 1

        # Init audio subsystem
        this.audio = pyaudio.PyAudio()
        this.sampleSize = this.audio.get_sample_size( pyaudio.paInt16 )
        this.framesPerChunk = int( config.sampleRate / CHUNKS_PER_SECOND)
        try: this.channels = this.audio.get_device_info_by_index( config.audioInputDevice ).get( "maxInputChannels" )
        except: this.channels = 1

        # Округляем количество каналов
        if this.channels>8 :
            this.channels = 8
        elif this.channels > 6:
            this.channels = 6
        elif this.channels > 4:
            this.channels = 4
        
        #chunkSize = int( this.framesPerChunk * this.sampleSize * this.channels )

        # Открываем аудиопоток, читаем его полусекундными кусками
        this.audioStream = this.audio.open( 
            format = pyaudio.paInt16, 
            channels = this.channels,
            rate = config.sampleRate,
            input = True,
            output = False,
            input_device_index=config.audioInputDevice,
            frames_per_buffer = this.framesPerChunk,
            stream_callback=this._callback,
        )

    def __enter__(this):
        return this

    def __exit__(this, exc_type, exc_value, traceback):

        if this.audioStream != None:
            try: this.audioStream.close()
            except:pass
            this.audioStream = None

        if this.audio != None:
            try: this.audio.terminate() 
            except:pass
            this.audio = None

        if this.vad != None:
            try: del(this.vad)
            except:pass
            this.vad = None


    @property
    def muted(this)->bool:
        return this._muted

    @muted.setter
    def muted(this, mute ) :
        this._muted = mute
        if mute : this.ignoreFirstFrame = True

    @property
    def rms(this)->int:
        return this._rms[this.channel]

    @property 
    def noiseLevel(this)->int:
        return this._noiseLevel[this.channel]

    @property 
    def noiseThreshold(this)->int:
        return config.noiseThreshold

    @property
    def triggerLevel(this)->int :
        return this._noiseLevel[this.channel] + this.noiseThreshold

    @property
    def active(this)->bool:
        return this._active

    @active.setter
    def active(this, newValue):
        if( this._active and not newValue) : this.buffer.clear()
        this._active = newValue

    def _callback( this, data, frame_count, time_info, status):
        # Если микрофон выключен - ничего не делаем
        if this.muted :
            return None, pyaudio.paContinue
        # А еще игнорируем первый фрейм после unmute:
        if this.ignoreFirstFrame :
            this.ignoreFirstFrame = False
            return None, pyaudio.paContinue

        # Контролируем размер буфера. В режиме ожидания 1с, в активном режиме 5с
        maxBufferSize = int(CHUNKS_PER_SECOND*10 if this.active else CHUNKS_PER_SECOND*2)

        while len(this.buffer)>maxBufferSize : this.buffer.pop(0)

        # Конвертим аудио в массив 16битных значений:
        data = np.fromstring( data, dtype='int16')

        # Раскидаем данные по каналам, преобразуя их обратно в поток байтов
        rmsTarget = 1500
        rmsDelta = 999999
        rmsChannel = 0
        channels = [0]*this.channels
        this._rms = [0]*this.channels
        for ch in range(this.channels):
            channels[ch] = data[ch::this.channels].tobytes()
            this._rms[ch] = audioop.rms( channels[ch], this.sampleSize )

            delta = abs( this._rms[ch] - rmsTarget )
            if delta < rmsDelta:
                rmsDelta = delta
                rmsChannel = ch

        this.buffer.append( channels )

        if not this.active :
            for ch in range(this.channels) :
                if this._rms[ch] + this.noiseThreshold < this._noiseLevel[ch] :
                    this._noiseLevel[ch] = this._rms[ch] + int( this.noiseThreshold / 4 )

            if isinstance( config.channelSelection, int ) :
                this.channel = config.channelSelection if config.channelSelection<this.channels else 0
            elif config.channelSelection == "rms" :
                this.channel = rmsChannel


            vadFrameSize = int(config.sampleRate*this.sampleSize/1000 * VAD_FRAME)
            p = 0
            voiceFrames = 0
            totalFrames = 0
            while p+vadFrameSize <= len(channels[this.channel]):
                totalFrames += 1
                if this.vad.is_speech( channels[this.channel][p:p+vadFrameSize], config.sampleRate ): voiceFrames += 1
                p += vadFrameSize

            isVoice = (totalFrames>0) and ((voiceFrames*100/totalFrames)>=config.vadConfidence)

            if isVoice and (this.rms > this.triggerLevel) :
                this.active = True
        else:
            for ch in range(this.channels) :
                if this._rms[ch] + this.noiseThreshold > this._noiseLevel[ch] :
                    this._noiseLevel[ch] = this._rms[ch]

        return None, pyaudio.paContinue

    def read(this, wait: bool = False):
        n = 0
        # Немного подождем если в буфере нет данных
        while wait and len( this.buffer ) <= 0 and n <= 3 :
            time.sleep( 1 / CHUNKS_PER_SECOND / 3 )
            n += 1

        # Если в буфере есть данные - возвращаем их
        if len( this.buffer ) > 0: 
            data = this.buffer[0][this.channel]
            this.buffer.pop( 0 )
            return data
        else:
            return None

