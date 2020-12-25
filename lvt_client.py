#!/usr/bin/env python3
import sys
import time
import os
import io
import json
import asyncio
import pyaudio
import audioop
import wave
import ssl
import websockets
import threading
import multiprocessing
import contextlib
from lvt.const import *
from lvt.protocol import *
from lvt.logger import *
from lvt.client.microphone import Microphone
from lvt.client.config import Config
from lvt.client.updater import Updater

quiet = False
config = None
shared = None
microphone = None
animator = None

### showHelp(), showDevices() ##########################################################
#region
def showHelp():
    """Display usage instructions"""
    print( "usage: lvt_client.py [options]" )
    print( "Options available:" )
    print( " -h | --help                    show these notes" )
    print( " -d | --devices                 list audio devices to specify in configuration file" )
    print( " -q | --quiet                   hide sound level indicator" )
    print( " -l[=<file>] | --log[=<file>]   Overwrite log file location defined in config file " )

def showDevices():
    """List audio deivces to use in config"""
    print( "List of devices supported. Both device index or device name could be used" )
    audio = pyaudio.PyAudio()
    print( f' Index   Channels   Device name' )
    for i in range( audio.get_device_count() ):
        device = audio.get_device_info_by_index( i )
        print( f'  {i:>2}    I:{device.get("maxInputChannels")} / O:{device.get("maxOutputChannels")}   "{device.get("name")}"' )
        #print(device)
    audio.terminate()

#endregion

### printStatus() ######################################################################
#region
def printStatus():
    global quiet
    if quiet : return

    width = 48
    scale = 5000
    rms = microphone.rms
    if rms > scale : rms = scale
    graph = ''
    for i in range( 0,int( rms * width / scale ) + 1 ): graph += '='
    graph = f'{graph:50}'

    pL = int( microphone.noiseLevel * width / scale )
    pL = 1 if pL < 1 else width if pL > width else pL

    pR = int( microphone.triggerLevel * width / scale )
    pR = 1 if pR < 1 else width if pR > width else pR
    if pL >= pR : pR = pL + 1

    graph = graph[:pL] + '|' + graph[pL:pR] + '|' + graph[pR + 1:]

    face = 'O_O' if microphone.active else '-_-'
    face = f'x{face}x' if microphone.muted else f'({face})'

    sys.__stdout__.write( f'[{lastAnimation:^10}] {face} {rms:>5} [{graph}]  \r' )
#endregion

### play() #############################################################################
#region
def play( data, onPlayed=None ):
    # Asynchronously play wave from memory by with BytesIO via
    # audioOutputStream
    try: 
        audio = pyaudio.PyAudio()
        with wave.open( io.BytesIO( data ), 'rb' ) as wav:
            # Get sample length in seconds
            waveLen = len( data ) / ( wav.getnchannels() * wav.getsampwidth() * wav.getframerate() )
            audioStream = audio.open( format=pyaudio.get_format_from_width( wav.getsampwidth() ),
                channels=wav.getnchannels(),
                rate=wav.getframerate(),
                output=True,
                output_device_index=config.audioOutputDevice )
            audioStream.start_stream()
            # Get absolute time when data playing finished
            stopTime = time.time() + waveLen + 0.3
            audioStream.write( wav.readframes( wav.getnframes() ) )
            # Wait until complete
            while time.time() < stopTime : time.sleep( 0.2 )

    except Exception as e:
        print( f'Exception playing audio: {e}' )
    finally:
        try: audioStream.close()
        except:pass
        try: audio.terminate() 
        except:pass
        shared.messageProcessingPaused = False
#endregion

### processMessages() ##################################################################
#region
async def processMessages( connection ):
    global lastMessageReceived
    global pingAreadySent
    global lastAnimation

    t = time.time()

    # Ping server every 20 seconds
    if ( t - lastMessageReceived > 20 ) and not pingAreadySent: 
        await connection.send( MSG_STATUS )
        pingAreadySent = True

    while not shared.messageProcessingPaused:
        message = None
        try:
            message = await asyncio.wait_for( connection.recv(), timeout=0.01 )
        except asyncio.TimeoutError:
            return
        if message == None or len( message ) == 0 : return
        lastMessageReceived = t
        pingAreadySent = False

        m,p = parseMessage( message )
        if m == MSG_STATUS:
            if p != None : shared.serverStatus = p
        elif m == MSG_CONFIG:
            if p != None : shared.serverConfig = p
        elif m == MSG_IDLE: 
            microphone.active = False
        elif m == MSG_DISCONNECT:
            shared.isConnected = True
        elif m == MSG_TEXT:
            if p != None :
                print()
                print( p )
        elif m == MSG_MUTE: 
            microphone.muted = True
            animator.muted = True
        elif m == MSG_UNMUTE: 
            microphone.muted = False
            animator.muted = False
        elif m == MSG_ANIMATE:
            if p == None : p = ANIMATE_NONE
            if animator != None and p in ANIMATION_ALL:
                animator.animate( p )
            lastAnimation = p
        elif m == MSG_UPDATE:
            if p != None: 
                try:
                    package = json.loads( p )
                    updater = Updater()
                    if updater.update( package ) :
                        shared.isTerminated = True
                        await connection.send( MESSAGE( MSG_DISCONNECT, "Reboot after file update" ) )
                        time.sleep( 3 )
                        restartClient()
                except Exception as e:
                    printError( f'Error while updating client: {e}' )
        elif m == MSG_REBOOT:
            print( 'Device reboot is not yet implemented, resarting client instead' )
            await connection.send( MESSAGE( MSG_DISCONNECT, "Reboot by server request" ) )
            restartClient()
            
        elif not isinstance( message,str ) : # Wave data to play
            shared.messageProcessingPaused = True
            thread = threading.Thread( target=play, args=[message] )
            thread.daemon = False
            thread.start()
        else:
            print( f'Unknown message received: "{m}"' )
            pass
