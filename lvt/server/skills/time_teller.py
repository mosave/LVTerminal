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
    def onLoad( this ):
        this.priority = 1000
        this.subscribe( TOPIC_DEFAULT )
        this.extendVocabulary('сколько, сейчас времени, который час, какой сегодня день недели, скажи, число, дата')

    async def onText( this ):
        if this.isAppealed :
            if this.findWordChainB('сколько * времени') or \
                this.findWordChainB('который * час'):
                this.stopParsing(ANIMATION_ACCEPT)
                s = transcribeTime(  datetime.datetime.today() ).replace('часа', 'часа́')
                await this.sayAsync( s )

            elif this.findWordChainB('какой сегодня день') or \
                this.findWordChainB('какой день недели') or \
                this.findWordChainB('скажи какой день') or \
                this.findWordChainB('скажи * какое * число') or \
                this.findWordChainB('скажи * какая * дата') or \
                this.findWordChainB('какое сегодня число'):
                this.stopParsing(ANIMATION_ACCEPT)

                await this.sayAsync('Сегодня '+ transcribeDate(datetime.datetime.today()) )
