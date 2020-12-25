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
            iDict = this.findWord( 'словарь' )
            iRecognize = this.findWord( 'распознавание' )
            iNoDict = this.findWordChain( 'без словарь' )

            if (iDict>=0 and iNoDict<0) and iOn>=0 and iOn<iDict or \
                iNoDict>=0 and iOff>=0 and iOff<iNoDict :
                if this.terminal.vocabularyMode:
                    this.stopParsing( ANIMATION_CANCEL )
                    this.say("режим распознавания со словарем уже включен")
                else:
                    this.terminal.vocabularyMode = True
                    this.terminal.usingVocabulary = True
                    this.stopParsing( ANIMATION_ACCEPT )
                    this.say("Включаю режим распознавания со словарем")
            elif (iDict>=0 and iNoDict<0) and iOff>=0 and  iOff<iDict or \
                iNoDict>=0 and iOn>=0 and iOn<iNoDict :
                if this.terminal.vocabularyMode:
                    this.terminal.vocabularyMode = False
                    this.terminal.usingVocabulary = False
                    this.stopParsing( ANIMATION_ACCEPT )
                    this.say("Выключаю режим распознавания со словарем")
                else:
                    this.stopParsing( ANIMATION_CANCEL )
                    this.say("режим распознавания со словарем уже выключен")

