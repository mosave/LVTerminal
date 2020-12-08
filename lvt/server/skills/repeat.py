import sys
from lvt.const import *
from lvt.server.grammar import *
from lvt.server.skill import Skill

TOPIC_REPEAT_MODE = 'RepeatMode'
class SkillRepeat(Skill):
    def onLoad( this ):
        #print('loading repeat')
        this.subscribe(TOPIC_DEFAULT)
        this.subscribe(TOPIC_REPEAT_MODE)

    def onText( this ):
        pass

