import json
import sys
import time
from lvt.const import *
from lvt.protocol import *
import lvt.grammar as grammar

config = None
terminals = None

########################################################################################
class Terminal():
    def setConfig( gConfig, gTerminals ):
        global config
        global terminals
        config = gConfig
        terminals = gTerminals

    def __init__(this, id ):
        this.id = id
        this.name = f'Terminal #{id}'
        this.currentNode = ''
        this.lastActivity = time.time()
        this.isAwaken = False
        this.messages = []
        this.setDictionary(this.getFullDictionary())
        this.speaker = None

    @property
    def isActive(this) -> bool:
        return (time.time() - this.lastActivity < 3*60 )

    @property
    def usingDictionary(this) -> bool:
        return( len(this.dictionary)>0)

    def getFullDictionary(this):
        words = grammar.normalizeWords( config.assistantName )
        words = grammar.joinWords( words, config.confirmationPhrases )
        words = grammar.joinWords( words, config.cancellationPhrases )
        print(words)
        return(words)

    def getDictionaryWords(this) -> str:
        words = ""
        for word in this.dictionary:
            words += word+' '
        return( words.strip() )

    def setDictionary(this, dict ):
        if( isinstance(dict, str)):
            dict = dict.lower().replace(',',' ').replace(';',' ').replace('  ',' ').strip()
            this.dictionary = dict.split(' ') if( len(dict) > 0 ) else []
        else:
            this.dictionary = []

    def processPartial( this, text ):
        if not this.isAwaken:
            words = grammar.wordsToList(config.assistantName)
            for w in words:
                if grammar.oneOfWords( w, text ): 
                    this.animate(ANIMATION_AWAKE)
                    this.isAwaken = True
                    break;

    def processFinal( this, text ):
        this.isAwaken = False
        this.animate(ANIMATION_NONE)

    def getStatus( this ):
        js = '{'
        js += f'"Terminal":"{this.id}",'
        js += f'"Name":"{this.name}",'
        js += f'"Active":"{this.isActive}",'
        js += f'"UsingDictionary":"{this.usingDictionary}",'
        js += f'"Dictionary":'+json.dumps(this.dictionary, ensure_ascii=False)+','
        js += f'"zzz":"zzz"'
        js += '}'
        return js

    def animate( this, animation ):
        print(f'Animate {animation}')

        this.messages.append( MESSAGE(MSG_ANIMATE, animation) )


