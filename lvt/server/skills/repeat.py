import sys
from lvt.const import *
from lvt.grammar import *
from lvt.server.skill import Skill

#Define base skill class
class SkillRepeat(Skill):
    def onLoad( this ):
        #print('loading repeat')
        this.subscribe(TOPIC_DEFAULT)

    def onText( this ):
        pass


    #def onPartialText( this, text:str, appeal:bool ):
    #    pass
    #def onEnterState( this, state:str, text:str, isFinal: bool, isAppeal:bool ):
    #    pass

    #def onExitState( this, state:str, text:str, isFinal: bool, isAppeal:bool ):
    #    pass
        
    #def onTimer( this, state:str ):
    #    pass


