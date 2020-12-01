import sys
import time
import os
import ssl
import asyncio
import websockets
import pyaudio
from contextlib import asynccontextmanager, contextmanager, AsyncExitStack
from lvt.const import *
from lvt.protocol import *
from lvt.client.sound_estimator import SoundEstimator

lastMessageReceived = None
pingAreadySent = None
lastAnimation = None

##############################################################################################
def printStatus( config, shared, estimator ):

    width = 49
    scale = 5000
    rms = estimator.rms
    if rms > scale : rms = scale
    graph = ''
    for i in range( 0,int( rms * width / scale )+1 ): graph += '='
    graph = f'[{graph:50}] '
    p = int(  estimator.noiseLevel * width / scale )+1
    graph = graph[:p] + '|' + graph[p + 1:]
    p = int(  estimator.triggerLevel * width / scale )+1
    graph = graph[:p] + '|' + graph[p + 1:]

    face = '(-_-)' if shared.isIdle else '(O_O)'
    print( f'[{lastAnimation:^10}] {face} {rms:>5} {graph} ', end='\r' )

##############################################################################################
async def receiveMessages( connection, messages, shared ):
    global lastMessageReceived
    global pingAreadySent
    global lastAnimation

    t = time.time()
    # Server inactivity timeout control
    if t - lastMessageReceived > 30 : 
        print()
        print( "Server not answering. Reconnecting" )
        shared.isConnected = False
        return

    # Ping server every 20 seconds
    if ( time.time() - lastMessageReceived > 20 ) and not pingAreadySent: 
        await connection.send( MSG_STATUS )
        pingAreadySent = True

    while True:
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
            shared.isIdle = True
        elif m == MSG_DISCONNECT: 
            shared.isConnected = True
        elif m == MSG_ANIMATE:
            if p == None : 
                p = ANIMATE_NONE
                message = MESSAGE(MSG_ANIMATE, p)

            lastAnimation = p
            messages.put( message )
        else:
            messages.put( message )

##############################################################################################
async def Client( config, messages, shared ):
    global lastMessageReceived
    global pingAreadySent
    global lastAnimation

    print( "Starting websock client" )
    if config.audioInputDevice != None :
        print( f'Audio input device: #{config.audioInputDevice} "{config.audioInputName}"' )
    else:
        print( 'Using default audio input device' )

    while not shared.isTerminated:
        try:
            shared.isIdle = True
            shared.isConnected = False

            # Init audio subsystem
            audio = pyaudio.PyAudio()
            # Open audio stream
            audioStream = audio.open( 
                format = pyaudio.paInt16, 
                channels = 1,
                rate = config.sampleRate,
                input = True,
                input_device_index=config.audioInputDevice,
                frames_per_buffer = 4000 )

            estimator = SoundEstimator( audio.get_sample_size( pyaudio.paInt16 ) )

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
            async with websockets.connect( uri, ssl=sslContext ) as connection:
                try:
                    lastAnimation = ANIMATION_NONE
                    lastMessageReceived = time.time()
                    pingAreadySent = False

                    shared.isConnected = True
                    shared.isIdle = True
                    print( 'Connected, press Ctrl-C to exit' )
                    await connection.send( MESSAGE( MSG_TERMINAL, config.terminalId, config.password ) )
                    #await connection.send( MESSAGE( MSG_TEXT, 'блаблабла. БЛА!' ) )
                    #await connection.send( MSG_CONFIG )

                    while not shared.isTerminated and shared.isConnected:
                        waveBuffer = []
                        # wait until sound is triggered

                        while not shared.isTerminated and shared.isConnected and shared.isIdle:
                            await receiveMessages( connection, messages, shared )

                            waveData = audioStream.read( 4000 )
                            waveBuffer.append( waveData )
                            if len( waveBuffer ) > 3 : waveBuffer.pop( 0 )

                            if estimator.estimate( waveData ):
                                shared.isIdle = False
                                break

                            printStatus( config, shared, estimator )

                        while not shared.isTerminated and shared.isConnected and not shared.isIdle:
                            await receiveMessages( connection, messages, shared )

                            if len( waveBuffer ) > 0:
                                waveData = waveBuffer[0]
                                waveBuffer.pop( 0 )
                            else:
                                waveData = audioStream.read( 4000 )
                                estimator.estimate( waveData )
                                printStatus( config, shared, estimator )

                            if len( waveData ) == 0 : continue
                                
                            await connection.send( waveData )


                except KeyboardInterrupt:
                    if not shared.isTerminated: print( "Terminating..." )
                    shared.isTerminated = True
                except Exception as e:
                    if isinstance( e, websockets.exceptions.ConnectionClosedOK ) :
                        print( 'Disconnected' )
                    elif isinstance( e, websockets.exceptions.ConnectionClosedError ):
                        print( 'Disconnected by error' )
                    else:
                        print(f'Client loop error: {e}')
                        try: await connection.send( MSG_DISCONNECT )
                        except: pass

        except KeyboardInterrupt:
            if not shared.isTerminated: print( "Terminating..." )
            shared.isTerminated = True
        except Exception as e:
            print( f'Connection thread exception: {e} ' )
            await asyncio.sleep( 10 )
        finally:
            #Release audio device
            try: audioStream.close()
            except: pass
            try: audio.terminate() 
            except: pass

    print( "Finishing Client thread" )
