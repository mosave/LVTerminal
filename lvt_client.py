#!/usr/bin/env python3 
import sys
import time
import io
import json
import asyncio
import pyaudio
import wave
import ssl
import websockets
import multiprocessing
import subprocess
#region leak troubleshooting:
TRACE_MALLOC = False
if TRACE_MALLOC :
    import tracemalloc
    import linecache
    import gc
#endregion
from lvt.const import *
from lvt.protocol import *
from lvt.logger import *
from lvt.client.microphone import Microphone
from lvt.client.animator import Animator
import lvt.client.config as config
import lvt.client.updater as updater

audio : pyaudio.PyAudio
shared = None
microphone : Microphone
animator : Animator

### showHelp(), showDevices() ##########################################################
#region
def showHelp():
    """Display usage instructions"""
    print( "Использование: lvt_client.py [параметры]" )
    print( "Допустимые параметры:" )
    print( " -h | --help                       Вывод этой подсказки" )
    print( " -d | --devices                    Показать список аудио устройств" )
    print( " -q | --quiet                      Не отображать уровень звука в консоли" )
    print( " -c=<config> | --config=<config>   Использоавть указанный файл конфигурации" )

def showDevices():
    global audio
    """List audio deivces to use in config"""
    print( "Список поддерживаемых аудио устройств. В файле конфигурации может быть указан как индекс так и название устройств" )
    print( f' Индекс  Каналы     Название устройтсва' )
    for i in range( audio.get_device_count() ):
        device = audio.get_device_info_by_index( i )
        print( f'  {i:>2}    I:{device.get("maxInputChannels")} / O:{device.get("maxOutputChannels")}   "{device.get("name")}"' )
        #print(device)
    audio.terminate()
#endregion

### printStatus() ######################################################################
#region
async def printStatusThread():
    global shared
    global microphone
    while not shared.isTerminated:
        if not shared.quiet and animator!=None :
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
            face = f'x({face})x' if microphone.muted else f'o({face})o'
            sys.__stdout__.write( f'[{animator.animation:^10}] {face} CH:{microphone.channel} RMS:{microphone.rms:>5} VAD:{microphone.vadLevel:>3} [{graph}]  \r' )
            await asyncio.sleep(1)
#endregion

### GetVolume() / SetVolume() ##########################################################
#region
def getVolume():
    global alsaaudio
    if config.volumeControl != None:
        return alsaaudio.Mixer(cardindex=config.volumeCardIndex, control=config.volumeControl ).getvolume()[0]
    else:
        return None

def getVolumePlayer():
    global alsaaudio
    if config.volumeControl != None:
        return alsaaudio.Mixer(cardindex=config.volumeCardIndex, control=config.volumeControlPlayer ).getvolume()[0]
    else:
        return None

def setVolume( volume ):
    try:
        alsaaudio.Mixer(cardindex=config.volumeCardIndex, control=config.volumeControl ).setvolume(volume)
    except Exception as e:
        pass

def setVolumePlayer( volume ):
    try:
        alsaaudio.Mixer(cardindex=config.volumeCardIndex, control=config.volumeControlPlayer ).setvolume(volume)
    except Exception as e:
        pass
#endregion

### play() #############################################################################
#region
def play( data ):
    global audio
    global shared
    global microphone
    global animator

    volumePlayer = getVolumePlayer()
    if volumePlayer != None:
        setVolumePlayer(0)

    muteUnmute = not microphone.muted
    if muteUnmute : 
        microphone.muted = True
        animator.muted = True
    try:
        #fn = datetime.datetime.today().strftime(f'{config.terminalId}_%Y%m%d_%H%M%S_play.wav')
        #f = open(os.path.join( ROOT_DIR, 'logs',fn),'wb')
        #f.write(data)
        #f.close()
        #volume = getVolume()
        #setVolume('0%')
        #time.sleep(0.1)

        with wave.open( io.BytesIO( data ), 'rb' ) as wav:
            sampwidth = wav.getsampwidth()
            format = pyaudio.get_format_from_width( sampwidth )
            nchannels = wav.getnchannels()
            framerate = wav.getframerate()
            nframes = wav.getnframes()
            #print(f'file properties: sampwidth {sampwidth} nchannels {nchannels} framerate {framerate} nframes {nframes} frames ({len(data)} bytes)')
            # Workaoround broken .wav header:
            t = len( data ) / sampwidth / nchannels
            if ( t > 0 ) and ( t < nframes ) :  nframes = t

            frames = wav.readframes( nframes )
            #print(f'{len(frames)} bytes of {nframes} frames read')
            # Control & fix broken .wav header
            t = int( len( frames ) / sampwidth / nchannels )
            if ( t > 0 ) and ( t < nframes ) : nframes = t

        #print(f'open {nframes} frames ({len(frames)} bytes)')
        audioStream = audio.open(
            format=format,
            channels=nchannels,
            rate=framerate,
            output=True,
            output_device_index=int(config.audioOutputDevice),
            frames_per_buffer = nframes - 4
        )
        startTime = time.time()
        #print('write frames')
        audioStream.write( frames )
        #print('setting volume')
        #time.sleep(0.1)
        #setVolume(volume)

        # Calculate time before audio played
        timeout = (nframes / framerate + 0) - (time.time() - startTime)
        # and wait if required...
        if timeout>0 : time.sleep( timeout )
    except Exception as e:
        print( f'Exception playing audio: {e}' )
    finally:
        try: audioStream.stop_stream()
        except: pass
        try: audioStream.close()
        except:pass
        pass

    if muteUnmute : 
        microphone.muted = False
        animator.muted = False

    if volumePlayer != None:
        setVolumePlayer(volumePlayer)

