import sys
import time
from lvt.const import *
from lvt.protocol import *
from lvt.server.grammar import *
from lvt.server.skill import Skill

TOPIC_PARROT_MODE = 'ParrotMode'
REMINDER_TIMEOUT = 60
class ParrotModeSkill(Skill):
    """Скилл "Режим попугая" позволяет оценить качество распознавания речи.
    Ключевые фразы для активации режима: "Повторяй за мной" или "Включи режим попугая"
    """
    def onLoad( self ):
        self.subscribe( TOPIC_DEFAULT,TOPIC_PARROT_MODE )
        self.priority = 1000
        self.remindOn = 0
        self.extendVocabulary( "повторяй за мной, включи режим попугая" )
        self.extendVocabulary( "выключи режим попугая, перестань повторять" )

    async def onText( self ):
        if self.topic == TOPIC_PARROT_MODE:
            self.remindOn = time.time() + REMINDER_TIMEOUT

            iOff = self.findWord( 'выключи' )
            iOn = self.findWord( 'включи' )

            iStop = self.findWord( 'перестань' )
            iRepeat = self.findWord( 'повторять' )
            iParrot = self.findWord( 'попугай' )
            if iOff >= 0 and iParrot > 0 or iStop >= 0 and iRepeat >= 0 :
                self.stopParsing( ANIMATION_ACCEPT )
                await self.changeTopic( TOPIC_DEFAULT )
            else:
                await self.sayAsync( self.terminal.originalTextUnfiltered )

        else:
            if self.isAppealed :
                if self.findWordChainB( 'включи режим попугая' ) or \
                    self.findWordChainB( 'переключись * режим попугая' ) or \
                    self.findWordChainB( 'перейди в режим попугая' ) or \
                    self.findWordChainB( 'повторяй за мной' ) :
                    await self.changeTopic( TOPIC_PARROT_MODE )
                    self.stopParsing( ANIMATION_ACCEPT )

    async def onTopicChange( self, newTopic: str, params={} ):
        if self.topic == TOPIC_DEFAULT and newTopic == TOPIC_PARROT_MODE :
            self.animate( ANIMATION_AWAKE )
            await self.sayAsync( 'Окей, говорите и я буду повторять всё, что услышу!. ' + 'Для завершения скажите: "перестань за мной повторять"' )
            # Задаем время проговаривания напоминания
            self.remindOn = time.time() + REMINDER_TIMEOUT
        elif self.topic == TOPIC_PARROT_MODE :
            await self.sayAsync( 'Режим попугая выключен' )
            self.remindOn = 0
       
    async def onTimer( self ):
        if( self.topic == TOPIC_PARROT_MODE ):
            if time.time() > self.remindOn:
                await self.sayAsync( 'Для завершения скажите "выключить режим попугая" или "перестань за мной повторять"!' )
                self.remindOn = time.time() + REMINDER_TIMEOUT

