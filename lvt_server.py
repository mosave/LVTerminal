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
from lvt.server.terminal_factory import TerminalFactory
from lvt.server.state_machine import StateMachine
from lvt.server.speaker import Speaker
from lvt.server.speakers import Speakers

########################################################################################
#                               Globals initialization
#region
#First thing first: save store script' folder as ROOT_DIR:
ROOT_DIR = os.path.abspath( os.path.dirname( __file__ ) )

print( 'Light Voice Terminal server' )
SetLogLevel( -1 )
sslContext = None

config = Config( os.path.splitext( os.path.basename( __file__ ) )[0] + '.cfg' )

#TTS.setConfig( config )
Terminal.setConfig( config )
StateMachine.setConfig( config )
Speakers.setConfig( config )

terminals = Terminal.loadAllTerminals()

print( f'Listening port: {config.serverPort}' )
if( len( config.sslCertFile ) > 0 and len( config.sslKeyFile ) > 0 ):
    print( f'Connection: Secured' )
    try:
        print( config.sslCertFile )
        print( config.sslKeyFile )
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
model = Model( config.model )
fullModel = Model if config.model == config.fullModel else Model( config.fullModel )
spkModel = SpkModel( config.spkModel ) if len( config.spkModel ) > 0 else None

#endregion
########################################################################################
def processChunk( terminal: Terminal, recognizer: KaldiRecognizer, spkRecognizer: KaldiRecognizer, message: str ):
    result = False
    try:
        text = ''

        if spkRecognizer != None and terminal.speaker == None :
            # Current speaker identification
            if spkRecognizer.AcceptWaveform( message ):
                j = json.loads( spkRecognizer.FinalResult() )
                # Get speaker footprpint
                spk = j["spk"] if 'spk' in j else []
                if len( spk ) > 0 :
                    # Speakers database
                    speakers = Speakers()
                    terminal.speaker = speakers.identify( spk )

        try:
            # Speech recognition
            result = recognizer.AcceptWaveform( message )
            if result: 
                #print(recognizer.FinalResult())
                j = json.loads( recognizer.FinalResult() )
                text = j['text'].strip()
            else:
                #print(recognizer.PartialResult())
                j = json.loads( recognizer.PartialResult() )
                text = j['partial'].strip()

            if len( text ) > 0 : terminal.onText( text, result )
        except KeyboardInterrupt as e:
            loop.stop()
        except Exception as e: 
            print( f'Exception processing AcceptWaveForm={result}: {e}' )
    except KeyboardInterrupt as e:
        loop.stop()
        raise e
    except Exception as e:
        print( f'Exception processing chunk: {e}' )
    return result
########################################################################################
async def Server( connection, path ):
    global terminals
    global model
    global spkModel
    # Kaldi speech recognizer objects
    recognizer = None
    # Kaldi speaker identification object
    spkRecognizer = None
    # Currently connected Terminal
    terminal : Terminal = None
    # temp var to track Terminal
    words = '-'
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
                w = terminal.getVocabulary()
                if recognizer == None or words != w :
                    words = w
                    if len( words ) > 0 : # Фильтрация по словарю:
                        recognizer = KaldiRecognizer( model, config.sampleRate, json.dumps( words.split( ' ' ), ensure_ascii=False ) )
                        if( spkModel != None ): 
                            spkRecognizer = KaldiRecognizer( model, spkModel, config.sampleRate )
                    else: # Распознование без использования словаря
                        recognizer = KaldiRecognizer( fullModel, config.sampleRate )
                        if( spkModel != None ):
                            spkRecognizer = KaldiRecognizer( fullModel, spkModel, config.sampleRate )

            # Ждем сообщений, дергая terminal.onTimer примерно раз в секунду
            message = None
            while message == None:
                try:
                    if terminal != None and time.time() - lastTickedOn > 0.9:
                        lastTickedOn = time.time()
                        terminal.onTimer()
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
                    id, password = split2( p )
                    id = str(id).lower()
                    print(f'{id} / {password}')
                    if id in terminals and terminals[id].password == password:
                        terminal = terminals[id]
                        terminal.onConnect( messageQueue )
                        print( f'Terminal {id} ("{terminal.name}") authorized' )
                        #terminal.say("Терминал авторизован")
                        #terminal.play('/home/md/chord.wav')
                    else:
                        print( 'Not authorized. Disconnecting' )
                        sendMessage(MSG_TEXT,'Wrong terminal Id or password')
                        break

                else:
                    print( f'Unknown message: "{message}"' )
                    break
            else: # Получен байт-массив
                if terminal == None : break

                completed = await loop.run_in_executor( pool, processChunk, terminal, recognizer, spkRecognizer, message )
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
            loop.stop()
        else:
            print( f'{tn}: unhandled exception {e}' )
    finally:
        if terminal != None : terminal.onDisconnect()
        recognizer = None
        spkRecognizer = None
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
    print( f'\n\rLVT Server terminated by user' )
    loop.stop()
except Exception as e: 
    print( f'Exception in main terminal loop {e}' )
#endregion
########################################################################################
