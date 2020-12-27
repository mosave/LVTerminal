import sys
import time
import os
from lvt.client.apa102 import APA102
from gpiozero import LED
from lvt.const import *
from lvt.client.config import Config
from lvt.client.animator import Animator

class APA102Animator(Animator):

    def __init__( this, config: Config, shared ):
        Animator.__init__( this, config, shared )

        if config.apa102LedCount<1 or config.apa102LedCount>=127 :
            raise Exception("Invalid number of APA102 LEDs specified")
        this.nPixels = config.apa102LedCount
        this.muteLeds = config.apa102MuteLeds
        # драйвер
        this.leds = APA102( num_led=this.nPixels )
        # Подать питание на плату:
        this.power = LED( 5 )
        this.power.on()


    def __del__( this ):
        this.off()
        try: this.power.off()
        except:pass
        try: this.leds.cleanup()
        except:pass


    def animationAwake( this, restart:bool ):
        """Wake up and listening"""

        if restart : 
            this.brAwake = 100
            this.phaseAwake = 0
            this.timeout = 0.1
            locked = True
        elif this.phaseAwake == 0 :
            this.brAwake *= 0.7
            if this.brAwake < 10 : 
                this.brAwake = 9
                this.phaseAwake = 1
                this.stepAwake = -1
            this.timeout = 0.02
            locked = True
        else:
            this.brAwake += this.stepAwake 
            if this.stepAwake < 0 and this.brAwake < 2 :
                this.brAwake = 2
                this.stepAwake = -this.stepAwake
            elif this.stepAwake > 0 and this.brAwake > 30 :
                this.brAwake = 30
                this.stepAwake = -this.stepAwake
            this.timeout = 0.05
            locked = False


        this.show( [255,255,255,this.brAwake] * this.nPixels )
        return locked

    def animationThink( this, restart:bool ):
        """Thinking"""
        if restart : 
            this.pxThink = []
            for i in range( this.nPixels ):
                this.pxThink.append( this.leds.wheel( int(i*255/this.nPixels) ) )
        else:
            this.pxThink.append(this.pxThink[0])
            this.pxThink.pop(0)

        this.timeout = 0.1
        this.showRGB( this.pxThink )
        return False

    def animationAccept( this, restart:bool ):
        """Accepted"""
        if restart : 
            this.brAccept = 100
            this.timeout = 0.1
        else:
            this.brAccept = this.brAccept * 0.5
            this.timeout = 0.02
            if this.brAccept < 2 :
                this.brAccept = 0
                this.animation = ANIMATION_NONE
                this.timeout = 0.5

        this.show( [0,255,0,this.brAccept] * this.nPixels )
        return (this.brAccept>0)

    def animationCancel( this, restart:bool ):
        """Cancelled / Ignoring"""
        if restart : 
            this.brCancel = 100
            this.timeout = 0.1
        else:
            this.brCancel = this.brCancel * 0.5
            this.timeout = 0.02
            if this.brCancel < 2 :
                this.brCancel = 0
                this.animation = ANIMATION_NONE
                this.timeout = 0.5

        this.show( [255,0,0,this.brCancel] * this.nPixels )
        return (this.brCancel>0)

    def animationNone( this, restart:bool ):
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

        if this.muted :
            for i in this.muteLeds:
                this.leds.set_pixel( i, 0,0,255, 100 )

        this.leds.show()

    def showRGB( this, pixels ):
        for i in range( this.nPixels ):
            this.leds.set_pixel_rgb( i, pixels[i] )

        if this.muted :
            for i in this.muteLeds:
                this.leds.set_pixel( i, 0,0,255, 100 )

        this.leds.show()

