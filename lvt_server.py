#!/usr/bin/env python3
import json
import os
import sys
import asyncio
import ssl
import pathlib
import websockets
import concurrent.futures
import logging
import time
from vosk import Model, SpkModel, KaldiRecognizer, SetLogLevel
from lvt.const import *
from lvt.protocol import *
from lvt.server.config import Config 
from lvt.server.terminal import Terminal
from lvt.server.speaker import Speaker

########################################################################################
#                               Globals initialization
#region
#First thing first: save store script' folder as ROOT_DIR:
ROOT_DIR = os.path.abspath( os.path.dirname( __file__ ) )

print( 'Light Voice Terminal server' )
SetLogLevel( -1 )
sslContext = None

config = Config( os.path.splitext( os.path.basename( __file__ ) )[0] + '.cfg' )

Terminal.initialize( config )
Speaker.initialize( config )

print( f'Listening port: {config.serverPort}' )
if( len( config.sslCertFile ) > 0 and len( config.sslKeyFile ) > 0 ):
    print( f'Connection: Secured' )
    try:
        sslContext = ssl.SSLContext( ssl.PROTOCOL_TLS_SERVER )
        sslContext.load_cert_chain( config.sslCertFile, config.sslKeyFile )
    except Exception as e:
        sslContext = None
        print( f'Error loading certificate files: {e}' )
        exit( 1 )
else:
    print( f'Connection: Unsecured' )

print( f'Number of recognition threads: {config.recognitionThreads}' )
print( f'Sampling rate: {config.sampleRate}' )
print( f'Voice model: {config.model}' )
print( f'Full voice model: {config.fullModel}' )

if( len( config.spkModel ) > 0 ):
    print( f'Speaker identification model: {config.spkModel}' )
else:
    print( 'Speaker identification disabled' )
print( f'Assistant Name(s): {config.assistantName}' )

#region Gpu part, uncomment if vosk-api has gpu support
#
# from vosk import GpuInit, GpuInstantiate
# GpuInit()
# def thread_init():
#     GpuInstantiate()
#endregion
model = Model( config.model ) if config.model != '' else None
fullModel = Model( config.fullModel ) if config.fullModel != '' and config.fullModel != config.model else None
spkModel = SpkModel( config.spkModel ) if config.spkModel != '' else None

#endregion
########################################################################################
def processChunk( 
        waveform, 
        terminal: Terminal, 
        recognizer: KaldiRecognizer, 
        spkRecognizer: KaldiRecognizer,
        usingVocabulary: bool
    ):
    text = ''
    final = False
    try:

        # Если включена идентификация говорящего - извлечь результаты распознавания с помощью spkRecognizer
        if spkRecognizer != None:
            final = spkRecognizer.AcceptWaveform( waveform )
            if final: # Фраза распознана полностью
                j = json.loads( spkRecognizer.FinalResult() )
                # Получить распознанный текст
                text = str(j['text']).strip() if 'text' in j else ''
                # Извлечь сигнатуру голоса:
                signature = j["spk"] if 'spk' in j else []
                if len( signature ) > 0 : # Идентифицировать говоращего по сигнатуре
                    #print(signature)
                    terminal.speaker = Speaker.identify( signature )
            else:
                # Получить распознанный текст
                j = json.loads( spkRecognizer.PartialResult() )
                text = str(j['partial']).strip() if 'partial' in j else ''

        # Если для распознавания используется словарь - распознаем текст повторно
        if spkRecognizer == None or usingVocabulary:
            final = recognizer.AcceptWaveform( waveform )
            if final: 
                j = json.loads( recognizer.FinalResult() )
                text = str(j['text']).strip() if 'text' in j else ''
            else:
                j = json.loads( recognizer.PartialResult() )
                text = str(j['partial']).strip() if 'partial' in j else ''

        if len( text ) > 0 : terminal.onText( text, final )

    except KeyboardInterrupt as e:
        onCtrlC()
        raise e
    except Exception as e:
        print( f'Exception processing waveform chunk : {e}' )
    return final
