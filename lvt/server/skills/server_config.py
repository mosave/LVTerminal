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
    def onLoad( self ):
        self.priority = 5000
        self.subscribe( TOPIC_DEFAULT )
        self.extendVocabulary( "обнови пере запусти загрузи терминал" )
        self.nextVersionCheckOn = datetime.datetime.now()

    async def onText( self ):
        if self.isAppealed :

            if self.findWordChainB( 'обнови * терминал' )  :
                self.stopParsing( ANIMATION_THINK )
                await self.terminal.updateClient()

            # Хак: в словаре малой модели отсутствуют слова "перезагрузи" и "перезапусти"
            elif self.findWordChainB( 'пере загрузи * терминал' ) or self.findWordChainB( 'пере запусти * терминал' ) or \
                self.findWordChainB( 'загрузи * терминал' ) or self.findWordChainB( 'запусти * терминал' ) :
                self.stopParsing( ANIMATION_THINK )
                await self.sayAsync( "Выполняется перезагрузка терминала." )
                self.terminal.reboot( "Терминал перезагружен." )

    async def onTimer( self ):
        if self.topic == TOPIC_DEFAULT and self.lastAppealed :
            if datetime.datetime.now() > self.lastAppealed + datetime.timedelta( seconds=10 ) and datetime.datetime.now() > self.nextVersionCheckOn :
                self.nextVersionCheckOn = datetime.datetime.today() + datetime.timedelta( hours=32 )
                if self.terminal.clientVersion != VERSION :
                    if self.terminal.autoUpdate == 2 :
                        await self.terminal.updateClient()
                    if self.terminal.autoUpdate == 1 :
                        await self.sayAsync( 'Версия терминала устарела.' )
                        await self.sayAsync( 'Для обновления скажите "Обновить терминал".' )

    def updateDevices( self ):
        try:
            entities.init()
            self.terminal.updateVocabulary()
        except Exception as e:
            pass
