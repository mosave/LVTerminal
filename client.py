#!/usr/bin/env python3
import sys
import time
import datetime
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
from lvt.alsa_supressor import AlsaSupressor
from lvt.client.microphone import Microphone
from lvt.client.config import Config
from lvt.client.updater import Updater

config = None
shared = None
microphone = None
animator = None

### showHelp(), showDevices() ##########################################################
#region
def showHelp():
    """Display usage instructions"""
    print( "Использование: lvt_client.py [параметры]" )
    print( "Допустимые параметры:" )
    print( " -h | --help                    Вывод этой подсказки" )
    print( " -d | --devices                 Показать список аудио устройств" )
    print( " -q | --quiet                   Не отображать уровень звука в консоли" )

def showDevices():
    """List audio deivces to use in config"""
    print( "Список поддерживаемых аудио устройств. В файле конфигурации может быть указан как индекс так и название устройств" )
    audio = pyaudio.PyAudio()
    print( f' Индекс  Каналы     Название устройтсва' )
    for i in range( audio.get_device_count() ):
        device = audio.get_device_info_by_index( i )
        print( f'  {i:>2}    I:{device.get("maxInputChannels")} / O:{device.get("maxOutputChannels")}   "{device.get("name")}"' )
        #print(device)
    audio.terminate()
#endregion

### printStatus() ######################################################################
#region
def printStatus():
    global shared
    if shared.quiet : return

    width = 38
    scale = 5000
    rms = microphone.rms
    if rms > scale : rms = scale
    graph = ''
    for i in range( 0,int( rms * width / scale ) + 1 ): graph += '='
    graph = f'{graph:40}'

    pL = int( microphone.noiseLevel * width / scale )
    pL = 1 if pL < 1 else width if pL > width else pL

    pR = int( microphone.triggerLevel * width / scale )
    pR = 1 if pR < 1 else width if pR > width else pR
    if pL >= pR : pR = pL + 1

    graph = graph[:pL] + '|' + graph[pL:pR] + '|' + graph[pR + 1:]

    face = 'O_O' if microphone.active else '-_-'
    face = f'x{face}x' if microphone.muted else f'({face})'

    sys.__stdout__.write( f'[{animator.animation:^10}] {face} CH:{microphone.channel} RMS:{microphone.rms:>5} VAD:{microphone.vadLevel:>3} [{graph}]  \r' )
#endregion

### play() #############################################################################
#region
def play( data ):
    global microphone
    global shared
    global config
    muteUnmute = not microphone.muted
    if muteUnmute : 
        microphone.muted = True
        animator.muted = True
    try:

        audio = pyaudio.PyAudio()
        #fn = datetime.datetime.today().strftime(f'{config.terminalId}_%Y%m%d_%H%M%S_play.wav')
        #f = open(os.path.join( ROOT_DIR, 'logs',fn),'wb')
        #f.write(data)
        #f.close()

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
            while time.time() < startTime + waveLen : time.sleep( 0.2 )
    except Exception as e:
        print( f'Exception playing audio: {e}' )
    finally:
        try: audioStream.stop_stream()
        except: pass
        try: audioStream.close()
        except:pass
        try: audio.terminate() 
        except:pass

    if muteUnmute : 
        microphone.muted = False
        animator.muted = False

#endregion

### processMessages() ##################################################################
#region
async def processMessages( connection ):
    global lastMessageReceived
    global pingAreadySent

    t = time.time()

    # Ping server every 20 seconds
    if ( t - lastMessageReceived > 20 ) and not pingAreadySent: 
        await connection.send( MSG_STATUS )
        pingAreadySent = True

    message = None
    try:
        message = await asyncio.wait_for( connection.recv(), timeout=0.05 )
    except asyncio.TimeoutError:
        return
    if message == None or len( message ) == 0 : return
    lastMessageReceived = t
    pingAreadySent = False

    m,p = parseMessage( message )
    #if isinstance(m, str) : print(m)
    if m == MSG_STATUS:
        try:
            if p != None : shared.serverStatus = json.loads(p)
        except:
            pass
    elif m == MSG_CONFIG:
        try:
            if p != None : shared.serverConfig = json.loads(p)
        except:
            pass
    elif m == MSG_WAKEUP: 
        microphone.active = True
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
    elif m == MSG_UPDATE:
        if p != None: 
            try:
                package = json.loads( p )
                updater = Updater()
                if updater.update( package ) :
                    shared.isTerminated = True
                    await connection.send( MESSAGE( MSG_DISCONNECT, "Reboot after file update" ) )
                    restartClient()
            except Exception as e:
                printError( f'Ошибка при обновлении клиента: {e}' )
    elif m == MSG_REBOOT:
        print( 'Перезагрузка устройства еще не реализована. Перезапускаю клиент...' )
        await connection.send( MESSAGE( MSG_DISCONNECT, "Reboot by server request" ) )
        restartClient()
            
    elif not isinstance( message,str ) : # Wave data to play
        play(message)
    else:
        print( f'Unknown message received: "{m}"' )
        pass
