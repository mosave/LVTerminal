#!/usr/bin/env python3 
from asyncio import protocols
import sys
import time
import io
import json
import asyncio
import pyaudio
import wave
import ssl
import aiohttp
import multiprocessing
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
playerVolume : int = 100

#region showHelp(), showDevices() ######################################################
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

#region printStatus() ##################################################################
async def printStatusThread():
    global shared
    global microphone
    global animator
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

#region GetVolume() / SetVolume() ######################################################
def getVolume():
    global alsaaudio
    if config.volumeControl != None:
        return alsaaudio.Mixer(cardindex=config.volumeCardIndex, control=config.volumeControl ).getvolume()[0]
    else:
        return None

def getPlayerVolume():
    global alsaaudio
    global playerVolume
    if config.volumeControlPlayer != None:
        volume = alsaaudio.Mixer(cardindex=config.volumeCardIndex, control=config.volumeControlPlayer ).getvolume()[0]
        if volume>0: 
            playerVolume = volume
        return volume
    else:
        return None

def setVolume( volume: int ):
    volume = int(volume)
    volume = 100 if volume>100 else (0 if volume<0 else volume)

    try:
        alsaaudio.Mixer(cardindex=config.volumeCardIndex, control=config.volumeControl ).setvolume(volume)
    except Exception as e:
        pass

def setPlayerVolume( volume ):
    global playerVolume
    volume = int(volume)
    volume = 100 if volume>100 else (0 if volume<0 else volume)
    if volume>0: 
        playerVolume = volume
    try:
        alsaaudio.Mixer(cardindex=config.volumeCardIndex, control=config.volumeControlPlayer ).setvolume(volume)
    except Exception as e:
        pass
#endregion

#region play() #########################################################################
def play( data ):
    global audio
    global shared
    global microphone
    global animator

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

#endregion

#region messageThread() ################################################################
async def messageThread( connection ):
    global playerVolume
    global shared
    global microphone
    while True:
        try:
            msg = await connection.receive()
            m = None
            if msg.type == aiohttp.WSMsgType.BINARY:
                play(msg.data)
                continue
            elif msg.type == aiohttp.WSMsgType.TEXT:
                m,p = parseMessage( msg.data )
            
                #region Handling message m
                if m == MSG_STATUS:
                    if p != None : 
                        shared.terminalStatus = json.loads(p)
                        setVolume(int(shared.terminalStatus['Terminals'][config.terminalId]['Volume']))
                elif m == MSG_LVT_STATUS:
                    if p != None : shared.serverStatus = json.loads(p)
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
                    setVolume(p)
                elif m == MSG_MUTE_PLAYER:
                    v = getPlayerVolume()
                    if v is not None and v>0:
                        setPlayerVolume( 0 )
                        await asyncio.sleep(0.5)

                elif m == MSG_UNMUTE_PLAYER:
                    v = getPlayerVolume()
                    if v is not None and v==0:
                        await asyncio.sleep(0.5)
                        setPlayerVolume( playerVolume )

                elif m == MSG_VOLUME_PLAYER: 
                    p = int(p)
                    p = 100 if p>100 else (0 if p<0 else p)
                    setPlayerVolume(p)
                elif m == MSG_ANIMATE:
                    if p == None : p = ANIMATION_NONE
                    if animator != None and p in ANIMATION_ALL:
                        animator.animate( p )
                elif m == MSG_UPDATE:
                    if p != None: 
                        package = json.loads( p )
                        if updater.updateClient( package ) :
                            shared.isTerminated = True
                            restartClient()
                elif m == MSG_REBOOT:
                    print( 'Перезагрузка устройства еще не реализована. Перезапускаю клиент...' )
                    restartClient()
                else:
                    print( f'Unknown message received: "{m}"' )
                #endregion
            elif msg.type == aiohttp.WSMsgType.CLOSED:
                break
        except asyncio.TimeoutError:
            continue
        except KeyboardInterrupt:
            break
        except Exception as e:
            print( f'Message "{m}" processing {type(e).__name__}: {e}' )
#endregion

#region microphoneThread() #############################################################
async def microphoneThread( connection ):
    global shared
    global microphone
    with Microphone() as mic:
        microphone = mic
        _active = False
        while not shared.isTerminated:
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
                    await connection.send_bytes( data )
            else:
                _active = False
                pass

            await asyncio.sleep( 0.2 )
    microphone = None
#endregion

#region client() #######################################################################
async def client( serverUrl, sslContext ):
    global lastMessageReceived
    global pingAreadySent
    global microphone
    global shared

    log( "Запуск Websock сервиса" )
    while not shared.isTerminated:
        shared.isConnected = False
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(
                    serverUrl, 
                    receive_timeout = 0.5,
                    heartbeat=10, 
                    ssl= ssl.SSLContext if sslContext is not None else None,
                    ssl_context=sslContext ) as connection:
                    shared.isConnected = True

                    await connection.send_str( MESSAGE( MSG_TERMINAL, config.terminalId, config.password, VERSION ) )

                    tasks = [
                        asyncio.ensure_future( messageThread(connection) ),
                        asyncio.ensure_future( microphoneThread(connection) )
                        ]
                    if not shared.quiet :
                        tasks.append( asyncio.ensure_future( printStatusThread() ) )
                    done, pending = await asyncio.wait( tasks, return_when=asyncio.FIRST_COMPLETED, )
                    shared.isConnected = False
                    for task in pending:
                        task.cancel()

        except Exception as e:
            logError( f'Client error {type(e).__name__}: {e}' )
            await asyncio.sleep( 10 )
        except:
            shared.isConnected = False
            onCtrlC()
        finally:
            shared.isConnected = False

    log( "Finishing Client thread" )
#endregion

#region onCtrlC(), restartClient #######################################################
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
    try: 
        loop.stop()
    except: 
        pass

def restartClient():
    """  Перезапуск клиента в надежде что он запущен из скрипта в цикле """
    global shared
    print( 'Перезапуск...' )
    shared.isTerminated = True
    shared.exitCode = 42 # перезапуск
#endregion

#region Main program ###################################################################
if __name__ == '__main__':
    print()
    print( f'Lite Voice Terminal Client v{VERSION}' )

    print()
    print("========== Инициализация аудиоподсистемы ==========")
    audio = pyaudio.PyAudio()
    print("============= Инициализация завершена =============")
    print("")

    playerVolume = getPlayerVolume()
    if playerVolume is None or playerVolume<=0:
        playerVolume = 100

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
            print( f'Громкость плеера: {getPlayerVolume()}% ({config.volumeControlPlayer})' )

    # protocol = 'ws'
    sslContext = None
    if config.ssl :
        if config.sslAllowAny : # Disable host name and SSL certificate validation
            sslContext = ssl.SSLContext( ssl.PROTOCOL_TLS_CLIENT )
            sslContext.check_hostname = False
            sslContext.verify_mode = ssl.CERT_NONE
    # url = f'{protocol}://{config.serverAddress}:{config.serverPort}'

    url = f"http://{config.serverAddress}:{config.serverPort}"

    log( f'Сервер URL: {url}' )

    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete( client( url, sslContext ) )

        #loop.run_until_complete( websockClient( url, sslContext) )
    except KeyboardInterrupt as e:
        onCtrlC()
    except Exception as e:
        logError( f'Unhandled exception {type(e).__name__}: {e}' )
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
