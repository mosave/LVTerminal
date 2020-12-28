import sys
import time
from lvt.const import *
from lvt.server.grammar import *
from lvt.server.skill import Skill

#Define base skill class
class ServerConfigSkill(Skill):
    """Управление режимами сервера.
    Ключевые фразы скилла: "Включи (выключи) режим распознавания со словарем"
    """
    def onLoad( this ):
        #print('loading AppealDetector')
        this.priority = 5000
        this.subscribe( TOPIC_DEFAULT )
        this.extendVocabulary("включи выключи используй режим распознавания со словарем, без словаря, с использованием, без использования");
        this.extendVocabulary("словари словарю")

    def onText( this ):
        if this.isAppealed :
            iOff = this.findWord( 'выключи' )
            iOn = this.findWord( 'включи' )
            (iNoDict,_) = this.findWordChain( 'без словаря' )
            iDict = this.findWord( 'словарь' ) if iNoDict<0 else -1
            iRecognize = this.findWord( 'распознавание' )

            if iOn>=0 and iOn<iDict  or  iOff>=0 and iOff<iNoDict :
                if this.terminal.vocabularyMode:
                    this.stopParsing( ANIMATION_CANCEL )
                    this.say("режим распознавания со словарем уже включен")
                else:
                    this.terminal.vocabularyMode = True
                    this.terminal.usingVocabulary = True
                    this.stopParsing( ANIMATION_ACCEPT )
                    this.say("Включаю режим распознавания со словарем")
            elif iOff>=0 and iOff<iDict  or  iOn>=0 and iOn<iNoDict :
                if this.terminal.vocabularyMode:
                    this.terminal.vocabularyMode = False
                    this.terminal.usingVocabulary = False
                    this.stopParsing( ANIMATION_ACCEPT )
                    this.say("Выключаю режим распознавания со словарем")
                else:
                    this.stopParsing( ANIMATION_CANCEL )
                    this.say("режим распознавания со словарем уже выключен")

