import time
from lvt.const import *
from lvt.protocol import MSG_API_FIRE_INTENT
from lvt.server.grammar import *
from lvt.server.skill import Skill
import lvt.server.api as api


#Define base skill class
class HomeAssistantIntentsSkill(Skill):
    """ Отлафливание фраз-триггеров, описанных в конфигурации Intent'ов Home Assistant (lvt => intents => ...)
    При обнаружении ключевой фразы скилл передает на сторону HA инициацию срабатывания соответствующего Intent'а.
    """
    def onLoad( self ):
        self.priority = 0
        self.__intents = []
        # Фразы анализируются только в режиме основного топика
        #self.subscribe( TOPIC_YES_NO )

    async def onText( self ):
        for intent in self.intents:
            for u in intent["Utterance"]:
                if self.findWordChainB( str(u) ) :
                    data = dict(intent['Data']) if 'Data' in intent else []
                    api.fireIntent( intent['Intent'], self.terminal.id, self.terminal.originalText, data)
                    self.stopParsing()

    @property
    def intents(self)->list:
        return self.__intents

    @intents.setter
    def intents(self, newIntents:list):
        if bool(newIntents):
            self.__intents = [i for i in newIntents if bool(i["Terminals"]) and self.terminal.id in i["Terminals"]]
            intents = [i for i in newIntents if not bool(i["Terminals"]) and i["Intent"] not in self.__intents]
            for i in intents:
                self.__intents.append(i)
        else:
            self.__intents = []
        