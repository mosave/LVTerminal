import sys
import time
from lvt.const import *
from lvt.server.grammar import *
from lvt.server.skill import Skill

#Define base skill class
class DateTimeDetectorSkill(Skill):
    """Извлекает из фразы информацию о дате и/или времени """
    def onLoad( this ):
        this.priority = 9930
        this.subscribe( TOPIC_ALL )

    def onText( this ):
        pass

