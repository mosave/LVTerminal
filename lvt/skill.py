import sys

from lvt.const import *
from lvt.server.terminal import Terminal

#Define base skill class
class Skill:
    def __init__( this, terminal: Terminal ):
        # Enable this skill
        this.enalbed = False

        # list of other skills this skill depends on (to ensure they will be registered
        this.dependsOn = list()

        # list of states to call skill' processPartial()
        this.statesProcessPartial = list()

        # list of states to call skill' processFinal()
        this.statesProcessFinal = list()

        # Current terminal
        this.terminal = terminal
        pass

    def processPartial( this, currentState, text ) -> ():
        # ( newState, )
        pass

    def processFinal( this, currentState, text ):
        pass

    def Say( this, text ):
        terminal.Say(text)

