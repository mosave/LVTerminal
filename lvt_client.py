#!/usr/bin/env python3
import sys
import time
import os
import asyncio
import audioop
import websockets
import multiprocessing
import pyaudio
import contextlib
from lvt.const import *
from lvt.client.sound_processor import SoundProcessor
from lvt.client.config import Config
from lvt.client.client import Client
from lvt.client.message_handler import MessageHandler


def showHelp():
    print( "usage: lvt_client.py [option]" )
    print( "Options available:" )
    print( "  -h | --help      these notes" )
    print( "  -d | --devices   list audio devices to specify in configuration file" )

def showDevices():
    print( "List of devices supported. Both device index or device name could be used" )
    audio = pyaudio.PyAudio()
    print( f' Index   Channels   Device name' )
    for i in range( audio.get_device_count() ):
        device = audio.get_device_info_by_index( i )
        print( f'  {i:>2}    I:{device.get("maxInputChannels")} / O:{device.get("maxOutputChannels")}   "{device.get("name")}"' )
        #print(device)
    audio.terminate()

######################################################################################
if __name__ == '__main__':
    #First thing first: save store script' folder as ROOT_DIR:
    ROOT_DIR = os.path.abspath( os.path.dirname( __file__ ) )

    print( "Lignt Voice Terminal Client" )

    if( len( sys.argv ) > 0 ):
        for arg in sys.argv:
            a = arg.strip().lower()
            if( ( a == '-h' ) or ( a == '--help' ) or ( a == '/?' ) ):
                showHelp()
                exit( 0 )
            elif( ( a == '-d' ) or ( a == '--devices' ) ):
                showDevices()
                exit( 0 )
    try:
        global config

        config = Config( os.path.splitext( os.path.basename( __file__ ) )[0] + '.cfg' )
        SoundProcessor.setConfig( config )

        shared = multiprocessing.Manager().Namespace()
        shared.isTerminated = False
        shared.isConnected = False
        shared.isMuted = False
        shared.serverStatus = '{"Terminal":""}'
        shared.serverConfig = '{}'
        messages = multiprocessing.Queue()

        messageHandler = multiprocessing.Process( target=MessageHandler, args=(config, messages, shared) )
        messageHandler.start()

        loop = asyncio.get_event_loop()
        loop.run_until_complete( Client( config, messages, shared ) )

        #client.join()
        messageHandler.join()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print( f'Unhandled exception in main thread: {e}' )
    print( 'Finishing application' )

