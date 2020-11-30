import json
import sys
import time
from lvt.const import *
from lvt.protocol import *
import lvt.grammar as grammar
import rhvoice_wrapper # https://pypi.org/project/rhvoice-wrapper/

config = None

########################################################################################
class Terminal():
    def setConfig( gConfig ):
        global config
        config = gConfig

    def __init__(this, id  ):
        this.id = id
        this.name = f'Terminal #{id}'
        this.currentNode = ''
        this.lastActivity = time.time()
        this.isAwaken = False
        this.messageQueue = None
        this.setDictionary(this.getFullDictionary())
        this.speaker = None


    def say( this, text ):
        if this.messageQueue == None : return
        if(config.ttsEngine == TTS_RHVOICE):
            tts = rhvoice_wrapper.TTS( 
                threads=1, 
                data_path=config.rhvDataPath, 
                config_path=config.rhvConfigPath,
                lame_path=None, opus_path=None, flac_path=None,
                quiet=True
            )
            waveData = tts.get( 
                text, 
                voice=config.rhvVoice, 
                format_='wav', 
                sets=config.rhvParams,
            )

            this.sendDatagram( waveData )
            #with tts.say(text, voice=config.rhvVoice, format_='pcm', buff=8000, sets=None) as waves:
            #    for wave in waves: this.sendDatagram(wave)
            tts = None


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
        return(words)

    # Возвращает полный текущий список слов для фильтрации распознавания речи 
    # или пустую строку если фильтрация не используется
    def getVocabulary(this) -> str:
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
        js += f'"Dictionary":'+json.dumps(this.dictionary, ensure_ascii=False)+''
        js += '}'
        return js

    def animate( this, animation ):
        print(f'Animate {animation}')
        this.sendMessage( MSG_ANIMATE, animation )

    def sendMessage( this, msg:str, p1:str=None, p2:str=None ):
        if this.messageQueue != None: this.messageQueue.append( MESSAGE( msg, p1, p2 ) )

    def sendDatagram( this, data ):
        if this.messageQueue != None: this.messageQueue.append( data )


