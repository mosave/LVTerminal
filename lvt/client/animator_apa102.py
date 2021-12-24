import sys
import time
import os
from lvt.client.apa102 import APA102
from gpiozero import LED
from lvt.const import *
from lvt.client.animator import Animator
import lvt.client.config as config

class APA102Animator(Animator):
    def __init__( self, shared ):

        self.shared = shared
        self.nPixels = config.apa102LedCount
        self.muteLeds = config.apa102MuteLeds
        self.leds = APA102( self.nPixels )

        # Подать питание на плату:
        self.power = LED( 5 )
        self.power.on()
        Animator.__init__( self, shared )

    def __del__( self ):
        try: self.off()
        except:pass
        try: self.power.off()
        except:pass
        try: self.leds.cleanup()
        except:pass


    def animationAwake( self, restart:bool ):
        """Wake up and listening"""

        if restart : 
            self.brAwake = 2
            self.stepAwake = 2
            self.timeout = 0.3
        else:
            self.brAwake += self.stepAwake 
            if self.stepAwake < 0 and self.brAwake < 2 :
                self.brAwake = 2
                self.stepAwake = -self.stepAwake
                self.timeout = 0.5
            elif self.stepAwake > 0 and self.brAwake > 40 :
                self.brAwake = 30
                self.stepAwake = -self.stepAwake
                self.timeout = 0.05
            else:
                self.timeout = 0.05


        self.show( [255,255,255,self.brAwake] * self.nPixels )
        return False

    def animationThink( self, restart:bool ):
        """Thinking"""
        if restart : 
            self.pxThink = []
            for i in range( self.nPixels ):
                self.pxThink.append( self.leds.wheel( int(i*255/self.nPixels) ) )
        else:
            self.pxThink.append(self.pxThink[0])
            self.pxThink.pop(0)

        self.timeout = 1.5/self.nPixels
        self.showRGB( self.pxThink )
        return False

    def animationAccept( self, restart:bool ):
        """Accepted"""
        if restart : 
            self.brAccept = 100
            self.timeout = 0.5
        else:
            self.brAccept = self.brAccept * 0.5
            self.timeout = 0.1
            if self.brAccept < 2 :
                self.brAccept = 0
                self.timeout = 0.5

        self.show( [0,255,0,self.brAccept] * self.nPixels )
        return (self.brAccept>0)

    def animationCancel( self, restart:bool ):
        """Cancelled / Ignoring"""
        if restart : 
            self.brCancel = 100
            self.timeout = 0.5
        else:
            self.brCancel = self.brCancel * 0.5
            self.timeout = 0.1
            if self.brCancel < 2 :
                self.brCancel = 0
                self.timeout = 0.5

        self.show( [255,0,0,self.brCancel] * self.nPixels )
        return (self.brCancel>0)

    def animationNone( self, restart:bool ):
        """Standup animation"""
        self.show( [0,0,0,0] * self.nPixels )
        self.timeout = 0.3
        return False

    def show( self, pixels ):
        for i in range( self.nPixels ):
            self.leds.set_pixel( i, \
                  int( pixels[4 * i + 0] ), \
                  int( pixels[4 * i + 1] ), \
                  int( pixels[4 * i + 2] ), \
                  int( pixels[4 * i + 3] ) )

        if self.muted :
            for i in self.muteLeds:
                self.leds.set_pixel( i, 0,0,255, 100 )

        self.leds.show()

    def showRGB( self, pixels ):
        for i in range( self.nPixels ):
            self.leds.set_pixel_rgb( i, pixels[i] )

        if self.muted :
            for i in self.muteLeds:
                self.leds.set_pixel( i, 0,0,255, 100 )

        self.leds.show()

