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
from lvt.client.sound_processor import SoundProcessor
from lvt.client.config import Config
from lvt.client.client import Client
from lvt.client.message_handler import MessageHandler

if __name__ == '__main__':
    #set project folder to correct value
    ROOT_DIR = os.path.abspath( os.path.join( os.path.dirname( __file__ ),'../' ) )
    print(ROOT_DIR)

    config = Config( 'lvt_client.cfg' )
    SoundProcessor.setConfig( config )

    shared = multiprocessing.Manager().Namespace()
    shared.isTerminated = False
    shared.isConnected = False
    shared.isMuted = False
    shared.serverStatus = '{"Terminal":""}'
    shared.serverConfig = '{}'
    messages = multiprocessing.Queue()

    #messages.put(MESSAGE(MSG_ANIMATE, ANIMATION_NONE))
    #messages.put(MESSAGE(MSG_ANIMATE, ANIMATION_AWAKE))
    messages.put(MESSAGE(MSG_ANIMATE, ANIMATION_THINK))
    #messages.put(MESSAGE(MSG_ANIMATE, ANIMATION_ACCEPT))
    #messages.put(MESSAGE(MSG_ANIMATE, ANIMATION_CANCEL))
    #messages.put(MESSAGE(MSG_ANIMATE, ANIMATION_ACCEPT))
    #messages.put(MESSAGE(MSG_ANIMATE, ANIMATION_CANCEL))
    #messages.put(MESSAGE(MSG_ANIMATE, ANIMATION_ACCEPT))
    #messages.put(MESSAGE(MSG_ANIMATE, ANIMATION_CANCEL))
    #messages.put(MESSAGE(MSG_ANIMATE, ANIMATION_ACCEPT))
    #messages.put(MESSAGE(MSG_ANIMATE, ANIMATION_CANCEL))
    #messages.put(MESSAGE(MSG_ANIMATE, ANIMATION_NONE))
    MessageHandler(config, messages, shared, True )
