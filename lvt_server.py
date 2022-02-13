#!/usr/bin/env python3 
import json
from logging import fatal
import os
import sys
import asyncio
import ssl

from aiohttp import web, WSMsgType
import concurrent.futures
import time
import wave
import datetime

from vosk import Model, SpkModel, KaldiRecognizer, SetLogLevel
from lvt.const import *
from lvt.server.grammar import *
from lvt.protocol import *
from lvt.logger import *
import lvt.server.config as config
import lvt.server.persistent_state as persistent_state
import lvt.server.entities as entities
import lvt.server.terminal as terminals
import lvt.server.speakers as speakers
import lvt.server.api as api


#region processVoice ###################################################################
async def processVoice( waveChunk, recognizer: KaldiRecognizer):
    """ Recognize audio chunk and process with terminal.onText() """
    signature = None
    text = ''
    final = False
    try:
        final = recognizer.AcceptWaveform( waveChunk )

        if final: # Фраза распознана полностью
            j = json.loads( recognizer.FinalResult() )
            # Получить распознанный текст
            text = str( j['text'] ).strip() if 'text' in j else ''
        else:
            # Получить распознанный текст
            j = json.loads( recognizer.PartialResult() )
            text = str( j['partial'] ).strip() if 'partial' in j else ''

        # Попытаться извлечь сигнатуру голоса:
        signature = j["spk"] if 'spk' in j else []
    except KeyboardInterrupt as e:
        onCtrlC()
        raise e
    except Exception as e:
        logError( f'Exception processing phrase chunk : {e}' )
    return (final, text, signature)

#endregion

