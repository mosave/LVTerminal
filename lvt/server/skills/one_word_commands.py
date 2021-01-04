import sys
import time
from lvt.const import *
from lvt.server.grammar import *
from lvt.server.skill import Skill

TOPIC_WAIT_COMMAND = "WaitCommand"
WAIT_COMMAND_TIMEOUT = 5 # время в режиме ожидания команды, секунд

#Define base skill class
class OneWordCommandSkill(Skill):
    """'Мажордом, свет!'"""
    def onLoad( this ):
        this.priority = 9700
        this.subscribe( TOPIC_DEFAULT )
        this.extendVocabulary("свет");

    def onText( this ):
        if this.isAppealed and this.appealPos + 2 == len( this.words ):
            if this.isWord( this.appealPos + 1, 'свет', {'NOUN','nomn'} ):
                this.insertWords( this.appealPos + 1,'включи' )
                this.stopParsing()
                this.restartParsing()

