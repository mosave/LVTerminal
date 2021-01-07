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
import datetime

sys.path.append(os.path.abspath( os.path.join( os.path.dirname( __file__ ),'../' ) ))

from lvt.const import *
from lvt.protocol import *
from lvt.logger import *
from lvt.server.grammar import *
from lvt.server.config import Config 
from lvt.server.mqtt import MQTT
from lvt.server.entities import Entities
from lvt.server.devices import Devices
from lvt.server.terminal import Terminal
from lvt.server.speaker import Speaker
from lvt.server.skill import Skill

def abort(msg:str):
    print(f'>>> Тест не прошел: {msg}')
    sys.exit()

def onText( text:str, controlPhrase : str=None ):
    messageQueue.clear()
    logs.clear()
    print( f'>>> Распознавание "{text}"' )
    words = wordsToList( text )
    text = ""
    for w in words :
        text += ( ' ' if text != '' else '' ) + w
        terminal.onPartialText( text )
    print( '>>> Анализ фразы' )
    terminal.onText( text )
    print( f'>>> Сообщений в очереди клиента: {len(messageQueue)}' )
    if len( terminal.locations ) > 0 :
        locations = ', '.join( terminal.locations )
        print( f'>>> Локации: {locations}' )

    messageQueue.clear()
    errors = 0
    for m in logs :
        if m.startswith('E '): errors += 1
    if errors >0 : 
        abort(f'Обнаружены ошибки: {errors}')
    if controlPhrase != None :
        if terminal.text.find(normalizeWords(controlPhrase)) <0 :
            abort(f'Не обнаружена контрольная фраза "{controlPhrase}"')

    print()

def checkIfSaid(phrase):
    phrase = normalizeWords(phrase)
    for m in logs :
        if m.startswith('D') and m.find('Say')>0 and normalizeWords(m).find(phrase)>0 : return True
    abort(f'Терминал не произнес ключевую фразу "{phrase}"')


def testAppealDetector():
    logs.clear()
    print( '***** AppealDetectorSkill tests' )
    onText( 'слушай, мажордом, сделай что-нибудь!', 'мажордом сделай что-нибудь' )
    onText( 'слушай, алиса...' )
    if( terminal.topic != 'WaitCommand') : abort('Терминал не перешел в режим ожидания команды')
    onText( 'сделай уже что нибудь!', 'алиса сделай уже что нибудь' )
    if( terminal.topic != TOPIC_DEFAULT) : abort('Терминал не вернулся в нормальный режим')

def testAcronym():
    logs.clear()
    print( '***** AcronymaExpanderSkill tests' )
    Entities().acronyms.append(['зелёный вентилятор ','махатель лопастями'])
    onText( 'слушай мажордом выключи махателя лопастями','зелёный вентилятор' )

def testOneWordCommandSkill():
    logs.clear()
    print( '***** OneWordCommandSkill tests' )
    onText( 'алиса, свет!', 'алиса включи свет')

def testLocationExtractor():
    logs.clear()
    print( '***** LocationExtractorSkill tests' )
    onText( 'слушай мажордом включи свет на кухне и в туалете', 'включи свет' )
    if ', '.join( terminal.locations ) != 'кухня, туалет' : abort('Неправильно извлечены локации')

def testParrotMode():
    logs.clear()
    print( '***** ParrotModeSkill tests' )
    onText( 'слушай мажордом повторяй за мной' )
    checkIfSaid('я буду повторять')
    if( terminal.topic != 'ParrotMode') : abort('Терминал не перешел в режим попугая')
    onText( 'Ехал грека через реку' )
    checkIfSaid('ехал грека через реку')
    onText( 'На мели мы лениво налима ловили' )
    checkIfSaid( 'На мели мы лениво налима ловили' )

    onText( 'Включи режим распознавания со словарем' )
    onText( 'Включи режим распознавания со словарем' )
    checkIfSaid( 'уже включен' )

    onText( 'Включи режим распознавания без словаря' )
    checkIfSaid( 'Выключаю режим распознавания со словарем' )

    onText( 'Перестань попугайничать' )
    checkIfSaid('режим попугая выключен')
    if( terminal.topic != TOPIC_DEFAULT) : abort('Терминал не вернулся в нормальный режим')

