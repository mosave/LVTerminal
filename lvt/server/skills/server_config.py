import sys
import time
import threading
from lvt.const import *
from lvt.server.grammar import *
from lvt.server.skill import Skill
from lvt.server.entities import Entities
from lvt.server.devices import Devices

#Define base skill class
class ServerConfigSkill(Skill):
    """Управление режимами сервера.
    Ключевые фразы скилла: "Включи (выключи) режим распознавания со словарем"
    """
    def onLoad( this ):
        this.priority = 5000
        this.subscribe( TOPIC_DEFAULT )
        this.extendVocabulary("включи выключи используй режим распознавания со словарём, без словаря, с использованием, без использования");
        this.extendVocabulary("словари словарю")
        this.mdUpdateResult = 0

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
                    this.say("режим распознавания со словарём уже включен")
                else:
                    this.terminal.vocabularyMode = True
                    this.terminal.usingVocabulary = True
                    this.stopParsing( ANIMATION_ACCEPT )
                    this.say("Включаю режим распознавания со словарём")
            elif iOff>=0 and iOff<iDict  or  iOn>=0 and iOn<iNoDict :
                if this.terminal.vocabularyMode:
                    this.terminal.vocabularyMode = False
                    this.terminal.usingVocabulary = False
                    this.stopParsing( ANIMATION_ACCEPT )
                    this.say("Выключаю режим распознавания со словарём")
                else:
                    this.stopParsing( ANIMATION_CANCEL )
                    this.say("режим распознавания со словарём уже выключен")
            elif this.findWordChainB('обновить список устройств'):
                this.stopParsing(ANIMATION_THINK)
                this.say("Запуск обновления устройств ")

                this.mdUpdateResult = 0
                thread = threading.Thread( target=this.updateDevices() )
                thread.daemon = False
                thread.start()

    def onTimer( this ):
        if this.mdUpdateResult==1:
            this.stopParsing(ANIMATION_ACCEPT)
            this.say('Устройства обновлены')
            this.mdUpdateResult = 0
        elif this.mdUpdateResult==2:
            this.stopParsing(ANIMATION_CANCEL)
            this.say('Ошибка при обновлении устройств')
            this.mdUpdateResult = 0

    def updateDevices( this ):
        try:
            Entities.initialize(this.config)
            Devices.initialize(this.config)

            if this.config.mdIntegration :
                Devices.loadMajorDoMoDevices()
            Devices.updateDefaultDevices()
            this.terminal.updateVocabulary()
            this.mdUpdateResult = 1
        except Exception as e:
            this.mdUpdateResult = 2
