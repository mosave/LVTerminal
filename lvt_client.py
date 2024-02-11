#!/usr/bin/env python3 
import sys
import time
import io
import json
import asyncio
import pyaudio
import wave
import ssl
import aiohttp

from lvt.const import *
from lvt.protocol import *
from lvt.logger import *
from lvt.client.microphone import Microphone
import lvt.client.config as config
import lvt.client.updater as updater

audio : pyaudio.PyAudio
microphone : Microphone = None
defaultPlayerVolume : int = 0

isQuiet = False
isTerminated = False
exitCode = 0
isConnected = False
terminalStatus = '{"Terminal":""}'
serverStatus = '{}'




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
    global microphone
    global isTerminated

    while not isTerminated:
        if microphone is not None :
            width = 38
            scale = 5000
            rms = microphone.rms
            if rms > scale : rms = scale
            graph = ''
            if not microphone.muted:
                for i in range( 0,int( rms * width / scale ) + 1 ): graph += '='
            graph = f'{graph:40}'

            pL = int( microphone.noiseLevel * width / scale )
            pL = 1 if pL < 1 else width if pL > width else pL

            pR = int( microphone.triggerLevel * width / scale )
            pR = 1 if pR < 1 else width if pR > width else pR
            if pL >= pR : pR = pL + 1

            if not microphone.muted:
                graph = graph[:pL] + '|' + graph[pL:pR] + '|' + graph[pR + 1:]
            else:
                graph += ' '

            mouth = 'o' if microphone.speaking else '_'
            face = f'*{mouth}*' if microphone.active else f'-{mouth}-'
            face = f'x({face})x' if microphone.muted else f'@({face})@'
            playing = 'P' if microphone.playing else 'p'
            sys.__stdout__.write( f'  {face} [{playing}] CH:{microphone.channel} RMS:{microphone.rms:>5} VAD:{microphone.vadLevel:>3} [{graph}]  \r' )
        await asyncio.sleep(1)
#endregion

#region ALSA: <get|set>[Player]Volume() ################################################
def getVolume():
    global alsaaudio
    global microphone
    if config.volumeControlVoice is not None:
        volume = alsaaudio.Mixer(cardindex=config.volumeCardIndex, control=config.volumeControlVoice ).getvolume()[0]
        if microphone is not None: microphone.voiceVolume = volume
        return volume
    else:
        return None

def getPlayerVolume():
    global alsaaudio
    if config.volumeControlPlayer is not None:
        volume = alsaaudio.Mixer(cardindex=config.volumeCardIndex, control=config.volumeControlPlayer ).getvolume()[0]
        if microphone is not None: microphone.playerVolume = volume
        return volume
    else:
        return 0

def setVolume( volume: int ):
    volume = int(volume)
    volume = 100 if volume>100 else (0 if volume<0 else volume)

    try:
        alsaaudio.Mixer(cardindex=config.volumeCardIndex, control=config.volumeControlVoice ).setvolume(volume)
        if microphone is not None: microphone.voiceVolume = volume
    except Exception as e:
        pass

def setPlayerVolume( volume ):
    volume = int(volume)
    volume = 100 if volume>100 else (0 if volume<0 else volume)
    try:
        alsaaudio.Mixer(cardindex=config.volumeCardIndex, control=config.volumeControlPlayer ).setvolume(volume)
        if microphone is not None: microphone.playerVolume = volume
    except Exception as e:
        pass
#endregion

#region mutePlayerAsync() / unmutePlayerAsync() ##################################################
async def mutePlayerAsync():
    global defaultPlayerVolume
    v = getPlayerVolume()
    if v is not None and v>0: 
        defaultPlayerVolume = v
        while v>0:
            v -= 5
            if v<0: v=0
            setPlayerVolume(v)
            await asyncio.sleep( 0.01 )

        await asyncio.sleep( 0.5 )

async def unmutePlayerAsync():
    global defaultPlayerVolume
    v = getPlayerVolume()
    if v is not None and defaultPlayerVolume > v: 
        await asyncio.sleep( 1 )
        while v < defaultPlayerVolume:
            v += 5
            if v>defaultPlayerVolume: v=defaultPlayerVolume
            setPlayerVolume(v)
            await asyncio.sleep( 0.01 )

#endregion

