import sys
import time
from lvt.const import *
from lvt.protocol import *
from lvt.server.grammar import *
from lvt.server.utterances import Utterances
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
        self.utterances = Utterances( self.terminal )
        self.utterances.add("on", "включи режим попугая")
        self.utterances.add("on", "повторяй за мной")
        self.utterances.add("off", "выключи режим попугая")
        self.utterances.add("off", "перестань за мной повторять")
        self.utterances.add("off", "перестань повторять")
        self.setVocabulary( TOPIC_DEFAULT, self.utterances.vocabulary )

    async def onTextAsync( self ):

        if self.terminal.topic == TOPIC_PARROT_MODE:
            self.remindOn = time.time() + REMINDER_TIMEOUT
            matches = self.utterances.match(self.words)
            if (len(matches)>0) and (matches[0].id=='off'):
                self.stopParsing()
                await self.terminal.changeTopicAsync( TOPIC_DEFAULT )
            else:
                await self.terminal.sayAsync( self.terminal.originalText )

        elif self.terminal.isAppealed :
            matches = self.utterances.match(self.words)
            if (len(matches)>0) and (matches[0].id=='on'):
                await self.terminal.changeTopicAsync( TOPIC_PARROT_MODE )
                self.stopParsing()

    async def onTopicChangeAsync( self, newTopic: str, params={} ):
        if newTopic == TOPIC_PARROT_MODE:
            self.terminal.useVocabulary = False

        if self.terminal.topic == TOPIC_DEFAULT and newTopic == TOPIC_PARROT_MODE :
            await self.terminal.sayAsync( 'Окей, говорите и я буду повторять всё, что услышу!. ' + 'Для завершения скажите: "перестань за мной повторять"' )
            # Задаем время проговаривания напоминания
            self.remindOn = time.time() + REMINDER_TIMEOUT
        elif self.terminal.topic == TOPIC_PARROT_MODE :
            await self.terminal.sayAsync( 'Режим попугая выключен' )
            self.remindOn = 0
            self.stopParsing()
       
    async def onTimerAsync( self ):
        if( self.terminal.topic == TOPIC_PARROT_MODE ):
            if time.time() > self.remindOn:
                await self.terminal.sayAsync( 'Для завершения скажите "выключить режим попугая" или "перестань за мной повторять"!' )
                self.remindOn = time.time() + REMINDER_TIMEOUT

