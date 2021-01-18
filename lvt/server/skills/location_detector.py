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
        this.extendVocabulary('в у на под за около и или здесь во всех комнатах всём доме квартире')

    def onText( this ):
        (index, l) = this.findWordChain('везде')
        if index<0 : (index, l) = this.findWordChain('во всех комнатах')
        if index<0 : (index, l) = this.findWordChain('во всём доме')
        if index<0 : (index, l) = this.findWordChain('во всей квартире')
        if index<0 : (index, l) = this.findWordChain('в доме')
        if index<0 : (index, l) = this.findWordChain('в квартире')
        if index>=0 :
            this.deleteWord(index, l)
            for locations in this.entities.locations :
                this.terminal.parsedLocations.append( locations[0] )

        this.replaceWordChain('здесь', 'в '+this.terminal.defaultLocation)

        for locations in this.entities.locations :
            for badIndex in range(1,len(locations)+1) :
                # li = 1,2,..n,0 (основное название локации будет последним)
                il = badIndex if badIndex<len(locations) else 0
                location = locations[il]

                (index, l) = this.findWordChain(location)
                if index>0 :
                    nf = this.getNormalForm( index-1 )
                    if nf=="в" or nf=="у" or nf=="на" or nf=="за" or nf=="под" or nf=="около" :
                        index -= 1
                        l += 1

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

