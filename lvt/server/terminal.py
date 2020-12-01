import json
import sys
import time
from lvt.const import *
from lvt.protocol import *
from lvt.server.state_machine import StateMachine
import lvt.grammar as grammar
import rhvoice_wrapper # https://pypi.org/project/rhvoice-wrapper/

config = None

########################################################################################
class Terminal():
    """Terminal class
    Properties
      * id: Unique terminal Id, used for client identification
      * password: Password for client identification
      * name: terminal name, speech-friendly Id
      * speaker: Speaker object containing last speaking person details if available
    """
    def setConfig( gConfig ):
        global config
        config = gConfig

    def __init__(this, tCfg  ):
        this.id = tCfg['id'] if 'id' in tCfg else ''
        if this.id=='': raise Exception( f'Termininal configuration error: Id is not defined (section "Terminal", line {cfg.sectionId}' )
        this.password = tCfg['password'] if 'password' in tCfg else ''
        if this.password=='': raise Exception( f'Termininal configuration error: Password is not defined (section "Terminal", line {cfg.sectionId}' )
        this.name = tCfg['name'] if 'name' in tCfg else ''
        if this.name=='': raise Exception( f'Termininal configuration error: Name is not defined (section "Terminal", line {cfg.sectionId}' )
        this.verbose = (tCfg['verbose']=='1') if 'verbose' in tCfg else False
        this.lastActivity = time.time()
        this.isAwaken = False
        this.messageQueue = None
        this.setDictionary(this.getFullDictionary())
        this.speaker = None
        this.stateMachine = StateMachine( this )

    def say( this, text ):
        """Проговорить сообщение на терминал. 
          Текст сообщения так же дублируется командой "Text"
        """
        if this.messageQueue == None : return
        this.sendMessage( MSG_TEXT, text )
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
        """Терминал способен передавать команды (в онлайне) """
        return (time.time() - this.lastActivity < 1*60 )

    @property
    def usingDictionary(this) -> bool:
        return( len(this.dictionary)>0)

    def getFullDictionary(this):
        words = grammar.normalizeWords( config.assistantName )
        words = grammar.joinWords( words, config.confirmationPhrases )
        words = grammar.joinWords( words, config.cancellationPhrases )
        return(words)

    def getVocabulary(this) -> str:
        """Возвращает полный текущий список слов для фильтрации распознавания речи 
           или пустую строку если фильтрация не используется
        """
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
        """Основная точка входа для обработки текущего распознанного фрагмента (фраза не завершена)"""
        if not this.isAwaken:
            words = grammar.wordsToList(config.assistantName)
            for w in words:
                if grammar.oneOfWords( w, text ): 
                    this.animate(ANIMATION_AWAKE)
                    this.isAwaken = True
                    break;
        this.stateMachine.processPartial( text )

    def processFinal( this, text ):
        """Основная точка входа для обработки распознанной фразы"""
        if this.verbose : this.sendMessage(MSG_TEXT,f'Распознано: "{text}"')
        this.stateMachine.processFinal( text )

        this.isAwaken = False
        this.animate(ANIMATION_NONE)

    def getStatus( this ):
        """JSON строка с описанием текущего состояния терминала на стороне сервера
          Используется для передачи на сторону клиента.
          Клиент при этом уже авторизован паролем
        """
        js = '{'
        js += f'"Terminal":"{this.id}",'
        js += f'"Name":"{this.name}",'
        js += f'"Active":"{this.isActive}",'
        js += f'"UsingDictionary":"{this.usingDictionary}",'
        js += f'"Dictionary":'+json.dumps(this.dictionary, ensure_ascii=False)+''
        js += '}'
        return js

    def animate( this, animation ):
        """Передать слиенту запрос на анимацию"""
        print(f'Animate {animation}')
        this.sendMessage( MSG_ANIMATE, animation )

    def sendMessage( this, msg:str, p1:str=None, p2:str=None ):
        if this.messageQueue != None: this.messageQueue.append( MESSAGE( msg, p1, p2 ) )

    def sendDatagram( this, data ):
        if this.messageQueue != None: this.messageQueue.append( data )


