import sys
import time
import os
import pyaudio
import audioop
from lvt.const import *

config = None

class SoundEstimator:
    def setConfig( gConfig ):
        global config
        config = gConfig

    def __init__( this, sampleSize ):
        this.sampleSize = sampleSize
        this.rms = 50
        this.noiseLevel = 1000
        this.noiseThreshold = config.noiseThreshold
        this.triggerLevel = this.noiseLevel + this.noiseThreshold
        pass
    def estimate( this, waveData, isActive:bool ) -> bool:
        this.rms = audioop.rms( waveData, this.sampleSize )

        if this.rms + this.noiseThreshold < this.noiseLevel :
            this.noiseLevel = this.rms + ( this.noiseThreshold / 2 )

        this.triggerLevel = this.noiseLevel + this.noiseThreshold

        return ( this.rms > this.triggerLevel )
            

