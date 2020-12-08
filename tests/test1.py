#!/usr/bin/env python3
import json
import os
import sys
import asyncio
import ssl
import pathlib
import websockets
import logging
import time
from lvt.const import *
from lvt.protocol import *
from lvt.server.grammar import *
from lvt.server.config import Config 
from lvt.server.terminal import Terminal
from lvt.server.speaker import Speaker
from lvt.server.skill import Skill


def onText( text ):
    messageQueue.clear()
    print( f'>>> Распознавание "{text}"' )
    words = wordsToList( text )
    text = ""
    for w in words :
        text += ( ' ' if text != '' else '' ) + w
        terminal.onText( text, False )
    print( '>>> Анализ фразы' )
    terminal.onText( text, True )
    print( f'>>> Сообщений в очереди клиента: {len(messageQueue)}' )
    if len( terminal.locations ) > 0 :
        locations = ', '.join( terminal.locations )
        print( f'>>> Локации: {locations}' )

    messageQueue.clear()
    print()


def testAppealDetector():
    print( '***** AppealDetectorSkill tests' )
    onText( 'Ехал грека через реку' )
    onText( 'слушай, мажордом, сделай что-нибудь!' )
    onText( "слушай, алиса..." )
    onText( "сделай уже что нибудь!" )

def testAcronym():
    print( '***** AcronymaExpanderSkill tests' )
    onText( "слушай мажордом выключи роберта" )

def testOneWordCommandSkill():
    print( '***** OneWordCommandSkill tests' )
    onText( 'алиса, свет!' )

def testLocationExtractor():
    print( '***** LocationExtractorSkill tests' )
    onText( 'слушай мажордом включи свет на кухне и в туалете' )





#set project folder to correct value
ROOT_DIR = os.path.abspath( os.path.join( os.path.dirname( __file__ ),'../' ) )

config = Config( 'lvt_server.cfg' )

Terminal.initialize( config )
Speaker.initialize( config )

messageQueue = list()

terminal = Terminal.authorize( 'testterminal', 'Password' )
terminal.logLevel = LOGLEVEL_VERBOSE
terminal.onConnect( messageQueue )

testAppealDetector()
testAcronym()
testOneWordCommandSkill()
testLocationExtractor()



terminal.onDisconnect()
