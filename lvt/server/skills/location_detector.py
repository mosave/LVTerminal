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
        this.priority = 9900
        this.subscribe( TOPIC_DEFAULT )

    def onText( this ):
        for locations in this.terminal.knownLocations :
            for badIndex in range(1,len(locations)+1) :
                il = badIndex if badIndex<len(locations) else 0
                location = locations[il]
                n = 1
                index = this.findWordChain('в '+location)
                if index == None : index = this.findWordChain('на '+location)
                if index == None : index = this.findWordChain('около '+location)

                if index != None:
                    if index>0 and this.isWord( index-1, None, {'CONJ'} ) :# Союз
                        index -= 1
                        this.deleteWord(index)
                    #if index>1 and this.isWord(index-2,'везде') and this.isWord(index-1,'кроме') :
                    #    ls = [x for x in this.` if "a" in x]
                    #    for locations
                    #else:

                    this.deleteWord( index, n + len(wordsToList(location)) )
                    this.terminal.parsedLocations.append( locations[0] )
        if len(this.terminal.parsedLocations)>0 :
            s = ', '.join(this.terminal.parsedLocations)
            this.logDebug(f'Локация: [{s}]')
                
