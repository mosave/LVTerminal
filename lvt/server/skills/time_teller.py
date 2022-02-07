import sys
import time
import datetime
from lvt.const import *
from lvt.server.grammar import *
from lvt.server.skill import Skill

#Define base skill class
class TellTheTimeSkill(Skill):
    """Проговаривает текущее время и дату.
    Ключевые слова для вызова:
    * Сколько времени, который час
    * Какой сегодня день недели, какое число, какая дата
    """
    def onLoad( self ):
        self.priority = 1000
        self.subscribe( TOPIC_DEFAULT )
        self.extendVocabulary('сколько, сейчас времени, который час, какой сегодня день недели, скажи, число, дата')

    async def onText( self ):
        if self.isAppealed :
            if self.findWordChainB('сколько * времени') or \
                self.findWordChainB('который * час'):
                self.stopParsing(ANIMATION_ACCEPT)
                s = transcribeTime(  datetime.datetime.today() ).replace('часа', 'часа́')
                await self.sayAsync( s )

            elif self.findWordChainB('какой сегодня день') or \
                self.findWordChainB('какой день недели') or \
                self.findWordChainB('скажи какой день') or \
                self.findWordChainB('скажи * какое * число') or \
                self.findWordChainB('скажи * какая * дата') or \
                self.findWordChainB('какое сегодня число'):
                self.stopParsing(ANIMATION_ACCEPT)

                await self.sayAsync('Сегодня '+ transcribeDate(datetime.datetime.today()) )
