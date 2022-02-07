import sys
import time
from lvt.const import *
from lvt.server.grammar import *
from lvt.server.skill import Skill

#Define base skill class
class DateTimeDetectorSkill(Skill):
    """Извлекает из фразы информацию о дате и/или времени """
    def onLoad( self ):
        self.priority = 9930
        self.subscribe( TOPIC_ALL )

    async def onText( self ):
        pass

