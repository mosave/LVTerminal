import json
from logging import fatal
import os
from numpy import random
import sys
import asyncio
import ssl

from lvt.const import *
from lvt.server.grammar import *
from lvt.protocol import *
from lvt.logger import *
import lvt.server.config as config
import lvt.server.persistent_state as persistent_state
import lvt.server.entities as entities
import lvt.server.terminal as terminals
import lvt.server.speakers as speakers
import lvt.server.speakers as speakers

from lvt.server.utterances import *
from lvt.server.tts import TTS


config.init()
persistent_state.restore()
entities.init()
terminals.init()
speakers.init()

tts = TTS()


u = Utterances( terminals.get('speaker2w') )
u.add('zzz', "[установить, сделать] громкость [терминала, колонки, динамика, звука, ] [на, в, ] volume=<number> процентов" )

m = u.matchText("Установи громкость пятьдесят процентов")


#print(inflectText("и зеленый попугай", {'femn'}))

print ( tts.prepareText('[Маленький хомяк: рд ]'))
print ( tts.prepareText('Еще нет и [13 час: 13, рд ]'))
print ( tts.prepareText('Температура на улице 15 [градус:15]'))
print ( tts.prepareText('38 [маленький хомяк: 38 ]'))

v = 3.01
while v<=4:
    print ( tts.prepareText(f' Температура {v} [градус: {v} ]'))
    v = v + 0.01

v = 1
while v<=111:
    print ( tts.prepareText(f' Температура {v} [градус: {v} ]'))
    v = v + 1

print ( tts.prepareText(' 1.1 [Прилет+ел попугай: 1.1 ]'))
print ( tts.prepareText(' 1.2 [Прилет+ел попугай: 1.2 ]'))
print ( tts.prepareText(' 1.11 [Прилет+ел попугай: 1.11 ]'))
print ( tts.prepareText(' 1.21 [Прилет+ел попугай: 1.21 ]'))
print ( tts.prepareText(' 1.001 [Прилет+ел попугай: 1.001 ]'))
print ( tts.prepareText(' 1.011 [Прилет+ел попугай: 1.011 ]'))
print ( tts.prepareText(' 1.041 [Прилет+ел попугай: 1.041 ]'))

print ( tts.prepareText(' 1 [Прилет+ел попугай: 1 ]'))
print ( tts.prepareText(' 5 [Прилет+ел попугай: 5 ]'))
print ( tts.prepareText(' 11 [Прилет+ел попугай: 11 ]'))
print ( tts.prepareText(' 121 [Прилет+ел  попугай: 121 ]'))

print(transcribeNumber(123))
print(transcribeNumber(121.5))
print(transcribeNumber(123.45))
print(transcribeNumber(123.345))
print(transcribeNumber(120.2345))
print(transcribeNumber(120.321))
print(transcribeNumber(120.311))
print(transcribeNumber(120.21))
print(transcribeNumber(120.11))
print(transcribeNumber(120.1))

parses = transcribeAndParseText(' Прилет+ели 123 попуг+ая')
print (tts.prepareText(' Прилет+ели 123 попуг+ая'))

print( tts.prepareText(" 35 или -35.1 [градусов:35.1]"))

print( tts.prepareText("Если бы у [3 баб+ушка: 3, рд] было 35 [яйцо: 35 ] они были бы дедушками") )

# vocabulary = wordsToVocabulary("человеки")
# vocabulary = wordsToVocabularyAllForms("косой")

#u = Utterance("включи свет [в, на] location=[кухне, прихожей, туалете на первом, гостевом туалете]", terminals.get('speaker2w'))
#u = Utterance("action=[включи,выключи] attr=* object=? [в, на, у] location=[11=кухне, 15=прихожей,14 = туалете, 14=туалете на первом, 14=гостевом туалете]", terminals.get('speaker31') )
#u = Utterance("action=[включи,выключи] attr=* object=? [в, на, у] location=<location>", terminals.get('speaker31'))

# u = Utterance("всего int=<integer> *", terminals.get('speaker31'))
# for i in range(0,1002):
#     n = i
#     n = random.randint(999999999)
#     s = "Всего "+transcribeInt(n,word="попугай")
#     # print(s)
#     m = u.matchText(s)
#     if int(m[1]['int']) != n:
#         print(f"{m[1]['int']} != {n}  ({s})")

u = Utterances( terminals.get('speaker31') )
# u.add( 'zzz', "Включи свет в location=<location>" )
# m = u.matchText("включи свет в прихожей")

u.add( 'zzz', "напомни time=<time> *" )
m = u.matchText("напомни через пятнадцать минут пожалуйста")


u.add( 'zzz', "всего number=<number> *" )
m = u.matchText("всего полтора попугая")
m = u.matchText("всего два попугая")
m = u.matchText("всего пять с половиной попугаев")
m = u.matchText("всего сто тысяч с четвертью попугаев")

m = u.matchText("всего девятнадцать сотен попугаев")

m = u.matchText("всего сто точка семнадцать десятитысячных попугаев")
m = u.matchText("всего сто целых семнадцать сотых попугая")



u.add( 'u1', "action=[включи,выключи] attr=* object=? [в, на, у] location=[11=кухне, 15=прихожей,14 = туалете, 14=туалете на первом, 14=гостевом туалете]" )
u.add( 'u2', "* [в, на, у] location=<location>" )
u.add( 'u3', "action=[включи,выключи] attr=* object=? [в, на, у] location=<location>")
u.add( 'u4', "action=[включи,выключи] object=? *")

u.add( 'u5', "сделай delta=[2=на пару градусов, 2=немного, 2=чуть, 3=на несколько градусов] [up=теплее, up=потеплее, down=холоднее, down=похолоднее]")

v = u.vocabulary

m1 = u.matchText("выключи свет в туалете")
m2 = u.matchText("включи приглушенный свет в гостевом туалете")
m3 = u.matchText("включи свет")

u = Utterance("включи свет [в, на] location=<location>", terminals.get('speaker31'))

u = Utterance("action=[включи,выключи] свет в location=<Locations>", terminals.get('speaker31'))
u = Utterance("включи color=* свет", terminals.get('speaker31'))
u = Utterance("Сколько сейчас времени", terminals.get('speaker31'))
u = Utterance("Выключи свет <time>", terminals.get('speaker31'))

