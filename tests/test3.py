#!/usr/bin/env python3
import sys
import time
import os
import io
import pyaudio
import audioop
import wave

import json
import os
import sys
import asyncio
import ssl
import pathlib
import websockets
import socket
import concurrent.futures
import logging
import time
import wave
import datetime




def play( data ):
    try:
        print()
        print("========== Инициализация аудиоподсистемы ==========")
        audio = pyaudio.PyAudio()
        print("============ Инициализация завершена ==============")
        print("")

        with wave.open( io.BytesIO( data ), 'rb' ) as wav:
            # Measure number of frames: 
            nFrames = int(len(data) / wav.getsampwidth() / wav.getnchannels() + 65)
            # Read ALL frames in memory:
            frames = wav.readframes(nFrames)
            # and calculate actual number of frames read...
            nFrames = int(len(frames)/wav.getsampwidth()/wav.getnchannels())

            # Calculate wav length in seconds
            waveLen = nFrames / wav.getframerate() + 0.3

            audioStream = audio.open( 
                format=pyaudio.get_format_from_width( wav.getsampwidth() ),
                channels=wav.getnchannels(),
                rate=wav.getframerate(),
                output=True,
                output_device_index=config.audioOutputDevice,
                frames_per_buffer = nFrames - 16 #!!! Dirty hack to workaround RPi cracking noise
            )
            audioStream.start_stream()
            startTime = time.time()
            audioStream.write( frames )

            # Wait until played
            while time.time() < startTime + waveLen : 
                time.sleep( 0.2 )
    except Exception as e:
        print( f'Exception playing audio: {e}' )
    finally:
        try: audioStream.stop_stream()
        except: pass
        try: audioStream.close()
        except:pass
        try: audio.terminate() 
        except:pass

def playFile(waveFileName):
    if os.path.dirname( waveFileName ) == '' :
        waveFileName = os.path.join( os.path.abspath( os.path.dirname( __file__ ) ), waveFileName )
    with open( waveFileName, 'rb' ) as wave:
        play( wave.read( 500 * 1024 ) )

playFile('1.wav')
playFile('2.wav')
playFile('3.wav')
playFile('4.wav')
