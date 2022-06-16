import datetime
from lvt.const import *
from lvt.server.grammar import *
from lvt.server.utterances import Utterances
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
        self.utterances = Utterances( self.terminal )
        self.utterances.add("time", "* сколько времени")
        self.utterances.add("time", "* сколько сейчас времени")
        self.utterances.add("time", "* который час")
        self.utterances.add("date", "* какой сегодня день недели")
        self.utterances.add("date", "* какое сегодня число")
        self.utterances.add("date", "* какая сегодня дата")
        self.vocabulary = self.utterances.vocabulary

    async def onTextAsync( self ):
        if self.isAppealed :
            matches = self.utterances.match(self.words)
            if len(matches)>0:
                self.stopParsing()
                if matches[0].id == 'time':
                    s = transcribeTime(  datetime.datetime.today() ).replace('часа', 'часа́')
                    await self.sayAsync( s )
                else:
                    await self.sayAsync('Сегодня '+ transcribeDate(datetime.datetime.today()) )