########################################################################################
async def Server( connection, path ):
    print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    global model
    global spkModel
    # Kaldi speech recognizer objects
    recognizer = None
    # Kaldi speaker identification object
    spkRecognizer = None
    # Currently connected Terminal
    terminal : Terminal = None
    # temp var to track Terminal
    vocabulary = ''
    messageQueue = list()
    lastTickedOn = time.time()
    def sendDatagram( data ):
        messageQueue.append( data )

    def sendMessage( msg:str, p1:str=None, p2:str=None ):
        sendDatagram( MESSAGE(msg,p1,p2 ) )

    def sendStatus():
        status = terminal.getStatus() if terminal != None else '{"Terminal":"?","Name":"Not Registered"}'
        sendMessage( MSG_STATUS, status )


    try:
        while True: # <== Breaking out of here will close connection
            while len( messageQueue ) > 0:
                await connection.send( messageQueue[0] )
                messageQueue.pop( 0 )

            if( terminal != None ):
                # Убеждаемся, что все распознавалки созданы и используется
                # актуальный словарь для фильтрации слов
                # Идентификация говорящего функционирует "поверх" основной
                # голосовой модели, поэтому
                # пересоздаем ее соответственно.
                # Инициализация распознавалок занимает от 30-100мс и не требует
                # много памяти.
                v = terminal.getVocabulary()
                if recognizer == None or vocabulary != v :
                    vocabulary = v
                    print (v)
                    if (len( vocabulary ) > 0) and model != None: # Фильтрация по словарю:
                        recognizer = KaldiRecognizer( model, config.sampleRate, json.dumps( vocabulary.split( ' ' ), ensure_ascii=False ) )
                        if( spkModel != None ): 
                            spkRecognizer = KaldiRecognizer( model, spkModel, config.sampleRate )
                    else: # Распознование без использования словаря
                        recognizer = KaldiRecognizer( fullModel if fullModel != None else model, config.sampleRate )
                        if( spkModel != None ):
                            spkRecognizer = KaldiRecognizer( fullModel if fullModel != None else model, spkModel, float(config.sampleRate) )

            # Ждем сообщений, дергая terminal.onTimer примерно раз в секунду
            message = None
            while message == None:
                try:
                    # Примерно раз в секунду дергаем terminal.onTime()
                    if terminal != None and int(time.time()) != int(lastTickedOn):
                        lastTickedOn = time.time()
                        terminal.onTimer()
                        # Отправляем новые сообщения клиенту, если они появились
                        while len( messageQueue ) > 0:
                            await connection.send( messageQueue[0] )
                            messageQueue.pop( 0 )

                    # Получаем сообщение или голосовой поток от клиента
                    message = await asyncio.wait_for( connection.recv(), timeout=0.2 )
                except asyncio.TimeoutError:
                    message = None

            if isinstance( message, str ): # Получено сообщение
                if terminal != None : terminal.lastActivity = time.time()
                m, p = parseMessage( message )
                if m == MSG_DISCONNECT:
                    break
                elif m == MSG_STATUS:
                    sendStatus()
                elif m == MSG_CONFIG:
                    if terminal == None : break
                    sendMessage( MSG_CONFIG, config.getJson() )
                elif m == MSG_TEXT:
                    if terminal == None : break
                    print(p)
                elif m == MSG_TERMINAL :
                    id, password, version = split3( p )
                    terminal = Terminal.authorize(id, password)
                    if terminal != None:
                        terminal.clientVersion = version
                        terminal.onConnect( messageQueue )
                        print( f'Terminal {id} ("{terminal.name}") authorized' )
                        #terminal.say("Терминал авторизован")
                        #terminal.play('/home/md/chord.wav')
                        if terminal.autoUpdate and version != VERSION :
                            if terminal.id == 'respeaker4' :
                                terminal.updateClient()
                            else:
                                # Уведомить об устаревании версии и спросить об обновлении.
                                pass

                    else:
                        print( 'Not authorized. Disconnecting' )
                        sendMessage(MSG_TEXT,'Wrong terminal Id or password')
                        break

                else:
                    print( f'Unknown message: "{message}"' )
                    break
            else: # Получен байт-массив
                if terminal == None : break

                completed = await loop.run_in_executor( pool, processChunk, message, terminal, recognizer, spkRecognizer, ( vocabulary !='' ) )
                if completed: sendMessage( MSG_IDLE )

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
            print( f'{tn} disconnected by error' )
        elif isinstance( e, KeyboardInterrupt ):
            onCtrlC()
        else:
            print( f'{tn}: unhandled exception {e}' )
    finally:
        print('fin')
        if terminal != None : terminal.onDisconnect()
        recognizer = None
        spkRecognizer = None

def onCtrlC():
    Terminal.dispose()
    Speaker.dispose()
    loop.stop()
    print()
    print( "Terminating..." )
########################################################################################
# Main server loop
#region
try:
    pool = concurrent.futures.ThreadPoolExecutor( config.recognitionThreads )
    start_server = websockets.serve( Server, config.serverAddress, config.serverPort, ssl=sslContext )
    loop = asyncio.get_event_loop()
    loop.run_until_complete( start_server )
    loop.run_forever()
except KeyboardInterrupt:
    onCtrlC()
except Exception as e: 
    print( f'Exception in main terminal loop {e}' )
#endregion
########################################################################################
