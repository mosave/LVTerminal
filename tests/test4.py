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

from lvt.server.utterances import *


config.init()
persistent_state.restore()
entities.init()
terminals.init()
speakers.init()

#u = Utterance("включи свет [в, на] location=[кухне, прихожей, туалете на первом, гостевом туалете]", terminals.get('speaker2w'))
#u = Utterance("action=[включи,выключи] attr=* object=? [в, на, у] location=[11=кухне, 15=прихожей,14 = туалете, 14=туалете на первом, 14=гостевом туалете]", terminals.get('speaker31') )
#u = Utterance("action=[включи,выключи] attr=* object=? [в, на, у] location=<location>", terminals.get('speaker31'))

u = Utterance("всего int=<integer> *", terminals.get('speaker31'))
#m = u.matchText("число сто двадцать три тысячи двенадцать word=?")

for i in range(0,1002):
    n = i
    n = random.randint(999999999)
    s = "Всего "+transcribeNumber(n,word="попугай")
    # print(s)
    m = u.matchText(s)
    if int(m[1]['int']) != n:
        print(f"{m[1]['int']} != {n}  ({s})")



u = Utterances( terminals.get('speaker31') )

u.add( 'u1', "action=[включи,выключи] attr=* object=? [в, на, у] location=[11=кухне, 15=прихожей,14 = туалете, 14=туалете на первом, 14=гостевом туалете]" )
u.add( 'u2', "* [в, на, у] location=<location>" )
u.add( 'u3', "action=[включи,выключи] attr=* object=? [в, на, у] location=<location>")
u.add( 'u4', "action=[включи,выключи] object=? *")

m1 = u.matchText("выключи свет в туалете")
m2 = u.matchText("включи приглушенный свет в гостевом туалете")
m3 = u.matchText("включи свет")

u = Utterance("включи свет [в, на] location=<location>", terminals.get('speaker31'))



u = Utterance("action=[включи,выключи] свет в location=<Locations>", terminals.get('speaker31'))
u = Utterance("включи color=* свет", terminals.get('speaker31'))
u = Utterance("Сколько сейчас времени", terminals.get('speaker31'))
u = Utterance("Выключи свет <time>", terminals.get('speaker31'))