#endregion

### processMessage()? messageProcessorThread() #########################################
#region
async def processMessage( message ):
    try:
        m,p = parseMessage( message )
        #if isinstance(m, str) : print(m)
        if not isinstance( message,str ) : # Wave data to play
            play(message)
        elif m == MSG_STATUS:
            try:
                if p != None : shared.terminalStatus = json.loads(p)
            except:
                pass
        elif m == MSG_LVT_STATUS:
            try:
                if p != None : shared.serverStatus = json.loads(p)
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
        elif m == MSG_VOLUME: 
            try:
                p = int(p)
                p = 100 if p>100 else (0 if p<0 else p)
                setVolume(p)
            except:
                pass
        elif m == MSG_VOLUME_PLAYER: 
            try:
                p = int(p)
                p = 100 if p>100 else (0 if p<0 else p)
                setVolumePlayer(p)
            except:
                pass
        elif m == MSG_ANIMATE:
            if p == None : p = ANIMATE_NONE
            if animator != None and p in ANIMATION_ALL:
                animator.animate( p )
        elif m == MSG_UPDATE:
            if p != None: 
                try:
                    package = json.loads( p )
                    if updater.updateClient( package ) :
                        shared.isTerminated = True
                        restartClient()
                except Exception as e:
                    logError( f'Ошибка при обновлении клиента: {e}' )
        elif m == MSG_REBOOT:
            print( 'Перезагрузка устройства еще не реализована. Перезапускаю клиент...' )
            restartClient()
        else:
            print( f'Unknown message received: "{m}"' )
            pass
    except Exception as e:
        print( f'Exception processing message "{message}": {e}' )
        pass

async def messageProcessorThread( connection ):
    async for message in connection:
        await processMessage(message)
#endregion

### microphoneThread() #################################################################
#region
async def microphoneThread( connection ):
    global shared
    global microphone
    with Microphone() as mic:
        microphone = mic
        await connection.send( MESSAGE( MSG_TERMINAL, config.terminalId, config.password, VERSION ) )
        _active = False
        while not shared.isTerminated:
            #await processMessages( connection )
            if microphone.active : 
                try:
                    if not _active and shared.serverStatus['StoreAudio']=='True' :
                        await connection.send(MESSAGE(MSG_TEXT,f'CH:{microphone.channel}: RMS {microphone.rms} MAXPP {microphone.maxpp}, VAD:{microphone.vadLevel}'))
                except Exception as e:
                    print( f'{e}' )
                    pass
                _active = True
                data = microphone.read()
                if not microphone.muted and data != None : 
                    await connection.send( data )

            else:
                _active = False
                pass

            await asyncio.sleep( 0.2 )
    microphone = None
#endregion

### tracemallocThread() ################################################################
#region
async def tracemallocThread():
    global shared
    tracemalloc.start(10)
    while not shared.isTerminated:
        gc.collect()
        snapshot = tracemalloc.take_snapshot().filter_traces((
            tracemalloc.Filter(True, "*asyncio*"),
            #tracemalloc.Filter(False, "<unknown>"),
        ))

        top_stats = snapshot.statistics('traceback')
        s ='Top10 memory usage\r\n'
        for index, stat in enumerate(top_stats[:5], 1):
            myCode = False
            s = s + ("#%s: %s objects, %.1f KiB\r\n" % (index, stat.count, stat.size / 1024))
            for frame in reversed(stat.traceback):
                my = 'lvterminal' in  frame.filename.lower()
                if my: myCode = True
                if my or not myCode:
                    s = s + ('%s#%s: %s \r\n'% (frame.filename, frame.lineno, linecache.getline(frame.filename, frame.lineno).strip()))
        log(s)
        await asyncio.sleep( 60 )
#endregion

