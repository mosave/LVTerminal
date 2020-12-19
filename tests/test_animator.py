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

sys.path.append(os.path.abspath( os.path.join( os.path.dirname( __file__ ),'../' ) ))

from lvt.const import *
from lvt.protocol import *
from lvt.const import *
from lvt.client.microphone import Microphone
from lvt.client.config import Config

if __name__ == '__main__':
    #set project folder to correct value
    ROOT_DIR = os.path.abspath( os.path.join( os.path.dirname( __file__ ),'../' ) )

    config = Config( 'lvt_client.cfg' )

    shared = multiprocessing.Manager().Namespace()
    shared.isTerminated = False
    shared.isConnected = False
    shared.isMuted = False
    shared.serverStatus = '{"Terminal":""}'
    shared.serverConfig = '{}'

    #from lvt.client.animator import Animator
    #animator = Animator( config, shared )

    from lvt.client.animator_apa102 import APA102Animator
    animator = APA102Animator( config, shared, 12 )
    
    animator.start()

    animator.animate(ANIMATION_NONE)
    time.sleep(1)
    animator.animate( ANIMATION_AWAKE)
    time.sleep(5)
    animator.animate( ANIMATION_THINK)
    time.sleep(5)
    animator.animate(ANIMATION_NONE)
    time.sleep(1)
    animator.animate( ANIMATION_ACCEPT)
    time.sleep(3)
    animator.animate( ANIMATION_CANCEL)
    time.sleep(3)
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
    animator.animate( ANIMATION_NONE)

