import sys
import time
import os
from lvt.client.apa102 import APA102
from gpiozero import LED
from lvt.const import *
from lvt.client.config import Config
from lvt.client.animator import Animator

class APA102Animator(Animator):
    def __init__( this, config: Config, shared, nPixels: int ):
        Animator.__init__( this, config,shared )

        this.nPixels = nPixels

        # драйвер
        this.leds = APA102( num_led=this.nPixels )
        # Подать питание на плату:
        this.power = LED( 5 )
        this.power.on()


    def __del__( this ):
        print( 'disposing' )
        this.off()
        this.leds.cleanup()
        this.power.off()

    def awake( this, restart:bool ):
        """Wake up and listening"""
        if restart : 
            this.brightness = 100
            this.phase = 0
            this.timeout = 0.1
        elif this.phase == 0 :
            this.brightness *= 0.7
            if this.brightness < 10 : 
                this.brightness = 9
                this.phase = 1
                this.step = -1
            this.timeout = 0.02
        else:
            this.brightness += this.step 
            if this.step < 0 and this.brightness < 2 :
                this.brightness = 2
                this.step = -this.step
            elif this.step > 0 and this.brightness > 30 :
                this.brightness = 30
                this.step = -this.step
            this.timeout = 0.05

        #print( f'{this.phase} {this.brightness} {this.step}' )

        this.show( [255,255,255,this.brightness] * this.nPixels )

    def think( this, restart:bool ):
        """Thinking"""
        if restart : 
            for i in range( this.nPixels ):
                this.leds.set_pixel_rgb( i, this.leds.wheel( int(i*255/this.nPixels) ) )
            this.leds.show()
        else:
            this.leds.rotate(-1)
            this.leds.show()
        this.timeout = 0.1

    def accept( this, restart:bool ):
        """Accepted"""
        if restart : 
            this.brightness = 100
            this.timeout = 0.05
        else:
            this.brightness = this.brightness * 0.5
            this.timeout = 0.02
            if this.brightness < 2 :
                this.brightness = 0
                this.animation = ANIMATION_NONE

        this.show( [0,255,0,this.brightness] * this.nPixels )

    def cancel( this, restart:bool ):
        """Cancelled / Ignoring"""
        if restart : 
            this.brightness = 100
            this.timeout = 0.1
        else:
            this.brightness = this.brightness * 0.5
            this.timeout = 0.02
            if this.brightness < 2 :
                this.brightness = 0
                this.animation = ANIMATION_NONE

        this.show( [255,0,0,this.brightness] * this.nPixels )

    def none( this, restart:bool ):
        """Standup animation"""
        this.show( [0,0,0,0] * this.nPixels )
        this.timeout = 0.3
    

    def show( this, pixels ):
        for i in range( this.nPixels ):
            this.leds.set_pixel( i, \
                  int( pixels[4 * i + 0] ), \
                  int( pixels[4 * i + 1] ), \
                  int( pixels[4 * i + 2] ), \
                  int( pixels[4 * i + 3] ) )

        this.leds.show()

