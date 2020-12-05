import sys
from lvt.const import *
from lvt.grammar import *
from lvt.server.skill import Skill

TOPIC_WAIT_COMMAND = "WaitCommand"

#Define base skill class
class AppealDetector(Skill):
    def onLoad( this ):
        #print('loading AppealDetector')
        this.priority = 999999
        this.subscribe( TOPIC_ALL )
        this.subscribe( TOPIC_WAIT_COMMAND )

    def onText( this ):
        #Should be false in theory
        if this.terminal.isAppealed : return 
        if this.detect() :
            pass
                

    def onPartialText( this, text:str, appeal:bool ):
        if this.terminal.isAppealed : return
        if detect() :
            pass


    def detect( this ):
        for word in terminal.words:



        return False
        if not appeal: 
            forms = grammar.wordsToList( word.normalForms )
            for nf in forms:
                appeal = appeal or grammar.oneOfWords( nf, config.assistantName )
        

    #def onEnterState( this, state:str, text:str, isFinal: bool, isAppeal:bool ):
    #    pass

    #def onExitState( this, state:str, text:str, isFinal: bool, isAppeal:bool ):
    #    pass
        
    #def onTimer( this, state:str ):
    #    pass