#endregion

### websockClient() ####################################################################
#region
async def websockClient():
    global lastMessageReceived
    global pingAreadySent
    global lastAnimation
    global microphone

    print( "Starting websock client" )

    while not shared.isTerminated:
        try:
            shared.isConnected = False

            protocol = 'ws'
            sslContext = None
            if config.ssl :
                protocol = 'wss'
                if config.sslAllowAny : # Disable host name and SSL certificate validation
                    sslContext = ssl.SSLContext( ssl.PROTOCOL_TLS_CLIENT )
                    sslContext.check_hostname = False
                    sslContext.verify_mode = ssl.CERT_NONE

            uri = f'{protocol}://{config.serverAddress}:{config.serverPort}'
            print( f'Connecting {uri}' )
            with Microphone() as microphone:
                async with websockets.connect( uri, ssl=sslContext ) as connection:
                    try:
                        lastAnimation = ANIMATION_NONE
                        lastMessageReceived = time.time()
                        pingAreadySent = False

                        shared.isConnected = True
                        print( 'Connected, press Ctrl-C to exit' )
                        await connection.send( MESSAGE( MSG_TERMINAL, config.terminalId, config.password, VERSION ) )
                        #await connection.send( MESSAGE( MSG_TEXT, 'блаблабла.
                        #БЛА!' ) )
                        #await connection.send( MSG_CONFIG )

                        while not shared.isTerminated and shared.isConnected:
                            await processMessages( connection )
                            if microphone.active : 
                                data = microphone.read()
                                if data != None : await connection.send( data )

                            else:
                                pass

                            printStatus()
                            time.sleep( 0.1 )

                    except KeyboardInterrupt:
                        onCtrlC()
                    except Exception as e:
                        if isinstance( e, websockets.exceptions.ConnectionClosedOK ) :
                            print( 'Disconnected' )
                        elif isinstance( e, websockets.exceptions.ConnectionClosedError ):
                            printError( f'Disconnected due to error: {e} ' )
                        else:
                            printError( f'Client loop error: {e}' )
                            try: await connection.send( MSG_DISCONNECT )
                            except:pass

        except KeyboardInterrupt:
            onCtrlC()
        except Exception as e:
            printError( f'Connection thread exception: {e} ' )
            await asyncio.sleep( 10 )
        finally:
            try: del( microphone )
            except:pass

    print( "Finishing Client thread" )
#endregion

### onCtrlC(), restartClient ###########################################################
#region
def onCtrlC():
    """ Gracefuly terminate program """
    global shared
    try:
        if not shared.isTerminated: 
            print()
            print( "Terminating..." )
        shared.isTerminated = True
    except:
        pass
    try: loop.stop()
    except: pass

def restartClient():
    """  Make Python re-compile and re-run app """
    print( 'Restarting...' )
    os.execl( sys.executable, f'"{format(sys.executable)}"', *sys.argv )
#endregion

### Main program #######################################################################
#region
if __name__ == '__main__':
    print()
    print( f'Lignt Voice Terminal Client v{VERSION}' )

    config = Config( os.path.splitext( os.path.basename( __file__ ) )[0] + '.cfg' )

    shared = multiprocessing.Manager().Namespace()
    shared.isTerminated = False
    shared.isConnected = False
    #shared.volume = 75
    shared.serverStatus = '{"Terminal":""}'
    shared.serverConfig = '{}'
    shared.messageProcessingPaused = False
    logFileName = None
    logger = None
    quiet = False

    for arg in sys.argv[1:]:
        a = arg.strip().lower()
        if ( a == '-h' ) or ( a == '--help' ) or ( a == '/?' ) :
            showHelp()
            exit( 0 )
        elif ( a == '-d' ) or ( a == '--devices' ) :
            showDevices()
            exit( 0 )
        elif ( a == '-q' ) or ( a == '--quiet' ) :
            shared.quiet = True
        elif a.startswith( "-l" ) or a.startswith( "-log" ):
            b = arg.split( '=',2 )
            config.logFileName = b[1] if len( b ) == 2 else "logs/client.log"

        else:
            printError( f'Invalid command line argument: "{arg}"' )

    Logger.initialize( config )
    Microphone.initialize( config )
    Updater.initialize( config, shared )

    if config.animator == "text":
        from lvt.client.animator import Animator
        animator = Animator( config,shared )
        animator.start()
    elif config.animator == "apa102":
        from lvt.client.animator_apa102 import APA102Animator
        animator = APA102Animator( config,shared )
        animator.start()
    else:
        animator = None


    print( f'Audio input: #{config.audioInputDevice} "{config.audioInputName}"' )
    print( f'Audio output: #{config.audioOutputDevice} "{config.audioOutputName}"' )

    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete( websockClient() )

    except Exception as e:
        if isinstance( e, websockets.exceptions.ConnectionClosedOK ) :
            print( f'Disconnected' )
        elif isinstance( e, websockets.exceptions.ConnectionClosedError ):
            printError( f'Disconnected by error' )
        elif isinstance( e, KeyboardInterrupt ):
            onCtrlC()
        else:
            printError( f'Unhandled exception in main thread: {e}' )

    if animator != None : del( animator )
    print( 'Finishing application' )
#endregion
