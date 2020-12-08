import sys
import time
from lvt.const import *
from lvt.server.grammar import *
from lvt.server.skill import Skill

TOPIC_WAIT_COMMAND = "WaitCommand"
WAIT_COMMAND_TIMEOUT = 5 # время в режиме ожидания команды, секунд

#Define base skill class
class LocationsDetectorSkill(Skill):
    """'Мажордом, свет!'"""
    def onLoad( this ):
        this.priority = 9800
        this.subscribe( TOPIC_DEFAULT )

    def onText( this ):
        if this.topic != TOPIC_DEFAULT : 
            return