#region playAsync() ####################################################################
async def playAsync( data ):
    global audio
    global microphone

    try:
        #fn = datetime.datetime.today().strftime(f'{config.terminalId}_%Y%m%d_%H%M%S_play.wav')
        #f = open(os.path.join( ROOT_DIR, 'logs',fn),'wb')
        #f.write(data)
        #f.close()
        with wave.open( io.BytesIO( data ), 'rb' ) as wav:
            #print(f'len={len(data)}')
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
    except Exception as e:
        logError( f'Ошибка при загрузке аудиофрагмента' )
        nframes = 0
        return

    if nframes<=0 or len(frames)<=0:
        logError( f'Аудиофрагмент пустой' )
        return

    try:
        #print(f'open {nframes} frames ({len(frames)} bytes), nchannels={nchannels}, framerate={framerate} ')
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
        #await asyncio.sleep(0.1)
        #setVolume(volume)

        # Calculate time before audio played
        timeout = (nframes / framerate + 0) - (time.time() - startTime)
        # and wait if required...
        if timeout>0 : 
            await asyncio.sleep( timeout )
    except Exception as e:
        logError( f'Ошибка при воспроизведении аудио: {e}' )
    finally:
        try: audioStream.stop_stream()
        except: pass
        try: audioStream.close()
        except:pass
        pass

#endregion

#region microphoneThread() #############################################################
async def microphoneThread( connection ):
    global isTerminated
    global microphone
    log( "Микрофон: Запуск" )
    with Microphone() as mic:
        microphone = mic
        _speakerStatus = "? ?"
        try:
            while not isTerminated:
                if microphone.active : 
                    data = microphone.read()
                    if data is not None : 
                        await connection.send_bytes( data )
                await asyncio.sleep( 0.2 )

                speakerStatus = f'{1 if microphone.playing else 0} {1 if microphone.speaking else 0}' 
                if speakerStatus != _speakerStatus:
                    await connection.send_str( MESSAGE( MSG_SPEAKER_STATUS, speakerStatus ) )
                    _speakerStatus = speakerStatus
                    await asyncio.sleep( 0.2 )

        except KeyboardInterrupt:
            log( "Микрофон: Получен сигнал на завершение" )
        except Exception as e:
            print()
            logError(f"Микрофон: {type(e).__name__}: {e}")
        microphone = None
    log( "Микрофон: Завершение" )
#endregion

#region messageThread() ################################################################
async def messageThread( connection ):
    global isTerminated
    global isConnected
    global terminalStatus
    global microphone

    log("Основной цикл: Запуск")
    while not isTerminated:
        try:
            msg = await connection.receive()
            m = None
            if msg.type == aiohttp.WSMsgType.BINARY:
                #print("binary received")
                await playAsync(msg.data)
                continue
            elif msg.type == aiohttp.WSMsgType.TEXT:
                m,p = parseMessage( msg.data )
                #print(f"{m} received")
            
                #region Handling message m
                if m == MSG_STATUS:
                    if p is not None:
                        terminalStatus = json.loads(p)
                        setVolume(int(terminalStatus['Terminals'][config.terminalId]['Volume']))
                elif m == MSG_LVT_STATUS:
                    if p is not None : serverStatus = json.loads(p)
                elif m == MSG_WAKEUP:
                    microphone.active = True
                elif m == MSG_IDLE:
                    microphone.active = False
                elif m == MSG_DISCONNECT:
                    isConnected = True
                elif m == MSG_TEXT:
                    if p is not None:
                        print()
                        print( p )
                elif m == MSG_VOLUME: 
                    setVolume(p)
                elif m == MSG_MUTE_PLAYER:
                    await mutePlayerAsync()
                elif m == MSG_UNMUTE_PLAYER:
                    await unmutePlayerAsync()
                elif m == MSG_UPDATE:
                    if p is not None: 
                        package = json.loads( p )
                        if updater.updateClient( package ):
                            restart()
                elif m == MSG_REBOOT:
                    restart()
                else:
                    logError( f'Unknown message received: "{m}"' )
                #endregion
            elif msg.type == aiohttp.WSMsgType.CLOSED:
                break
        except asyncio.TimeoutError:
            continue
        except KeyboardInterrupt:
            break
        except Exception as e:
            logError( f'Основной цикл, {m}: {type(e).__name__}: {e}' )

    log("Основной цикл: остановка")
#endregion

