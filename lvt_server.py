#!/usr/bin/env python3 
import json
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
from lvt.server.entities import *
from lvt.server.terminal import *
import lvt.server.speakers as speakers


### processChunk() #####################################################################
#region
#def processVoice( waveChunk, recognizer: KaldiRecognizer):
#    """ Recognize audio chunk and process with terminal.onText() """
#    text = ''
#    final = False
#    try:
#        final = recognizer.AcceptWaveform( waveChunk )
#        if final: 
#            j = json.loads( recognizer.FinalResult() )
#            text = str( j['text'] ).strip() if 'text' in j else ''
#        else:
#            j = json.loads( recognizer.PartialResult() )
#            text = str( j['partial'] ).strip() if 'partial' in j else ''

#    except KeyboardInterrupt as e:
#        onCtrlC()
#        raise e
#    except Exception as e:
#        logError( f'Exception processing waveform chunk : {e}' )
#    return (final, text)


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
### websockServer ######################################################################
#region
async def websockServer( connection, path ):
    """Main service thread - websock server implementation """
    global model
    global spkModel
    global fullModel
    # Kaldi speech recognizer objects
    recognizer = None
    # Kaldi speaker identification object
    recognizerUncut = None
    # Currently connected Terminal
    terminal = None

    aNames = wordsToList(config.assistantNames)

    # temp var to track Terminal
    vocabulary = ''
    messageQueue = list()
    lastTickedOn = time.time()
    message = None
    voiceData = None
    completed = False
    isAppealed = False
    text = ''
    textUncut = ''
    speakerSignature = None
    
    
    def sendDatagram( data ):
        messageQueue.append( data )

    def sendMessage( msg:str, p1:str=None, p2:str=None ):
        sendDatagram( MESSAGE( msg,p1,p2 ) )

    def sendStatus():
        status = json.dumps(terminal.getStatus()) if terminal != None else '{"Terminal":"?","Name":"Not Registered","Connected":"false"}'
        sendMessage( MSG_STATUS, status )

    #def createFilteredRecognizer():
    #    return None

    #def createFullRecognizer():
    #    return None

    #def createAppealRecognizer():
    #    return getFilteredRecognizer()

    try:
        while True: # <== Breaking out of here will close connection
            while len( messageQueue ) > 0:
                await connection.send( messageQueue[0] )
                messageQueue.pop( 0 )

            if( terminal != None ):
                # Инициализация KaldiRecognizer занимает 30-100мс и не требует много памяти.

                ## Убеждаемся, что первичная распознавалка создана с актуальным словарем
                #v = terminal.getVocabulary()
                #if recognizer == None or vocabulary != v :
                #    vocabulary = v
                #    # Основная распознавалка с фильтрацией по словарю:
                #    recognizer = KaldiRecognizer( model, VOICE_SAMPLING_RATE, json.dumps( list( vocabulary ), ensure_ascii=False ) )
                #    words = normalizeWords( text )

                # Создаем основную, нефильтрованную распознавалку
                if recognizer == None :
                    # Вычисляем базовую модель модель:
                    m = fullModel if fullModel != None else model

                    if( spkModel != None ): 
                        # Включить идентификацию по голосу
                        recognizer = KaldiRecognizer( m, VOICE_SAMPLING_RATE, spkModel )
                    else: 
                        # Не идентифицировать голос:
                        recognizer = KaldiRecognizer( m, VOICE_SAMPLING_RATE )

            # Ждем сообщений, дергая terminal.onTimer примерно раз в секунду
            message = None
            while message == None:
                try:
                    # Примерно раз в секунду дергаем terminal.onTime()
                    if terminal != None and int( time.time() ) != int( lastTickedOn ):
                        lastTickedOn = time.time()
                        terminal.onTimer()
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
                    sendMessage( MSG_LVT_STATUS, json.dumps(getLVTStatus()) )
                elif m == MSG_TEXT:
                    if terminal == None : break
                    log(f'[{terminal.id}] {p}')
                elif m == MSG_TERMINAL :
                    id, password, version = split3( p )
                    terminal = TerminalAuthorize( id, password, version )
                    if terminal != None:
                        terminal.ipAddress = connection.remote_address[0]
                        terminal.onConnect( messageQueue )
                        if terminal.autoUpdate==2 and version != VERSION :
                            terminal.updateClient()
                    else:
                        print( 'Not authorized. Disconnecting' )
                        sendMessage( MSG_TEXT,'Wrong terminal Id or password' )
                        break

                else:
                    printError( f'Unknown message: "{message}"' )
                    break
            # Получен аудиофрагмент приемлемой длины и терминал авторизован и 
            elif terminal != None and len(message)>=4000 and len(message)<=64000 :
                # Сохраняем аудиофрагмент в буффере:
                voiceData = message if voiceData==None else voiceData + message

                # Распознаем очередной фрагмент голоса
                (completed, text, signature) = await loop.run_in_executor( pool, processVoice, message, recognizer )
                if signature != None : speakerSignature = signature
                # Если фраза завершена и на входе есть хоть какой-то текст:
                if completed and len(text)>0:
                    # Создаем словарную распознавалку:
                    recognizerFiltered = KaldiRecognizer( model, VOICE_SAMPLING_RATE, json.dumps( list( terminal.getVocabulary() ), ensure_ascii=False ) )
                    # Распознаем фразу со словарем
                    (_, textFiltered, _) = await loop.run_in_executor( pool, processVoice, voiceData, recognizerFiltered )
                    recognizerFiltered = None

                    isProcessed = terminal.onText( voiceData, textFiltered, text, speakerSignature )

                    # Журналируем голос (если заказано в настройках)
                    if (int(config.voiceLogLevel)>=2) or (not processed and int(config.voiceLogLevel)>0 ):
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
                    if int(config.voiceLogLevel)>=3   or   not processed and int(config.voiceLogLevel)>0 :
                        with open(os.path.join( config.voiceLogDir, 'voice.log'), 'a') as voiceLog:
                            dt = datetime.datetime.today().strftime(f'%Y-%m-%d %H:%M:%S')
                            voiceLog.write( f'{dt}\t{terminal.id}\t{wavFileName}\n' +
                                f'\t{text}\n' +
                                f'\t{textFiltered}\n' )

                    voiceData = None
                    speakerSignature = None

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

                #    if isAppealed:
                #        (textUncut, speakerSignature) = await loop.run_in_executor( pool, processVoiceUncut, voiceData, recognizerUncut )
                #else:
                #    (completed, text) = await loop.run_in_executor( pool, processVoice, message, recognizer )
                #    (textUncut, speakerSignature) = await loop.run_in_executor( pool, processVoiceUncut, message, recognizerUncut )


                   

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
            printError( f'{tn} disconnected by error' )
        elif isinstance( e, KeyboardInterrupt ):
            onCtrlC()
        else:
            printError( f'{tn}: unhandled exception {e}' )
    finally:
        try: terminal.onDisconnect()
        except: pass
        recognizer = None
        spkRecognizer = None
