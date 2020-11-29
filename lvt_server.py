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
from lvt.server.speakers import Speaker, Speakers

########################################################################################
#                               Globals initialization
#region
print( 'Light Voice Terminal server' )
SetLogLevel( -1 )
sslContext = None
terminals = []

config = Config( os.path.splitext( os.path.basename( __file__ ) )[0] + '.cfg' )

Terminal.setConfig( config, terminals )
Speakers.setConfig( config )

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
def processChunk( terminal, recognizer, spkRecognizer, message ):
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
                if len( text ) > 0 : terminal.processFinal( text )
            else:
                #print(recognizer.PartialResult())
                j = json.loads( recognizer.PartialResult() )
                text = j['partial'].strip()
                if len( text ) > 0 : terminal.processPartial( text )
        except Exception as e: 
            print(f'Exception processing AcceptWaveForm={result}: {e}')

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
    terminal = None
    # temp var to track Terminal
    words = '-'

    async def sendStatus():
        status = terminal.getStatus() if terminal != None else '{"Terminal":"","Name":"Not Registered"}'
        await connection.send( MESSAGE( MSG_STATUS, status ) )

    try:
        while True:
            if( terminal != None ):
                w = terminal.getDictionaryWords().strip()
                if recognizer == None or ( words != w ):
                    words = w
                    if len( words ) > 0 :
                        recognizer = KaldiRecognizer( model, config.sampleRate, json.dumps( words.split( ' ' ), ensure_ascii=False ) )
                        if( spkModel != None ):
                            spkRecognizer = KaldiRecognizer( model, spkModel, config.sampleRate )
                    else:
                        recognizer = KaldiRecognizer( fullModel, config.sampleRate )
                        if( spkModel != None ):
                            spkRecognizer = KaldiRecognizer( fullModel, spkModel, config.sampleRate )

            message = await connection.recv()

            if isinstance( message, str ):
                if terminal != None : terminal.lastActivity = time.time()
                m, p = parseMessage( message )
                if m == MSG_DISCONNECT:
                    break
                elif m == MSG_CONFIG:
                    await connection.send( MESSAGE( MSG_CONFIG, config.getJson() ) )
                elif m == MSG_STATUS:
                    await sendStatus()
                elif m == MSG_TERMINAL_NAME:
                    if terminal == None : break
                    if p != None :
                        terminal.name = p
                        print( f'Terminal #{terminal.id} renamed to {terminal.name}' )
                    await sendStatus()
                elif m == MSG_TERMINAL :
                    id, password = split2(p)
                    try: id = int( id )
                    except: id = 0

                    print( f'Registering Terminal #{id}, password "{password}"' )

                    if id<=0 or password != 'Password':
                        print( 'Not authorized. Disconnecting' )
                        break

                    for t in terminals:
                        if t.id == id:
                            terminal = t
                            break
                    if terminal == None:
                        print( f'Registering terminal #{id}' )
                        terminal = Terminal( id )
                        terminals.append( terminal )
                    else:
                        print( f'Reconnecting terminal #{id}' )

                    await sendStatus()

                else:
                    print( f'Unknown message: "{message}"' )

            else:
                if terminal != None:
                    completed = await loop.run_in_executor( pool, processChunk, terminal, recognizer, spkRecognizer, message )
                    while len( terminal.messages ) > 0:
                        await connection.send( terminal.messages[0] )
                        terminal.messages.pop( 0 )
                    if completed:
                        await connection.send( MSG_IDLE )

    except Exception as e:
        tn = f'Terminal {terminal.name}' if terminal != None else 'Session '
        if isinstance( e, websockets.exceptions.ConnectionClosedOK ) :
            print( f'{tn} disconnected' )
        elif isinstance( e, websockets.exceptions.ConnectionClosedError ):
            print( f'{tn} disconnected by error' )
        else:
            print( f'{tn}: unhandled exception {e}' )
    finally:
        
        recognizer = None
        spkRecognizer = None
########################################################################################
pool = concurrent.futures.ThreadPoolExecutor( config.recognitionThreads )
start_server = websockets.serve( Server, config.serverAddress, config.serverPort, ssl=sslContext )

loop = asyncio.get_event_loop()
loop.run_until_complete( start_server )
loop.run_forever()

########################################################################################
