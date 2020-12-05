import sys
from lvt.const import *
from lvt.grammar import *
from lvt.server.skill import Skill

#Define base skill class
class SkillS(Skill):
    def onLoad( this ):
        #print('loading S')
        this.priority = 200
        pass

