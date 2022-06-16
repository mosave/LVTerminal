import sys
import time
from lvt.const import *
from lvt.server.grammar import *
from lvt.server.skill import Skill

TOPIC_DEBUG1 = "Debug1"
TOPIC_DEBUG2 = "Debug2"
TOPIC_DEBUG3 = "Debug3"
TOPIC_DEBUG4 = "Debug4"
#Define base skill class
class DebugSkill(Skill):
    """Скилл для отладки"""
    def onLoad( self ):
        self.priority = 9000
        #self.vocabulary = wordsToVocabulary("проверка да или нет поиска по шаблону")

    async def onTextAsync( self ):
        if self.isAppealed :
            pass

    async def onTopicChangeAsync( self, newTopic: str, params = {} ):
        pass
