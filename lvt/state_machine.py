import sys
from lvt.const import *
from lvt.grammar import *
from lvt.skill_factory import SkillFactory

#Define base skill class
class StateMachine:
    def __init__( this, terminal ):
        this.terminal = terminal
        this.currentState = 'idle'
        this.states = dict()
        this.states['idle'] = []
        this.skills = SkillFactory(terminal).sf.loadAllSkills()

    def processPartial( this, text ):
        for stateName in this.states:
            state = this.states[stateName]


    def processFinal( this, text ):
        pass


