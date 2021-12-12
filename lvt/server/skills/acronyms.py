import sys
import time
from lvt.const import *
from lvt.server.grammar import *
from lvt.server.skill import Skill

TOPIC_WAIT_COMMAND = "WaitCommand"
WAIT_COMMAND_TIMEOUT = 5 # время в режиме ожидания команды, секунд

#Define base skill class
class AcronymaExpanderSkill(Skill):
    """Вспомогательный скил, производит расшифровку устоявшихся фраз и имен собственных
    Специально для тех кто любит одушевлять и давать имена вещам :)
    Расшифровка производится по словарю lvt/entities/acronyms
    """
    def onLoad( self ):
        self.priority = 9950
        self.subscribe( TOPIC_ALL )

    def onText( self ):
        for a in self.entities.acronyms:
            for i in range(1, len(a)):
                self.replaceWordChain( a[i], a[0] )

