import sys
import time
import io
import os
import audioop
import pyaudio
import wave
from lvt.const import *
from lvt.protocol import *
from lvt.client.animator import Animator


def MessageHandler( config, messages, shared ):
    print( "Event handler thread starting" )
    while not shared.isTerminated:
        try:
            message = messages.get()
            m,p = parseMessage( message )
            if isinstance( message, str ) :
                if m == MSG_TEXT:
                    if p != None:
                        print()
                        print( f'Server: {p}' )
                elif m == MSG_ANIMATE:
                    if str( p ) in ANIMATION_ALL:
                        Animator().animate( p )
                else:
                    print( f'Message "{msg}" handler not yet implemented' )
            else: # Treat any binary data messages as wave fragments.
                shared.isMicrophoneEnabled = False
                try: #Play wave from memory by with BytesIO via audioStream
                    audio = pyaudio.PyAudio()
                    with wave.open( io.BytesIO( message ), 'rb' ) as wav:
                        # Get sample length in seconds
                        waveLen = len(message) / (wav.getnchannels() * wav.getsampwidth() * wav.getframerate())
                        audioStream = audio.open( format=pyaudio.get_format_from_width( wav.getsampwidth() ),
                            channels=wav.getnchannels(),
                            rate=wav.getframerate(),
                            output=True,
                            output_device_index=config.audioOutputDevice )
                        audioStream.start_stream()
                        # Get absolute time when message playing finished
                        stopTime = time.time() + waveLen + 0.2
                        audioStream.write( wav.readframes( wav.getnframes() ) )
                        # Wait until complete
                        while time.time()<stopTime : time.sleep( 0.2 )

                except Exception as e:
                    print( f'Exception playing audio: {e}' )
                finally:
                    try: audioStream.close()
                    except: pass
                    try: audio.terminate() 
                    except: pass
                shared.isMicrophoneEnabled = True


        except KeyboardInterrupt:
            if not shared.isTerminated : print( "Terminating..." )
            shared.isTerminated = True
        except Exception as e:
            print( f'Event handler thread exception: {e}' )

    print( "Finishing Event handler thread" )

