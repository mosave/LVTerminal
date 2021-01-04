import sys
import time
from lvt.const import *
from lvt.server.grammar import *
from lvt.server.skill import Skill

TOPIC_WAIT_COMMAND = "WaitCommand"
WAIT_COMMAND_TIMEOUT = 5 # время в режиме ожидания команды, секунд

#Define base skill class
class LocationsDetectorSkill(Skill):
    """Извлекает из распознанной фразы информацию о локации"""
    def onLoad( this ):
        this.priority = 9900
        this.subscribe( TOPIC_ALL )

    def onText( this ):
        for locations in this.entities.locations :
            for badIndex in range(1,len(locations)+1) :
                il = badIndex if badIndex<len(locations) else 0
                location = locations[il]

                (index, l) = this.findWordChain('в '+location)
                if index<0 : (index, l) = this.findWordChain('у '+location)
                if index<0 : (index, l) = this.findWordChain('на '+location)
                if index<0 : (index, l) = this.findWordChain('около '+location)

                if index >=0:
                    if index>0 and this.isWord( index-1, None, {'CONJ'} ) :# Союз
                        index -= 1
                        this.deleteWord(index)
                    #if index>1 and this.isWord(index-2,'везде') and this.isWord(index-1,'кроме') :
                    #    ls = [x for x in this.` if "a" in x]
                    #    for locations
                    #else:

                    this.deleteWord( index, l )
                    this.terminal.parsedLocations.append( locations[0] )

        if len(this.terminal.parsedLocations)>0 :
            s = ', '.join(this.terminal.parsedLocations)
            this.logDebug(f'Локация: [{s}]')

