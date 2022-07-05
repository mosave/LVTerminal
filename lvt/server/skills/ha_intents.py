from lvt.const import *
from lvt.server.grammar import *
from lvt.server.utterances import Utterances
from lvt.server.skill import Skill
import lvt.server.api as api


#Define base skill class
class HomeAssistantIntentsSkill(Skill):
    """ Отслеживание фраз-триггеров, описанных в конфигурации Intent'ов Home Assistant (lvt => intents => ...)
    При обнаружении ключевой фразы скилл передает на сторону HA инициацию срабатывания соответствующего Intent'а.
    """
    def onLoad( self ):
        self.priority = 400
        self.__intents = []
        self.__utterances = Utterances( self.terminal )
        # Фразы анализируются только в режиме основного топика
        self.subscribe( TOPIC_DEFAULT )

    async def onTextAsync( self ):
        if self.isAppealed and (self.topic == TOPIC_DEFAULT):
            matches = self.utterances.match(self.words)
            if len(matches)>0:
                #for match in matches:
                match = matches[0]
                intent = self.intents[int(match.id)]

                api.fireIntent( intent['Intent'], self.terminal.id, self.terminal.text, match.values)
                self.stopParsing()

    @property
    def intents(self)->list:
        return self.__intents

    @property
    def utterances(self)->Utterances:
        return self.__utterances

    @intents.setter
    def intents(self, newIntents:list):
        self.__intents = []
        if bool(newIntents):
            self.utterances.clear()
            self.__intents = [i for i in newIntents if not bool(i["Terminals"]) or (self.terminal.id in i["Terminals"]) ]
            for i in range(len(self.__intents)):
                for utterance in self.__intents[i]['Utterance']:
                    self.utterances.add( i, utterance )
                    
            self.vocabulary = self.utterances.vocabulary
            self.terminal.updateVocabulary()

