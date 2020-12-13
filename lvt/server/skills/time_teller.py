import sys
import time
from lvt.const import *
from lvt.server.grammar import *
from lvt.server.skill import Skill

#Define base skill class
class TellTheTimeSkill(Skill):
    def onLoad( this ):
        #print('loading AppealDetector')
        this.priority = 5000
        this.subscribe( TOPIC_ALL )

    def onText( this ):
        pass
