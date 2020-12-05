import sys
from lvt.const import *
from lvt.grammar import *
from lvt.server.skill import Skill

#Define base skill class
class SkillPrivet(Skill):
    def onLoad( this ):
        #print('loading privet')
        this.priority = 2
        pass

    def onText( this, state:str, text:str, final: bool, appeal:bool ):
        pass

    #def onEnterState( this, state:str, text:str, isFinal: bool, isAppeal:bool ):
    #    pass

    #def onExitState( this, state:str, text:str, isFinal: bool, isAppeal:bool ):
    #    pass
        
    #def onTimer( this, state:str ):
    #    pass

