#!/usr/bin/env python3 
import json
from logging import fatal
import os
import sys
import asyncio
import ssl

import websockets
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
def processVoice( waveChunk, recognizer: KaldiRecognizer):
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
async def websockServer( connection, path ):
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
    
    def sendDatagram( data ):
        messageQueue.append( data )

    def sendMessage( msg:str, p1:str=None, p2:str=None ):
        sendDatagram( MESSAGE( msg,p1,p2 ) )

    def sendStatus():
        status = json.dumps(terminal.getState()) if terminal != None else '{"Terminal":"?","Name":"Not Registered","Connected":"false"}'
        sendMessage( MSG_STATUS, status )

    try:
        while True: # <== Breaking out of here will close connection
            while len( messageQueue ) > 0:
                await connection.send( messageQueue[0] )
                messageQueue.pop( 0 )

            # Ждем сообщений, дергая terminal.onTimer примерно раз в секунду
            message = None
            while message == None:
                try:
                    # Примерно раз в секунду дергаем terminal.onTime()
                    if terminal != None and int( time.time() ) != int( lastTickedOn ):
                        lastTickedOn = time.time()
                        await terminal.onTimer()
                        # Отправляем новые сообщения клиенту, если они
                        # появились
                        while len( messageQueue ) > 0:
                            await connection.send( messageQueue[0] )
                            messageQueue.pop( 0 )

                    # Получаем сообщение или голосовой поток от клиента
                    message = await asyncio.wait_for( connection.recv(), timeout=0.2 )
                except asyncio.TimeoutError:
                    message = None

            if isinstance( message, str ): # Получено сообщение
                m, p = parseMessage( message )
                if m == MSG_DISCONNECT:
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
                        terminal.ipAddress = connection.remote_address[0]
                        terminal.version = version
                        await terminal.onConnect( messageQueue )
                        if terminal.autoUpdate==2 and version != VERSION :
                            await terminal.updateClient()
                    else:
                        print( 'Not authorized. Disconnecting' )
                        sendMessage( MSG_TEXT,'Wrong terminal Id or password' )
                        break

                else:
                    logError( f'Unknown message: "{message}"' )
                    break
            # Получен аудиофрагмент приемлемой длины и терминал авторизован
            elif terminal != None and len(message)>=4000 and len(message)<=64000 :
                if not isActive:
                    isActive = True
                    # Сохраняем аудиофрагмент в буффере
                    voiceData = message
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
                    voiceData = message if voiceData==None else voiceData + message

                # Распознаем очередной фрагмент голоса
                (completed, text, signature) = await loop.run_in_executor( 
                    pool, 
                    processVoice, 
                    message, 
                    recognizer if recognizer != None else gRecognizer
                )

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



                #if not isAppealed and not terminal.isAppealed:
                #    (completed, text) = await loop.run_in_executor( pool, processVoice, message, recognizer )
                #    if len(str(text))>0:
                #        # Проверка, не содержится ли в аудиофрагменте обращения к ассистенту
                #        words = wordsToList(normalizeWords( text ))
                #        for w in words:
                #            if oneOfWords( normalFormOf(w), aNames ):
                #                isAppealed = True

                   

        sendMessage( MSG_DISCONNECT )
        # send pending messages before disconnecting
        while len( messageQueue ) > 0:
            await connection.send( messageQueue[0] )
            messageQueue.pop( 0 )

    except Exception as e:
        tn = f'Terminal {terminal.name}' if terminal != None else 'Session '
        if isinstance( e, websockets.exceptions.ConnectionClosedOK ) :
            print( f'{tn} disconnected' )
        elif isinstance( e, websockets.exceptions.ConnectionClosedError ):
            logError( f'{tn} disconnected by error' )
        elif isinstance( e, KeyboardInterrupt ):
            onCtrlC()
        else:
            logError( f'{tn}: unhandled exception {e}' )
    finally:
        try: terminal.onDisconnect()
        except: pass
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
        sslContext.load_cert_chain( os.path.join( ROOT_DIR, config.sslCertFile ), os.path.join( ROOT_DIR, config.sslKeyFile ) )
    except Exception as e:
        sslContext = None
        print( f'Error loading certificate files: {e}' )
        exit( 1 )
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

    lvtServer = websockets.serve( websockServer, config.serverAddress, config.serverPort, ssl=sslContext )
    lvtApiServer = websockets.serve( api.server, config.serverAddress, config.apiServerPort )
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete( lvtApiServer )
    loop.run_until_complete( lvtServer )
    loop.run_forever()
except KeyboardInterrupt:
    onCtrlC()
except Exception as e: 
    logError( f'Exception in main terminal loop {e}' )
finally:
    persistent_state.save()

#endregion