### websockClient() ####################################################################
#region
async def websockClient( serverUrl, sslContext):
    global lastMessageReceived
    global pingAreadySent
    global microphone

    log( "Запуск Websock сервиса" )
    while not shared.isTerminated:
        try:
            shared.isConnected = False
            async with websockets.connect( serverUrl, ssl=sslContext ) as connection:
                shared.isConnected = True
                tasks = [
                    asyncio.ensure_future( messageProcessorThread(connection) ),
                    asyncio.ensure_future( microphoneThread(connection) )
                    ]
                if TRACE_MALLOC:
                    tasks.append( asyncio.ensure_future( tracemallocThread() ) )
                if not shared.quiet :
                    tasks.append( asyncio.ensure_future( printStatusThread() ) )
                done, pending = await asyncio.wait( tasks, return_when=asyncio.FIRST_COMPLETED, )
                for task in pending:
                    task.cancel()

        except Exception as e:
            shared.isConnected = False
            if isinstance( e, websockets.exceptions.ConnectionClosedOK ) :
                print( 'Disconnected' )
            elif isinstance( e, websockets.exceptions.ConnectionClosedError ):
                logError( f'Отключение в результате ошибки: {e} ' )
            else:
                logError( f'Websock Client error: {e}' )
                try: await connection.send( MSG_DISCONNECT )
                except:pass
                await asyncio.sleep( 10 )
        except:
            shared.isConnected = False
            onCtrlC()
        finally:
            shared.isConnected = False
            pass

    log( "Finishing Client thread" )
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
#endregion

### Main program #######################################################################
#region
if __name__ == '__main__':
    print()
    print( f'Lite Voice Terminal Client v{VERSION}' )

    print()
    print("========== Инициализация аудиоподсистемы ==========")
    audio = pyaudio.PyAudio()
    print("============= Инициализация завершена =============")
    print("")

    config.init( audio )
    loggerInit( config )

    shared = multiprocessing.Manager().Namespace()
    shared.quiet = False
    shared.isTerminated = False
    shared.exitCode = 0
    shared.isConnected = False
    shared.terminalStatus = '{"Terminal":""}'
    shared.serverStatus = '{}'

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
        elif ( a.startswith('-с=' ) or a.startswith('--config=') ):
            #config parameter is already processed
            pass
        else:
            logError( f'Неизвестный параметр: "{arg}"' )

    Microphone.init( audio )

    if config.animator == "text":
        from lvt.client.animator import Animator
        animator = Animator( shared )
        animator.start()
    elif config.animator == "apa102":
        from lvt.client.animator_apa102 import APA102Animator
        animator = APA102Animator( shared )
        animator.start()
        animator.animate(ANIMATION_THINK)
    else:
        animator = None


    print( f'Устройство для захвата звука: #{config.audioInputDevice} "{config.audioInputName}"' )
    print( f'Устройство для вывода звука: #{config.audioOutputDevice} "{config.audioOutputName}"' )

    if config.volumeControl != None or config.volumeControlPlayer != None :
        import alsaaudio
        
        try:
            volumeControls = alsaaudio.mixers(config.volumeCardIndex)
        except alsaaudio.ALSAAudioError:
            logError(f"Неправильный индекс устройства alsamixer ({config.volumeCardIndex})" )
            config.volumeCardIndex = 0
            config.volumeControl = None
            config.volumeControlPlayer = None
            volumeControls = []
        showControls = False
        if config.volumeControl != None and config.volumeControl not in volumeControls:
            logError( f"Неправильное название громкости LVT: {config.volumeControl}" )
            config.volumeControl = None
            showControls = True
        if config.volumeControlPlayer != None and config.volumeControlPlayer not in volumeControls:
            logError( f"Неправильное название громкости аудиоплеера: {config.volumeControlPlayer}" )
            config.volumeControlPlayer = None
            showControls = True
        if showControls:
            print( "Допустимые названия каналов управления громкостью:" )
            print( f"{', '.join(volumeControls)}" )

    if config.volumeControl != None or config.volumeControlPlayer != None :
        #print( f'Устройство для управления громкостью: "{alsaaudio.cards()[config.volumeCardIndex]}"' )
        if config.volumeControl != None :
            print( f'Громкость LVT: {getVolume()}% ({config.volumeControl})' )
        if config.volumeControlPlayer != None :
            print( f'Громкость плеера: {getVolumePlayer()}% ({config.volumeControlPlayer})' )

    protocol = 'ws'
    sslContext = None
    if config.ssl :
        protocol = 'wss'
        if config.sslAllowAny : # Disable host name and SSL certificate validation
            sslContext = ssl.SSLContext( ssl.PROTOCOL_TLS_CLIENT )
            sslContext.check_hostname = False
            sslContext.verify_mode = ssl.CERT_NONE

    url = f'{protocol}://{config.serverAddress}:{config.serverPort}'
    log( f'Сервер URL: {url}' )

    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete( websockClient( url, sslContext) )
    except Exception as e:
        if isinstance( e, websockets.exceptions.ConnectionClosedOK ) :
            print( f'Disconnected' )
        elif isinstance( e, websockets.exceptions.ConnectionClosedError ):
            logError( f'Disconnected by error' )
        elif isinstance( e, KeyboardInterrupt ):
            onCtrlC()
        else:
            logError( f'Unhandled exception: {e}' )
    except:
        onCtrlC()

    shared.isTerminated = True
    time.sleep(0.5)

    if animator != None : 
        animator.off()
        del( animator )

    if shared.exitCode == 42 :
        print( 'Перезапуск' )
        sys.exit(shared.exitCode)
    else:
        print( 'Завершение работы' )
#endregion
