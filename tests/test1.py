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

sys.path.append(os.path.abspath( os.path.join( os.path.dirname( __file__ ),'../' ) ))

from lvt.const import *
from lvt.protocol import *
from lvt.server.grammar import *
from lvt.server.config import Config 
from lvt.server.terminal import Terminal
from lvt.server.speaker import Speaker
from lvt.server.skill import Skill

def abort(msg:str):
    print(f'>>> Тест не прошел: {msg}')
    sys.exit()

def onText( text:str, controlPhrase : str=None ):
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
    errors = 0
    for m in terminal.logs :
        if m.startswith('E '): errors += 1
    if errors >0 : abort(f'Обнаружены ошибки: {errors}')
    if controlPhrase != None :
        if terminal.text.find(normalizeWords(controlPhrase)) <0 :
            abort(f'Не обнаружена контрольная фраза "{controlPhrase}"')

    print()

def checkIfSaid(phrase):
    phrase = normalizeWords(phrase)
    for m in terminal.logs :
        if m.startswith('D Say') and normalizeWords(m).find(phrase)>0 : return True
    abort(f'Терминал не произнес ключеву фразу "{phrase}"')


def testAppealDetector():
    print( '***** AppealDetectorSkill tests' )
    onText( 'Ой, ехал некогда Грека через какую-то реку. И ведь доехал же! ', \
          'ехал грека через какую-то реку и доехал')
    onText( 'слушай, мажордом, сделай что-нибудь!', 'мажордом сделай что-нибудь' )
    onText( 'слушай, алиса...' )
    if( terminal.topic != 'WaitCommand') : abort('Терминал не перешел в режим ожидания команды')
    onText( 'сделай уже что нибудь!', 'алиса сделай что нибудь' )
    if( terminal.topic != '') : abort('Терминал не вернулся в нормальный режим')

def testAcronym():
    print( '***** AcronymaExpanderSkill tests' )
    terminal.acronyms.append(['зелёный вентилятор ','махатель лопастями'])
    onText( 'слушай мажордом выключи махателя лопастями','зелёный вентилятор' )

def testOneWordCommandSkill():
    print( '***** OneWordCommandSkill tests' )
    onText( 'алиса, свет!', 'алиса включи свет')

def testLocationExtractor():
    print( '***** LocationExtractorSkill tests' )
    onText( 'слушай мажордом включи свет на кухне и в туалете', 'включи свет' )
    if ', '.join( terminal.locations ) != 'кухня, туалет' : abort('Неправильно извлечены локации')

def testParrotMode():
    print( '***** ParrotModeSkill tests' )
    onText( 'слушай мажордом повторяй за мной' )
    checkIfSaid('я буду повторять')
    if( terminal.topic != 'ParrotMode') : abort('Терминал не перешел в режим попугая')
    onText( 'Ехал грека через реку' )
    checkIfSaid('ехал грека через реку')
    onText( 'На мели мы лениво налима ловили' )
    onText( 'Перестань попугайничать' )
    checkIfSaid('режим попугая выключен')
    if( terminal.topic != '') : abort('Терминал не вернулся в нормальный режим')



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
testParrotMode()



terminal.onDisconnect()