#endregion

### websockClient() ####################################################################
#region
async def websockClient():
    global lastMessageReceived
    global pingAreadySent
    global microphone

    print( "Запуск Websock сервиса" )

    protocol = 'ws'
    sslContext = None
    if config.ssl :
        protocol = 'wss'
        if config.sslAllowAny : # Disable host name and SSL certificate validation
            sslContext = ssl.SSLContext( ssl.PROTOCOL_TLS_CLIENT )
            sslContext.check_hostname = False
            sslContext.verify_mode = ssl.CERT_NONE

    uri = f'{protocol}://{config.serverAddress}:{config.serverPort}'
    print( f'Сервер: {uri}' )

    while not shared.isTerminated:
        try:
            shared.isConnected = False
            async with websockets.connect( uri, ssl=sslContext ) as connection:
                with Microphone() as microphone:
                    lastMessageReceived = time.time()
                    pingAreadySent = False

                    shared.isConnected = True
                    print( 'Сервис запущен. Нажмите Ctrl-C для выхода' )
                    await connection.send( MESSAGE( MSG_TERMINAL, config.terminalId, config.password, VERSION ) )
                    _active = False
                    while not shared.isTerminated and shared.isConnected:
                        await processMessages( connection )
                        if microphone.active : 
                            try:
                                if not _active : print('just activated')

                                if not _active and shared.serverConfig['StoreAudio']=='True' :
                                    for ch in range(microphone.channels):
                                        await connection.send(MESSAGE(MSG_TEXT,f'CH#{ch}: RMS {microphone._rms[ch]} MAX {microphone._max[ch]}'))
                                    await connection.send(MESSAGE(MSG_TEXT,f'Selecting CH#{microphone.channel}, VAD:{microphone.vadLevel}'))
                            except Exception as e:
                                print( f'{e}' )
                                pass
                            _active = True
                            data = microphone.read()
                            if not microphone.muted and data != None : 
                                await connection.send( data )

                        else:
                            if _active : print('just deactivated')
                            _active = False
                            pass

                        printStatus()
                        await asyncio.sleep( 0.1 )

        except KeyboardInterrupt:
            onCtrlC()
        except Exception as e:
            shared.isConnected = False
            if isinstance( e, websockets.exceptions.ConnectionClosedOK ) :
                print( 'Disconnected' )
            elif isinstance( e, websockets.exceptions.ConnectionClosedError ):
                printError( f'Отключение в результате ошибки: {e} ' )
            else:
                printError( f'Websock Client error: {e}' )
                try: await connection.send( MSG_DISCONNECT )
                except:pass
                await asyncio.sleep( 10 )
        finally:
            pass

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
    """  Перезапуск клиента в надежде что он запущен из скрипта в цикле """
    print( 'Перезапуск...' )
    global shared
    shared.isTerminated = True
    shared.exitCode = 42 # перезапуск

def restartClientZZZ():
    """  Make Python re-compile and re-run app """
    print( 'Перезапуск...' )
    attempt = 1
    while True :
        try:
            fn = os.path.join( ROOT_DIR, 'client.py')
            #print(f'"{format(fn)}" {sys.argv}')
            #os.execl( sys.executable, f'"{format(sys.executable)}"', *sys.argv )
            os.execl( fn, *sys.argv )
            return
        except Exception as e:
            if attempt>=10 : raise e
            print(f'Ошибка: {e}')
            time.sleep(3)
            attempt += 1
            print(f'Перезапуск, попытка {attempt}...')
  
#endregion

### Main program #######################################################################
#region
if __name__ == '__main__':
    print()
    print( f'Lite Voice Terminal Client v{VERSION}' )

    AlsaSupressor.disableWarnings()

    config = Config()

    shared = multiprocessing.Manager().Namespace()
    shared.quiet = False
    shared.isTerminated = False
    shared.exitCode = 0
    shared.isConnected = False
    shared.serverStatus = '{"Terminal":""}'
    shared.serverConfig = '{}'
    Logger.initialize( config )


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

        else:
            printError( f'Неизвестный параметр: "{arg}"' )

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
        animator.animate(ANIMATION_THINK)
    else:
        animator = None


    print( f'Устройство для захвата звука: #{config.audioInputDevice} "{config.audioInputName}"' )
    print( f'Устройтсво для вывода звука: #{config.audioOutputDevice} "{config.audioOutputName}"' )

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
            printError( f'Unhandled exception: {e}' )

    if animator != None : del( animator )
    if shared.exitCode == 42 :
        print( 'Перезапуск' )
        sys.exit(shared.exitCode)
    else:
        print( 'Завершение работы' )
#endregion
