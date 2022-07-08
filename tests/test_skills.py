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
from lvt.server.entities import Entities
from lvt.server.terminal import Terminal
from lvt.server.speaker import Speaker
from lvt.server.skill import Skill

def abort(msg:str):
    print(f'>>> Тест не прошёл: {msg}')
    sys.exit()

async def onTextAsync( text:str, controlPhrase : str=None ):
    messageQueue.clear()
    logs.clear()
    print( f'>>> Распознавание "{text}"' )
    words = wordsToList( text )
    text = ""
    for w in words :
        text += ( ' ' if text != '' else '' ) + w
    print( '>>> Анализ фразы' )
    await terminal.onTextAsync( text )
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
    if controlPhrase is not None :
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
    await onTextAsync( 'слушай, мажордом, сделай что-нибудь!', 'мажордом сделай что-нибудь' )
    await onTextAsync( 'слушай, алиса...' )
    if( terminal.topic != 'WaitCommand') : abort('Терминал не перешёл в режим ожидания команды')
    await onTextAsync( 'сделай уже что нибудь!', 'алиса сделай уже что нибудь' )
    if( terminal.topic != TOPIC_DEFAULT) : abort('Терминал не вернулся в нормальный режим')

def testAcronym():
    logs.clear()
    print( '***** AcronymaExpanderSkill tests' )
    Entities().acronyms.append(['зелёный вентилятор ','махатель лопастями'])
    await onTextAsync( 'слушай мажордом выключи махателя лопастями','зелёный вентилятор' )

def testOneWordCommandSkill():
    logs.clear()
    print( '***** OneWordCommandSkill tests' )
    await onTextAsync( 'алиса, свет!', 'алиса включи свет')

def testLocationDetector():
    logs.clear()
    print( '***** LocationDetectorSkill tests' )
    await onTextAsync( 'слушай мажордом включи свет на кухне и в туалете' )
    if ', '.join( terminal.locations ) != 'кухня, туалет' : abort('Неправильно извлечены локации')

def testParrotMode():
    logs.clear()
    print( '***** ParrotModeSkill tests' )
    await onTextAsync( 'слушай мажордом повторяй за мной' )
    checkIfSaid('я буду повторять')
    if( terminal.topic != 'ParrotMode') : abort('Терминал не перешёл в режим попугая')
    await onTextAsync( 'Ехал грека через реку' )
    checkIfSaid('ехал грека через реку')
    await onTextAsync( 'На мели мы лениво налима ловили' )
    checkIfSaid( 'На мели мы лениво налима ловили' )

    await onTextAsync( 'Включи режим распознавания со словарём' )
    await onTextAsync( 'Включи режим распознавания со словарём' )
    checkIfSaid( 'уже включен' )

    await onTextAsync( 'Включи режим распознавания без словаря' )
    checkIfSaid( 'Выключаю режим распознавания со словарём' )

    await onTextAsync( 'Перестань за мной повторять' )
    checkIfSaid('режим попугая выключен')
    if( terminal.topic != TOPIC_DEFAULT) : abort('Терминал не вернулся в нормальный режим')

def testServerConfig():
    logs.clear()
    print( '***** ServerConfigSkill tests' )
    await onTextAsync( 'слушай мажордом выключи режим распознавания со словарём' )
    await onTextAsync( 'слушай мажордом включи режим распознавания со словарём' )
    checkIfSaid( 'Включаю режим распознавания со словарём' )
    await onTextAsync( 'слушай мажордом включи режим распознавания без словаря' )
    checkIfSaid( 'Выключаю режим распознавания со словарём' )

def testYesNo():
    logs.clear()
    print( '***** YesNoSkill tests' )
    await onTextAsync( 'алиса проверка да или нет' )
    checkIfSaid( 'Да или нет' )
    await onTextAsync('Траливали набекрень')
    checkIfSaid( 'не поняла' )
    #await onTextAsync( 'отмена' )
    await onTextAsync( 'да, уверен' )
    checkIfSaid( 'Подтверждено' )

def testFindWordChain():
    logs.clear()
    print( '***** findWordChain() tests' )
    await onTextAsync( 'алиса проверка поиска по шаблону' )
    checkIfSaid( 'Поиск по шаблону работает' )

def testTimeTeller():
    logs.clear()
    print( '***** TellTheTimeSkill tests' )
    await onTextAsync( 'алиса скажи сколько сейчас времени' )
    checkIfSaid( transcribeTime(datetime.datetime.today()) )
    await onTextAsync( 'алиса какое сегодня число' )
    checkIfSaid( transcribeDate(datetime.datetime.today()) )

def testOnOffSkill():
    logs.clear()
    print( '***** OnOffSkill() tests' )

    await onTextAsync( 'алиса включи свет в ванной' )
    await onTextAsync( 'алиса выключи свет слева' )

    await onTextAsync( 'эй алиса слушай выключи весь свет!' )
    await onTextAsync( 'алиса, включи свет здесь и на кухне' )
    await onTextAsync( 'алиса, включи весь свет здесь и на кухне' )
    await onTextAsync( 'алиса, включи весь свет в зале' )
    await onTextAsync( 'алиса, выключи здесь свет' )
    await onTextAsync( 'алиса, выключи свет везде' )
    await onTextAsync( 'алиса, выключи свет во всех комнатах' )
    await onTextAsync( 'алиса, включи свет слева' )

    checkIfSaid( 'Поиск по шаблону работает' )

ConfigParser.setConfigDir( os.path.join( ROOT_DIR, 'config.default' ) )

config = Config()
config.ttsEngine = None
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
Entities.initialize( config )
Terminal.initialize( config )
Speaker.initialize( config )


#d.methods['on'].execute()
#d.methods['off'].execute()

messageQueue = list()

terminal = Terminal.authorize( 'test', 'TestPassword', 'testscript' )
await terminal.onConnectAsync( messageQueue )

#print( transcribeDate(datetime.datetime.today()) )

#print( transcribeTime(datetime.datetime.today()) )


#print( transcribeInt(28,{'nomn','ADJF'}) )

#_s=''
#w = parseWord('восемь')[0]
#t = w.tag
#for c in list(t.CASES) :
#    for p in list(t.PARTS_OF_SPEECH) :
#        for g in list(t.KNOWN_GRAMMEMES) :
#            s = w.inflect( {str(c),str(p), str(g)})
#            if s is not None :
#                s = s.word
#                if s=='восьмое' :
#                    print( f'{str(c)},{str(p)}, {str(g)}: ' + s )
#                _s = s
#        #for g in list(t.KNOWN_GRAMMEMES) :
#        #    print( f'{c}, {p}, {g}: ' + transcribeInt(28,{str(c),str(p),str(g),'neut'},'декабря') )

#print( transcribeInt(1000,{'gent'},'хомяк') )
#print( transcribeInt(1111111,{'gent'}, 'хомяк') )

#print( transcribeInt(123123123,{'gent'}, 'хомяк') )

#testOnOffSkill()

testAppealDetector()
testFindWordChain()
testAcronym()
testOneWordCommandSkill()
testLocationDetector()
testParrotMode()
testServerConfig()
testYesNo()
testTimeTeller()


await terminal.onDisconnectAsync()

print('ALL SKILL TESTS PASSED!!!')
