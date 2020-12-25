import sys
import time
from lvt.const import *
from lvt.server.grammar import *
from lvt.server.skill import Skill

#Define base skill class
class ClientUpdaterSkill(Skill):
    def onLoad( this ):
        this.priority = 500
        this.subscribe( TOPIC_DEFAULT )

    def onText( this ):
        pass
