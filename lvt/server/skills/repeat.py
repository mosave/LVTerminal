import sys
from lvt.const import *
from lvt.grammar import *
from lvt.server.skill import Skill

#Define base skill class
class SkillRepeat(Skill):
    def onLoad( this ):
        #print('loading repeat')
        this.subscribe(STATE_DEFAULT)

    def onText( this, state:str, text:str, final: bool, appeal:bool ):
        if not appeal : return

        pass

    #def onEnterState( this, state:str, text:str, isFinal: bool, isAppeal:bool ):
    #    pass

    #def onExitState( this, state:str, text:str, isFinal: bool, isAppeal:bool ):
    #    pass
        
    #def onTimer( this, state:str ):
    #    pass


