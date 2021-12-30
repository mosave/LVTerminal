import sys
import time
import datetime
import threading
from lvt.const import *
from lvt.protocol import *
from lvt.server.grammar import *
from lvt.server.skill import Skill
import lvt.server.entities as entities

# Как часто проверять версию терминала (раз в день?)
CHECK_VERSION_TIMEOUT = 60 * 60 * 24
# Время после последнего обращения, через которое будет выполнена проверка версии клиента
APPEAL_TIMEOUT = 5

#Define base skill class
class ServerConfigSkill(Skill):
    """Управление режимами сервера.
    Ключевые фразы скилла: "Включи (выключи) режим распознавания со словарем"
    """
    def onLoad( this ):
        this.priority = 5000
        this.subscribe( TOPIC_DEFAULT )
        this.extendVocabulary( "обнови пере запусти загрузи терминал" )
        this.nextVersionCheckOn = datetime.datetime.now()

    def onText( this ):
        if this.isAppealed :

            if this.findWordChainB( 'обнови * терминал' )  :
                this.stopParsing( ANIMATION_THINK )
                this.terminal.updateClient()

            # Хак: в словаре малой модели отсутствуют слова "перезагрузи" и "перезапусти"
            elif this.findWordChainB( 'пере загрузи * терминал' ) or this.findWordChainB( 'пере запусти * терминал' ) or \
                this.findWordChainB( 'загрузи * терминал' ) or this.findWordChainB( 'запусти * терминал' ) :
                this.stopParsing( ANIMATION_THINK )
                this.say( "Выполняется перезагрузка терминала." )
                this.terminal.reboot( "Терминал перезагружен." )

    def onTimer( this ):
        if this.topic == TOPIC_DEFAULT and this.lastAppealed :
            if datetime.datetime.now() > this.lastAppealed + datetime.timedelta( seconds=10 ) and datetime.datetime.now() > this.nextVersionCheckOn :
                this.nextVersionCheckOn = datetime.datetime.today() + datetime.timedelta( hours=32 )
                if this.terminal.clientVersion != VERSION :
                    if this.terminal.autoUpdate == 2 :
                        this.terminal.updateClient()
                    if this.terminal.autoUpdate == 1 :
                        this.say( 'Версия терминала устарела.' )
                        this.say( 'Для обновления скажите "Обновить терминал".' )

    def updateDevices( this ):
        try:
            entities.init()
            this.terminal.updateVocabulary()
        except Exception as e:
            pass
