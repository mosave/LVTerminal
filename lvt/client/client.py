import sys
import time
import os
import ssl
import asyncio
import websockets
from contextlib import asynccontextmanager, contextmanager, AsyncExitStack
from lvt.const import *
from lvt.protocol import *
from lvt.client.sound_processor import SoundProcessor

lastMessageReceived = None
pingAreadySent = None
lastAnimation = None

##############################################################################################
def printStatus( config, shared, soundProcessor ):

    width = 49
    scale = 5000
    rms = soundProcessor.rms
    if rms > scale : rms = scale
    graph = ''
    for i in range( 0,int( rms * width / scale )+1 ): graph += '='
    graph = f'[{graph:50}] '
    p = int(  soundProcessor.noiseLevel * width / scale )+1
    graph = graph[:p] + '|' + graph[p + 1:]
    p = int(  soundProcessor.triggerLevel * width / scale )+1
    graph = graph[:p] + '|' + graph[p + 1:]

    face = 'O_O' if soundProcessor.isActive else '-_-'
    face = f'X{face}X' if soundProcessor.isMuted else f'({face})'
    print( f'[{lastAnimation:^10}] {face} {rms:>5} {graph}       ', end='\r' )

##############################################################################################
async def processMessages( connection, messages, shared, soundProcessor ):
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
            soundProcessor.isActive = False
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

    soundProcessor = None
    while not shared.isTerminated:
        try:
            shared.isConnected = False

            soundProcessor = SoundProcessor()

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
                    print( 'Connected, press Ctrl-C to exit' )
                    await connection.send( MESSAGE( MSG_TERMINAL, config.terminalId, config.password ) )
                    #await connection.send( MESSAGE( MSG_TEXT, 'блаблабла. БЛА!' ) )
                    #await connection.send( MSG_CONFIG )

                    while not shared.isTerminated and shared.isConnected:

                        # Ждем и обрабатываем сообщения пока не будет обнаружена речь
                        while not shared.isTerminated and shared.isConnected and not soundProcessor.isActive:
                            await processMessages( connection, messages, shared, soundProcessor )
                            soundProcessor.isMuted = shared.isMuted
                            soundProcessor.process()
                            printStatus( config, shared, soundProcessor )

                        while not shared.isTerminated and shared.isConnected and soundProcessor.isActive:
                            await processMessages( connection, messages, shared, soundProcessor )
                            soundProcessor.isMuted = shared.isMuted

                            if not soundProcessor.isActive : break

                            data = soundProcessor.read()
                            printStatus( config, shared, soundProcessor )

                            if data != None and len(data)>0 :
                                await connection.send( data )

                except KeyboardInterrupt:
                    if not shared.isTerminated: print( "Terminating..." )
                    shared.isTerminated = True
                except Exception as e:
                    if isinstance( e, websockets.exceptions.ConnectionClosedOK ) :
                        print( 'Disconnected' )
                    elif isinstance( e, websockets.exceptions.ConnectionClosedError ):
                        print( 'Disconnected due to error: {e} ' )
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
            #Release sound processor
            if soundProcessor != None:
                try:del(soundProcessor)
                except: pass
            soundProcessor = None

    print( "Finishing Client thread" )
