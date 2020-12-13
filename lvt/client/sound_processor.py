import sys
import time
import os
import pyaudio
import audioop
import webrtcvad
import numpy as np
from lvt.const import *
# Допустимые значения - 10, 20 или 30 мс
VAD_FRAME = 20 # ms
config = None

class SoundProcessor:
    def setConfig( gConfig ):
        global config
        config = gConfig

    def __init__( this ):
        this.rms = 50
        this.noiseLevel = 1000
        this.noiseThreshold = config.noiseThreshold
        this.triggerLevel = this.noiseLevel + this.noiseThreshold

        this.vad = webrtcvad.Vad(config.vadSelectivity)

        # Init audio subsystem
        this.audio = pyaudio.PyAudio()
        this.sampleSize = this.audio.get_sample_size( pyaudio.paInt16 )
        try:
            this.channels = this.audio.get_device_info_by_index( config.audioInputDevice ).get( "maxInputChannels" )
        except:
            this.channels = 1


        # Округляем количество каналов
        if this.channels>8 :
            this.channels = 8
        elif this.channels > 6:
            this.channels = 6
        elif this.channels > 4:
            this.channels = 4
        
        # Размер буффера, Читаем по полсекунды:
        this.framesPerBuffer = int( config.sampleRate / 2)
        this.bufferSize = int( this.framesPerBuffer * this.sampleSize * this.channels )

        # Открываем аудиопоток, читаем его полусекундными кусками
        this.audioStream = this.audio.open( 
            format = pyaudio.paInt16, 
            channels = this.channels,
            rate = config.sampleRate,
            input = True,
            output = False,
            input_device_index=config.audioInputDevice,
            frames_per_buffer = this.framesPerBuffer )

        this.outputBuffer = []
        this._isMuted = False
        this._isActive = False

    def __del__(this):
        if this.audioStream != None:
            try: this.audioStream.close()
            except: pass
            this.audioStream = None

        if this.audio != None:
            try: this.audio.terminate() 
            except: pass
            this.audio = None

        if this.vad != None:
            try: del(this.vad)
            except: pass
            this.vad = None

    @property
    def isMuted(this)->bool:
        return this._isMuted

    @isMuted.setter
    def isMuted(this, mute ) :
        this._isMuted = mute
        if mute : this.outputBuffer = []

    @property
    def isActive(this)->bool:
        return this._isActive

    @isActive.setter
    def isActive(this, active):
        if not active and this._isActive:
            # Перезапускаем процедуру определения уровня шума
            this.noiseLevel = 5000
        this._isActive = active

    def process( this  ):
        # Читаем аудио и конвертим их в массив 16битных значений:
        data = np.fromstring( this.audioStream.read( this.framesPerBuffer ), dtype='int16')
        if len(data)<=0 : return

        # Раскидаем данные по каналам, преобразуя их обратно в поток байтов
        rms = 0
        rmsMax = 0
        rmsMaxI = 0
        channel = 0
        channels = [0]*this.channels
        channelRms = [0]*this.channels
        for ch in range(this.channels):
            channels[ch] = data[ch::this.channels].tobytes()
            r = audioop.rms( channels[ch], this.sampleSize )
            if r > rmsMax:
                rmsMax = r
                channel = ch
            channelRms[ch] = r
            rms += r

        this.rms = int(rms / this.channels)
        if isinstance( config.channelSelection, int ) :
            channel = config.channelSelection if config.channelSelection<this.channels else 0
        elif config.channelSelection == "avg" :
            channel = 0

        while len( this.outputBuffer ) > 3 : 
            this.outputBuffer.pop( 0 )

        this.outputBuffer.append( channels[channel] )

        if this.isActive :
            if this.rms + this.noiseThreshold > this.noiseLevel :
                this.noiseLevel = this.rms - this.noiseThreshold
        else:
            if this.rms + this.noiseThreshold < this.noiseLevel :
                this.noiseLevel = this.rms + int( this.noiseThreshold / 4 )

        this.triggerLevel = this.noiseLevel + this.noiseThreshold

        vadFrameSize = int(config.sampleRate*this.sampleSize/1000 * VAD_FRAME)
        p = 0
        voiceFrames = 0
        totalFrames = 0
        while p+vadFrameSize <= len(channels[channel]):
            totalFrames += 1
            if this.vad.is_speech( channels[channel][p:p+vadFrameSize], config.sampleRate ): voiceFrames += 1
            p += vadFrameSize

        isVoice = (totalFrames>0) and ((voiceFrames*100/totalFrames)>=config.vadConfidence)

        if isVoice and (this.rms > this.triggerLevel) :
            this.isActive = True

    def read(this):
        if len( this.outputBuffer ) <= 0: 
            this.process()

        if len( this.outputBuffer ) > 0: 
            data = this.outputBuffer[0]
            this.outputBuffer.pop( 0 )
            return data
        else:
            return None

