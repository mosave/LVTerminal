import sys
from lvt.const import *
from lvt.server.grammar import *
from lvt.server.skill import Skill

#Define base skill class
class SkillRepeat(Skill):
    def onLoad( this ):
        #print('loading repeat')
        this.subscribe(TOPIC_DEFAULT)

    def onText( this ):
        pass