def testServerConfig():
    logs.clear()
    print( '***** ServerConfigSkill tests' )
    onText( 'слушай мажордом выключи режим распознавания со словарем' )
    onText( 'слушай мажордом включи режим распознавания со словарем' )
    checkIfSaid( 'Включаю режим распознавания со словарем' )
    onText( 'слушай мажордом включи режим распознавания без словаря' )
    checkIfSaid( 'Выключаю режим распознавания со словарем' )

def testYesNo():
    logs.clear()
    print( '***** YesNoSkill tests' )
    onText( 'алиса проверка да или нет' )
    checkIfSaid( 'Да или нет' )
    onText('Траливали набекрень')
    checkIfSaid( 'не поняла' )
    #onText( 'отмена' )
    onText( 'да, уверен' )
    checkIfSaid( 'Подтверждено' )

def testFindWordChain():
    logs.clear()
    print( '***** findWordChain() tests' )
    onText( 'алиса проверка поиска по шаблону' )
    checkIfSaid( 'Поиск по шаблону работает' )

def testTimeTeller():
    logs.clear()
    print( '***** TellTheTimeSkill tests' )
    onText( 'алиса скажи сколько сейчас времени' )
    checkIfSaid( transcribeTime(datetime.datetime.today()) )
    onText( 'алиса какое сегодня число' )
    checkIfSaid( transcribeDate(datetime.datetime.today()) )

def testMajorDoMo():
    logs.clear()
    print( '***** MajorDoMoSkill tests' )
    onText( 'Мажордом, обнови список устройств' )
    onText( 'Мажордом, включи свет в зале' )
    #checkIfSaid( transcribeDate(datetime.datetime.today()) )

def testOnOffSkill():
    logs.clear()
    print( '***** OnOffSkill() tests' )
    onText( 'эй алиса слушай выключи весь свет!' )
    onText( 'алиса свет!' )
    checkIfSaid( 'Поиск по шаблону работает' )


config = Config( 'lvt_server.cfg' )
config.logFileName = "logs/test_skills.log"
config.logLevel = logging.DEBUG
config.printLevel = logging.DEBUG

# hack - allow debug skill under no conditions:
config.skills['debugskill']['enable']=True

logs = list()
Logger.initialize( config )
Logger.setLogCapture(logs)
Grammar.initialize( config )
MQTT.initialize( config )
Entities.initialize( config )
Devices.initialize( config )
Terminal.initialize( config )
Speaker.initialize( config )


#d = Devices().devices['relayToilet']
#d.methods['on'].execute()
#d.methods['off'].execute()

messageQueue = list()

terminal = Terminal.authorize( 'test', 'Password', 'testscript' )
terminal.onConnect( messageQueue )

#print( transcribeDate(datetime.datetime.today()) )

#print( transcribeTime(datetime.datetime.today()) )


#print( transcribeNumber(28,{'nomn','ADJF'}) )

#_s=''
#w = parseWord('восемь')[0]
#t = w.tag
#for c in list(t.CASES) :
#    for p in list(t.PARTS_OF_SPEECH) :
#        for g in list(t.KNOWN_GRAMMEMES) :
#            s = w.inflect( {str(c),str(p), str(g)})
#            if s!=None :
#                s = s.word
#                if s=='восьмое' :
#                    print( f'{str(c)},{str(p)}, {str(g)}: ' + s )
#                _s = s
#        #for g in list(t.KNOWN_GRAMMEMES) :
#        #    print( f'{c}, {p}, {g}: ' + transcribeNumber(28,{str(c),str(p),str(g),'neut'},'декабря') )

#print( transcribeNumber(1000,{'gent'},'хомяк') )
#print( transcribeNumber(1111111,{'gent'}, 'хомяк') )

#print( transcribeNumber(123123123,{'gent'}, 'хомяк') )

testOnOffSkill()
#testMajorDoMo()

testAppealDetector()
testFindWordChain()
testAcronym()
testOneWordCommandSkill()
testLocationExtractor()
testParrotMode()
testServerConfig()
testYesNo()
testTimeTeller()


terminal.onDisconnect()

print('ALL SKILL TESTS PASSED!!!')
