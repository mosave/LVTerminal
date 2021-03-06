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
from lvt.config_parser import ConfigParser
from lvt.server.grammar import *
from lvt.server.config import Config 
from lvt.server.mqtt import MQTT
from lvt.server.entities import Entities
from lvt.server.devices import Devices
from lvt.server.terminal import Terminal
from lvt.server.speaker import Speaker
from lvt.server.skill import Skill

def abort(msg:str):
    print(f'>>> Тест не прошёл: {msg}')
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
        controlPhrase = normalizeWords(controlPhrase)
        found = False
        if terminal.text.find(controlPhrase) >=0 : found = True
        for m in logs :
            if normalizeWords(m).find(controlPhrase)>0 : 
                found = True
                break
        if not found:
            abort(f'Не обнаружена контрольная фраза "{controlPhrase}"')

    print()

def checkIfSaid(phrase):
    phrase = normalizeWords(phrase)
    for m in logs :
        if m.startswith('D') and m.find('Say')>0 and normalizeWords(m).find(phrase)>0 : return True
    abort(f'Терминал не произнёс ключевую фразу "{phrase}"')

    for m in logs :
        if normalizeWords(m).find(phrase)>0 : return True
    abort(f'В журнале не найдена ключевая запись "{phrase}"')


def testAppealDetector():
    logs.clear()
    print( '***** AppealDetectorSkill tests' )
    onText( 'слушай, мажордом, сделай что-нибудь!', 'мажордом сделай что-нибудь' )
    onText( 'слушай, алиса...' )
    if( terminal.topic != 'WaitCommand') : abort('Терминал не перешёл в режим ожидания команды')
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

def testLocationDetector():
    logs.clear()
    print( '***** LocationDetectorSkill tests' )
    onText( 'слушай мажордом включи свет на кухне и в туалете' )
    if ', '.join( terminal.locations ) != 'кухня, туалет' : abort('Неправильно извлечены локации')

def testParrotMode():
    logs.clear()
    print( '***** ParrotModeSkill tests' )
    onText( 'слушай мажордом повторяй за мной' )
    checkIfSaid('я буду повторять')
    if( terminal.topic != 'ParrotMode') : abort('Терминал не перешёл в режим попугая')
    onText( 'Ехал грека через реку' )
    checkIfSaid('ехал грека через реку')
    onText( 'На мели мы лениво налима ловили' )
    checkIfSaid( 'На мели мы лениво налима ловили' )

    onText( 'Включи режим распознавания со словарём' )
    onText( 'Включи режим распознавания со словарём' )
    checkIfSaid( 'уже включен' )

    onText( 'Включи режим распознавания без словаря' )
    checkIfSaid( 'Выключаю режим распознавания со словарём' )

    onText( 'Перестань за мной повторять' )
    checkIfSaid('режим попугая выключен')
    if( terminal.topic != TOPIC_DEFAULT) : abort('Терминал не вернулся в нормальный режим')

def testServerConfig():
    logs.clear()
    print( '***** ServerConfigSkill tests' )
    onText( 'слушай мажордом выключи режим распознавания со словарём' )
    onText( 'слушай мажордом включи режим распознавания со словарём' )
    checkIfSaid( 'Включаю режим распознавания со словарём' )
    onText( 'слушай мажордом включи режим распознавания без словаря' )
    checkIfSaid( 'Выключаю режим распознавания со словарём' )

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

    onText( 'алиса включи свет в ванной' )
    onText( 'алиса выключи свет слева' )

    onText( 'эй алиса слушай выключи весь свет!' )
    onText( 'алиса, включи свет здесь и на кухне' )
    onText( 'алиса, включи весь свет здесь и на кухне' )
    onText( 'алиса, включи весь свет в зале' )
    onText( 'алиса, выключи здесь свет' )
    onText( 'алиса, выключи свет везде' )
    onText( 'алиса, выключи свет во всех комнатах' )
    onText( 'алиса, включи свет слева' )

    checkIfSaid( 'Поиск по шаблону работает' )

ConfigParser.setConfigDir( os.path.join( ROOT_DIR, 'config.default' ) )

config = Config()
config.logFileName = "logs/test_skills.log"
config.logLevel = logging.DEBUG
config.printLevel = logging.DEBUG

# hack - allow debug skill under no conditions:
if 'debugskill' not in config.skills : config.skills['debugskill'] = {'enable':True}
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

terminal = Terminal.authorize( 'test', 'TestPassword', 'testscript' )
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

#testOnOffSkill()
#testMajorDoMo()

testAppealDetector()
testFindWordChain()
testAcronym()
testOneWordCommandSkill()
testLocationDetector()
testParrotMode()
testServerConfig()
testYesNo()
testTimeTeller()


terminal.onDisconnect()

print('ALL SKILL TESTS PASSED!!!')