#region websockServer ##################################################################
async def server( request ):
    """Main service thread - websock server implementation """
    global model
    global gModel
    global spkModel
    # Kaldi speech recognizer objects
    recognizer = None
    gRecognizer = None

    # Currently connected Terminal
    terminal = None

    # Assistant names
    aNames = wordsToList(config.assistantNames)

    # temp vars to track Terminal
    messageQueue = list()
    lastTickedOn = time.time()
    message = None
    voiceData = None
    isActive = False
    text = ''
    speakerSignature = None
    terminal = None
    
    def sendDatagram( data ):
        messageQueue.append( data )

    def sendMessage( msg:str, p1:str=None, p2:str=None ):
        sendDatagram( MESSAGE( msg,p1,p2 ) )

    def sendStatus():
        status = json.dumps(terminal.getState()) if terminal != None else '{"Terminal":"?","Name":"Not Registered","Connected":"false"}'
        sendMessage( MSG_STATUS, status )

    connection = web.WebSocketResponse()
    await connection.prepare(request)


    while True: # <== Breaking out of here will close connection
        try:
            # Отправляем накопившиеся в очереди сообщения
            while len( messageQueue ) > 0:
                message = messageQueue.pop( 0 )
                if( isinstance(message,str) ):
                    await connection.send_str( message )
                else:
                    await connection.send_bytes( message )

            # Ждем сообщений, дергая terminal.onTimer примерно раз в секунду
            message = await connection.receive(0.3)

            if message.type == WSMsgType.CLOSED:
                break
            elif message.type == WSMsgType.TEXT: # Получено текстовое сообщение
                m, p = parseMessage( message.data )
                if m == MSG_DISCONNECT:
                    connection.close()
                    break
                elif m == MSG_STATUS:
                    sendStatus()
                elif m == MSG_LVT_STATUS:
                    if terminal == None : break
                    sendMessage( MSG_LVT_STATUS, json.dumps(terminals.getState()) )
                elif m == MSG_TEXT:
                    if terminal == None : break
                    log(f'[{terminal.id}] {p}')
                elif m == MSG_TERMINAL :
                    id, password, version = split3( p )
                    terminal = terminals.authorize( id, password, version )
                    if terminal != None:
                        terminal.ipAddress = request.remote
                        terminal.version = version
                        await terminal.onConnect( messageQueue )
                        if terminal.autoUpdate==2 and version != VERSION :
                            await terminal.updateClient()
                    else:
                        print( 'Not authorized. Disconnecting' )
                        sendMessage( MSG_TEXT,'Wrong terminal Id or password' )
                        sendMessage( MSG_DISCONNECT )
                        break

                else:
                    logError( f'Unknown message: "{message}"' )
                    break
            # Получен аудиофрагмент приемлемой длины и терминал авторизован
            elif message.type == WSMsgType.BINARY and terminal != None:
                if not isActive:
                    isActive = True
                    # Сохраняем аудиофрагмент в буффере
                    voiceData = message.data
                    # Инициализация KaldiRecognizer занимает 30-100мс и не требует много памяти.

                    # Нефильтрованная распознавалка:
                    if model != None:
                        if( spkModel != None ): 
                            # Включить идентификацию по голосу
                            recognizer = KaldiRecognizer( model, VOICE_SAMPLING_RATE, spkModel )
                        else: 
                            # Не идентифицировать голос:
                            recognizer = KaldiRecognizer( model, VOICE_SAMPLING_RATE )
                    else:
                        recognizer = None

                    # Распознавалка "со словарем"
                    if  gModel != None:
                        gRecognizer = KaldiRecognizer(
                            gModel,
                            VOICE_SAMPLING_RATE,
                            json.dumps( list( terminal.getVocabulary() ), ensure_ascii=False )
                        )
                    else:
                        gRecognizer = None

                else:
                    # Сохраняем аудиофрагмент в буффере:
                    voiceData = message.data if voiceData==None else voiceData + message.data

                # Распознаем очередной фрагмент голоса
                (completed, text, signature) = await processVoice( 
                    message.data, 
                    recognizer if recognizer != None else gRecognizer
                )
                # (completed, text, signature) = await loop.run_in_executor( 
                #     pool, 
                #     processVoice, 
                #     message.data, 
                #     recognizer if recognizer != None else gRecognizer
                # )

                if signature != None : speakerSignature = signature

                # Если фраза завершена
                if completed:
                    # На входе есть хоть какой-то распознанный текст:
                    if len(text)>0:
                        # Если необходимо - распознаем речь повторно, используя словарь
                        if recognizer != None and gRecognizer != None :
                            (_, textFiltered, _) = await loop.run_in_executor( pool, processVoice, voiceData, gRecognizer )
                        else:
                            textFiltered = text

                        isProcessed = await terminal.onText( voiceData, textFiltered, text, speakerSignature )
                    else:
                        isProcessed = False
                        textFiltered = ''


                    # Журналируем голос (если заказано в настройках)
                    if (int(config.voiceLogLevel)>=3) or (int(config.voiceLogLevel)==2 and not isProcessed  ):
                        wavFileName = datetime.datetime.today().strftime(f'{terminal.id}_%Y%m%d_%H%M%S.wav')
                        wav = wave.open(os.path.join( config.voiceLogDir, wavFileName),'w')
                        wav.setnchannels(1)
                        wav.setsampwidth(2)
                        wav.setframerate(VOICE_SAMPLING_RATE)
                        wav.writeframesraw( voiceData )
                        wav.close()
                    else:
                        wavFileName = ''

                    # Журналируем расспознанный текст (если заказано)
                    if int(config.voiceLogLevel)>=3   or   not isProcessed and int(config.voiceLogLevel)>0 :
                        with open(os.path.join( config.voiceLogDir, 'voice.log'), 'a') as voiceLog:
                            dt = datetime.datetime.today().strftime(f'%Y-%m-%d %H:%M:%S')
                            voiceLog.write( f'{dt}\t{terminal.id}\t{wavFileName}\n' +
                                f'\t{text}\n' +
                                f'\t{textFiltered}\n' )

                    # Освобождаем память
                    if recognizer!=None : del(recognizer)
                    if gRecognizer!=None : del(gRecognizer)
                    recognizer = None
                    gRecognizer = None
                    del(voiceData)
                    voiceData = None
                    speakerSignature = None
                    isActive = False

                    # Переводим терминал в режим ожидания
                    sendMessage( MSG_IDLE )

        except asyncio.TimeoutError:
            # Примерно раз в секунду дергаем terminal.onTime()
            if terminal != None and int( time.time() ) != int( lastTickedOn ):
                lastTickedOn = time.time()
                await terminal.onTimer()
        except KeyboardInterrupt:
            onCtrlC()
            break
        except Exception as e:
            logError( f'Server thread {type(e).__name__}: {e}' )
        finally:
            pass
    if terminal is not None:
        terminal.onDisconnect()
    recognizer = None
