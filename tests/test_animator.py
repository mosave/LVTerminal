#!/usr/bin/env python3
import json
import os
import sys
import asyncio
import ssl
import pathlib
import websockets
import logging
import time
import pyaudio
import contextlib
import multiprocessing

sys.path.append( os.path.abspath( os.path.join( os.path.dirname( __file__ ),'../' ) ) )

from lvt.const import *
from lvt.protocol import *
from lvt.const import *
from lvt.alsa_supressor import AlsaSupressor
from lvt.client.microphone import Microphone
from lvt.client.config import Config

if __name__ == '__main__':
    #set project folder to correct value
    ROOT_DIR = os.path.abspath( os.path.join( os.path.dirname( __file__ ),'../' ) )

    AlsaSupressor.disableWarnings()

    config = Config()

    shared = multiprocessing.Manager().Namespace()
    shared.isTerminated = False
    shared.isConnected = False
    shared.isMuted = False
    shared.serverStatus = '{"Terminal":""}'
    shared.serverConfig = '{}'

    #from lvt.client.animator import Animator
    #animator = Animator( config, shared )

    from lvt.client.animator_apa102 import APA102Animator
    animator = APA102Animator( config, shared )
    
    animator.start()

    def animate( animation, timeout ):
        print( animation )
        animator.animate( animation )
        time.sleep( timeout )

    animate( ANIMATION_NONE, 1 )
    animate( ANIMATION_AWAKE, 3 )

    print('mute')
    animator.muted = True
    time.sleep( 3 )
    #animate( ANIMATION_THINK, 3 )

    animate( ANIMATION_ACCEPT,5)
    animate( ANIMATION_CANCEL,5)


    animator.animate( ANIMATION_ACCEPT )
    animator.animate( ANIMATION_CANCEL )

    print('un-mute')
    animator.muted = False

    animator.animate( ANIMATION_AWAKE )
    time.sleep(5)

    #animator.animate( ANIMATION_ACCEPT )
    #time.sleep(5)

    #animate( ANIMATION_THINK, 3 )

    #animate(ANIMATION_NONE, 1)
    #time.sleep(3)
    #animator.animate( ANIMATION_CANCEL)
    #time.sleep(3)
    #animator.animate( ANIMATION_ACCEPT)
    #time.sleep(3)
    #animator.animate( ANIMATION_CANCEL)
    #time.sleep(3)
    #animator.animate( ANIMATION_ACCEPT)
    #time.sleep(3)
    #animator.animate( ANIMATION_CANCEL)
    #time.sleep(3)
    #animator.animate( ANIMATION_ACCEPT)
    #time.sleep(3)
    #animator.animate( ANIMATION_CANCEL)
    #time.sleep(3)

    animator.animate( ANIMATION_NONE )
    time.sleep( 1 )
