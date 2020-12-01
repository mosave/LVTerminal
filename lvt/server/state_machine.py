import sys

from lvt.const import *
from lvt.grammar import *
#from lvt.server.skills import *

#Define base skill class
class StateMachine:
    def __init__( this, terminal ):
        this.terminal = terminal


        pass

    def processPartial( this, text ):
        pass

    def processFinal( this, text ):
        pass