#endregion

#region showHelp() #####################################################################
def showHelp():
    """Display usage instructions"""
    print( "usage: lvt_server.py [options]" )
    print( "Options available:" )
    print( " -h | --help                    show these notes" )
    print( " -l[=<file>] | --log[=<file>]   overwrite log file location defined in config file " )
#endregion

#region onCtrlC/ restart ###############################################################
def onCtrlC():
    loop.stop()
    print()
    print( "Terminating..." )
def restart():
    loop.stop()
    print()
    print( "Restarting..." )
    sys.exit(42)
#endregion

#region Main ###########################################################################

print()
print( f'Lite Voice Terminal Server v{VERSION}' )

config.init()

for arg in sys.argv[1:]:
    a = arg.strip().lower()
    if ( a == '-h' ) or ( a == '--help' ) or ( a == '/?' ) :
        showHelp()
        exit( 0 )
    elif ( a.startswith('-c=') or a.startswith('--config=') ) :
        #config parameter is already processed
        pass
    else:
        fatalError( f'Invalid command line argument: "{arg}"' )


persistent_state.restore()

entities.init()
terminals.init()
speakers.init()

sslContext = None

print( f'Listening port: {config.serverPort}' )
if( bool(config.sslCertFile) and bool( config.sslKeyFile ) ):
    print( f'Connection: Secured' )
    try:
        sslContext = ssl.SSLContext( ssl.PROTOCOL_TLS_SERVER )
        sslContext.load_cert_chain( config.sslCertFile, config.sslKeyFile )
    except Exception as e:
        fatalError( f'Loading certificates {type(e).__name__}: {e}' )
else:
    print( f'Connection: Unsecured' )

print( f'Voice model: {config.model}' )
print( f'Full voice model: {config.fullModel}' )

if bool( config.spkModel ):
    print( f'Speaker identification model: {config.spkModel}' )
else:
    print( 'Speaker identification disabled' )

#region Load models
model = None
gModel = None
spkModel = None
if bool(config.model):
    print()
    print("=========== Загрузка основной голосовой модели ===========")
    model = Model( config.model )
    if model == None: fatalError(f'Ошибка при загрузке голосовой модели {config.model}')

if bool(config.gModel):
    if config.gModel==config.model :
        gModel = model
    else:
        print()
        print("===== Загрузка модели для распознавания со словарем ======")
        gModel = Model( config.gModel )
        if gModel == None: fatalError(f'Ошибка при загрузке голосовой модели для распознавания со словарем {config.gModel}')

if bool(config.spkModel):
    print("======== Загрузка модели для идентификации голоса ========")
    spkModel = SpkModel( config.spkModel )
    if spkModel == None: fatalError(f'Ошибка при загрузке модели идентификации голоса {config.spkModel}')

print("============== Загрузка моделей завершена ================")
print()

# Set log level to reduce Kaldi/Vosk spuffing
SetLogLevel( -1 )


#endregion

# Main server loop
try:
    pool = concurrent.futures.ThreadPoolExecutor( config.recognitionThreads )
    loop = asyncio.get_event_loop()
 
    app = web.Application()
    app.add_routes([web.get('', server)])    
    app.add_routes([web.get('/api', api.server)])    
    app.add_routes([web.get('/api/', api.server)])
    web.run_app(
        app,
        host=config.serverAddress,
        port=config.serverPort,
        ssl_context = sslContext
        )

except KeyboardInterrupt:
    onCtrlC()
except Exception as e: 
    logError( f'Main terminal {type(e).__name__}: {e}' )
finally:
    persistent_state.save()

#endregion