#region client() #######################################################################
async def client( ):
    global microphone
    global isQuiet
    global isTerminated
    global isConnected

    log( "Запуск основного сервиса" )
    if config.ssl :
        sslContext = ssl.SSLContext( ssl.PROTOCOL_TLS_CLIENT )
        protocol = "https"
        if config.sslAllowAny : # Disable host name and SSL certificate validation
            sslContext.check_hostname = False
            sslContext.verify_mode = ssl.CERT_NONE
    else:
        sslContext = False
        protocol = "http"

    async with aiohttp.ClientSession() as session:
        printStatusTask = asyncio.ensure_future( printStatusThread() ) if not isQuiet else None


        while not isTerminated:
            isConnected = False
            try:
                async with session.ws_connect(
                    f"{protocol}://{config.serverAddress}:{config.serverPort}", 
                    receive_timeout = 0.5,
                    heartbeat=10,
                    ssl= sslContext,
                    ) as connection: 
                    isConnected = True

                    await connection.send_str( MESSAGE( MSG_TERMINAL, config.terminalId, config.password, VERSION ) )
                    microphoneTask = asyncio.ensure_future( microphoneThread(connection))
                    messageTask = asyncio.ensure_future( messageThread(connection))

                    tasks = []
                    tasks.append( microphoneTask )
                    tasks.append( messageTask )
                    if printStatusTask is not None: tasks.append( printStatusTask )

                    done, pending = await asyncio.wait( tasks, return_when=asyncio.FIRST_COMPLETED )

                    isConnected = False
                    logError("Disconnected")
                    if microphoneTask in pending:
                        microphoneTask.cancel()
                    if messageTask in pending:
                        messageTask.cancel()

            except Exception as e:
                isConnected = False
                print()
                logError( f'Client error {type(e).__name__}: {e}' )
                await asyncio.sleep( 10 )
            except:
                isConnected = False
                onCtrlC()
            finally:
                isConnected = False

    if printStatusTask is not None:
        printStatusTask.cancel()
        printStatusTask = None

    log( "Finishing Client thread" )
#endregion

#region onCtrlC(), restart #############################################################
def onCtrlC():
    """ Gracefuly terminate program """
    global isTerminated
    try:
        if not isTerminated:
            print()
            print( "Завершение программы..." )
        isTerminated = True
    except:
        pass
    try: 
        loop.stop()
    except: 
        pass

def restart():
    """  Перезапуск клиента в надежде что он запущен из скрипта в цикле """
    global isTerminated
    global exitCode
    log( 'Перезапуск...' )
    isTerminated = True
    exitCode = 42 # перезапуск
    sys.exit(42)
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

    defaultPlayerVolume = getPlayerVolume()

    for arg in sys.argv[1:]:
        a = arg.strip().lower()
        if ( a == '-h' ) or ( a == '--help' ) or ( a == '/?' ) :
            showHelp()
            exit( 0 )
        elif ( a == '-d' ) or ( a == '--devices' ) :
            showDevices()
            exit( 0 )
        elif ( a == '-q' ) or ( a == '--quiet' ) :
            isQuiet = True
        elif ( a.startswith('-с=' ) or a.startswith('--config=') ):
            #config parameter is already processed
            pass
        else:
            logError( f'Неизвестный параметр: "{arg}"' )

    config.init( audio )

    Microphone.init( audio )

    print( f'ID терминала: "{config.terminalId}"' )
    print( f'Устройство для захвата звука: #{config.audioInputDevice} "{config.audioInputName}"' )
    print( f'Устройство для вывода звука: #{config.audioOutputDevice} "{config.audioOutputName}"' )
    print( f'Канал микрофона: {config.microphones}' )
    print( f'Канал Voice loopback: {config.loopbackVoice}' )
    print( f'Канал Player loopback: {config.loopbackPlayer}' )

    if config.volumeControlVoice is not None or config.volumeControlPlayer is not None :
        import alsaaudio
        
        try:
            volumeControls = alsaaudio.mixers(config.volumeCardIndex)
        except alsaaudio.ALSAAudioError:
            logError(f"Неправильный индекс устройства alsamixer ({config.volumeCardIndex})" )
            config.volumeCardIndex = 0
            config.volumeControlVoice = None
            config.volumeControlPlayer = None
            volumeControls = []
        showControls = False
        if config.volumeControlVoice is not None and config.volumeControlVoice not in volumeControls:
            logError( f"Неправильное название громкости LVT: {config.volumeControlVoice}" )
            config.volumeControlVoice = None
            showControls = True
        if config.volumeControlPlayer is not None and config.volumeControlPlayer not in volumeControls:
            logError( f"Неправильное название громкости аудиоплеера: {config.volumeControlPlayer}" )
            config.volumeControlPlayer = None
            showControls = True
        if showControls:
            print( "Допустимые названия каналов управления громкостью:" )
            print( f"{', '.join(volumeControls)}" )

    if config.volumeControlVoice is not None or config.volumeControlPlayer is not None :
        #print( f'Устройство для управления громкостью: "{alsaaudio.cards()[config.volumeCardIndex]}"' )
        if config.volumeControlVoice is not None :
            print( f'Громкость LVT: {getVolume()}% ({config.volumeControlVoice})' )
        if config.volumeControlPlayer is not None :
            print( f'Громкость плеера: {getPlayerVolume()}% ({config.volumeControlPlayer})' )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete( client() )
    except KeyboardInterrupt as e:
        onCtrlC()
    except Exception as e:
        logError( f'Unhandled exception {type(e).__name__}: {e}' )
    except:
        onCtrlC()

    isTerminated = True
    time.sleep(1)

    if exitCode == 42:
        log( 'Перезапуск' )
        sys.exit( exitCode )
    else:
        print( 'Завершение работы' )
#endregion