#endregion
### apiServer ######################################################################
async def apiServer( reader, writer ):
    data = await reader.readuntil(b'\0')
    response = 'Ok'
    try:
        message = data.decode().strip('\0 \r\n')
        if isinstance( message, str ): # Получено строковое сообщение
            m, jsn = split2( message )
            data = json.loads( jsn )
            terminalId = data['terminal'] if 'terminal' in data else ''
            message = data['message'] if 'message' in data else ''
            terminal =  TerminalFind( terminalId ) if terminalId else None

            if m == MSG_API_STATUS : 
                response = json.dumps(getLVTStatus())
            elif terminal == None:
                response = 'Invalid Terminal Id'
            elif not terminal.isConnected:
                response = 'Terminal is Offline'
            elif m == MSG_API_SAY:
                if message :
                    terminal.say( message )
                else:
                    response = 'Message is empty'
            elif m == MSG_API_ASK :
                terminal.answerPrefix = data['answerPrefix'] if 'answerPrefix' in data else ''
                if message:
                    terminal.say( message )
                terminal.changeTopic( TOPIC_MD_ASK )
            elif m == MSG_API_YESNO :
                terminal.answerPrefix = data['answerPrefix'] if 'answerPrefix' in data else ''
                terminal.changeTopic( "YesNo", \
                    message=message,
                    topicYes = TOPIC_MD_YES,
                    topicNo = TOPIC_MD_NO,
                    topicCancel = TOPIC_MD_CANCEL
                )
            else:
                response = 'Bad Command'
    except Exception as e:
        response = f'Internal LVT error: {e}'
    response = (response+'').encode()
    writer.write( response)
    writer.close()



### showHelp() #########################################################################
#region
def showHelp():
    """Display usage instructions"""
    print( "usage: lvt_server.py [options]" )
    print( "Options available:" )
    print( " -h | --help                    show these notes" )
    print( " -l[=<file>] | --log[=<file>]   overwrite log file location defined in config file " )

#endregion
### onCtrlC/ restart ###################################################################
#region
def onCtrlC():
    TerminalDispose()
    loop.stop()
    print()
    print( "Terminating..." )
def restart():
    TerminalDispose()
    loop.stop()
    print()
    print( "Restarting..." )
    sys.exit(42)

#endregion
### Main program #######################################################################
#region
#First thing first: save store script' folder as ROOT_DIR:

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


Entities.initialize()
TerminalInit()
speakers.init()


# Set log level to reduce Kaldi/Vosk spuffing
SetLogLevel( -1 )
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
model = Model( config.model )
fullModel = Model( config.fullModel ) if bool(config.fullModel) and config.fullModel != config.model else None
spkModel = SpkModel( config.spkModel ) if bool(config.spkModel) else None
#endregion

# Main server loop
try:
    pool = concurrent.futures.ThreadPoolExecutor( config.recognitionThreads )
    lvtServer = websockets.serve( websockServer, config.serverAddress, config.serverPort, ssl=sslContext )
    lvtApiServer = asyncio.start_server( apiServer, config.serverAddress, config.apiServerPort )
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete( lvtApiServer )
    loop.run_until_complete( lvtServer )
    loop.run_forever()
except KeyboardInterrupt:
    onCtrlC()
except Exception as e: 
    printError( f'Exception in main terminal loop {e}' )

#endregion
