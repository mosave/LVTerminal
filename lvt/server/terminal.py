import json
import sys
import time
import datetime
import rhvoice_wrapper # https://pypi.org/project/rhvoice-wrapper/
from lvt.const import *
from lvt.protocol import *
from lvt.config_parser import ConfigParser
from lvt.server.state_machine import StateMachine
import lvt.grammar as grammar
import pymorphy2

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
    def __init__( this, terminalConfigFileName ):
        p = ConfigParser( terminalConfigFileName )

        this.id = os.path.splitext( os.path.basename( terminalConfigFileName ) )[0].lower()

        this.password = p.getValue( '','Password','' )
        if this.password == '': raise Exception( f'Termininal configuration error: Password is not defined' )
        this.name = p.getValue( '','Name',this.id )
        this.verbose = p.getIntValue( '', 'verbose', 0 ) == '1'
        this.location = p.getValue( '','Location', '' )

        this.lastActivity = time.time()
        this.isAwaken = False
        # messages are local output messages buffer used while terminal is
        # disconnected
        this.messages = list()

        # messageQueue is an external output message queue
        # It is assigned on terminal connection and invalidated (set to None)
        # on disconnection
        this.messageQueue = None

        this.usingVocabulary = False
        this.vocabulary = ""

        this.loadEntities()
        this.updateVocabulary()


        # Speaker() class instance for last recognized speaker (if any)
        this.speaker = None

        #Semantic analyser state machine
        this.stateMachine = StateMachine( this )
        this.connectedOn = None
        this.disconnectedOn = None

    def say( this, text ):
        """Проговорить сообщение на терминал. 
          Текст сообщения так же дублируется командой "Text"
        """
        this.sendMessage( MSG_TEXT, text )
        if( config.ttsEngine == TTS_RHVOICE ):
            tts = rhvoice_wrapper.TTS( threads=1, 
                data_path=config.rhvDataPath, 
                config_path=config.rhvConfigPath,
                lame_path=None, opus_path=None, flac_path=None,
                quiet=True )

            waveData = tts.get( text, 
                voice=config.rhvVoice, 
                format_='wav', 
                sets=config.rhvParams, )

            this.sendDatagram( waveData )
            tts = None

    def play( this, waveFileName: str ):
        """Проиграть wave файл на терминале. Максимальный размер файла 500к """
        this.sendMessage( MSG_TEXT, f'Playing "{waveFileName}"' )
        with open( waveFileName, 'rb' ) as wave:
            this.sendDatagram( wave.read( 500 * 1024 ) )

    @property
    def isActive( this ) -> bool:
        """Терминал способен передавать команды (в онлайне) """
        return ( time.time() - this.lastActivity < 1 * 60 )

    def onConnect( this, messageQueue:list() ):
        """Метод вызывается при подключении терминального клиента
          messageQueue is synchronous message output queue
        """
        this.connectedOn = time.time()
        this.messageQueue = messageQueue
        # В случае, если предыдущая сессия закончилась недавно
        if this.disconnectedOn != None and this.connectedOn - this.disconnectedOn < 60 * 10:
            while len( this.messages ) > 0:
                messageQueue.append( this.messages[0] )
                this.messages.pop( 0 )

        this.morphy = pymorphy2.MorphAnalyzer( lang=config.language )

    def onDisconnect( this ):
        """Вызывается при (после) завершения сессии"""
        this.disconnectedOn = time.time()
        this.morphy = None
        this.messageQueue = None

    def onText( this, text:str, final:bool ):
        """Основная точка входа для обработки распознанного фрагмента """
        # обнаружено обращение
        appeal = False
        wds = grammar.wordsToList( text )
        # морфологический разбор - для упрощения обработки фразы
        words = list()
        for w in wds:
            word = grammar.ParsedWord(w, this.morphy.parse( w ))
            words.append( word )
            if not appeal: 
                forms = grammar.wordsToList(word.normalForms)
                for nf in forms:
                    appeal = appeal or grammar.oneOfWords( nf, config.assistantName )

        if appeal and not this.isAwaken:
            this.animate( ANIMATION_AWAKE )
            this.isAwaken = True

        this.sendMessage(MSG_TEXT, f'{final}, {appeal}, {text}')
        this.stateMachine.onText( text, words, final, appeal )
        if final:
            if this.verbose : this.sendMessage( MSG_TEXT,f'Распознано: "{text}"' )
            this.isAwaken = False
            this.animate( ANIMATION_NONE )

    def onTimer( this ):
        this.stateMachine.onTimer()



    def getVocabulary( this ) -> str:
        """Возвращает полный текущий список слов для фильтрации распознавания речи 
           или пустую строку если фильтрация не используется
        """
        return this.vocabulary if this.usingVocabulary else ''

    def updateVocabulary( this ):
        words = grammar.normalizeWords( config.assistantName )
        words = grammar.joinWords( words, config.confirmationPhrases )
        words = grammar.joinWords( words, config.cancellationPhrases )
        words = grammar.joinWords( words, this.WellKnownNames config.cancellationPhrases )


        this.vocabulary = words

    def loadEntities():
        this.wellKnownNames = loadEntity("well_known_names")
        this.devices = loadEntity("devices")
        this.locations = loadEntity("locations")
        this.actions = loadEntity("actions")

    def loadEntity( entityFileName ):
        entities = list()
        p = ConfigParser(  os.path.join( 'lvt','server','entities', entityFileName ) )
        for v in p.values:
            entity = list()
            for i in range(2,len(v)):
                entity.append(v[i])
            entities.append(entity)
        return entities


# Messages 
#region
    def getStatus( this ):
        """JSON строка с описанием текущего состояния терминала на стороне сервера
          Используется для передачи на сторону клиента.
          Клиент при этом уже авторизован паролем
        """
        js = '{'
        js += f'"Terminal":"{this.id}",'
        js += f'"Name":"{this.name}",'
        js += f'"Active":"{this.isActive}",'
        js += f'"UsingVocabulary":"{this.usingVocabulary}",'
        js += f'"Dictionary":' + json.dumps( this.dictionary, ensure_ascii=False ) + ''
        js += '}'
        return js

    def animate( this, animation ):
        """Передать слиенту запрос на анимацию"""
        #print(f'Animate {animation}')
        this.sendMessage( MSG_ANIMATE, animation )

    def sendMessage( this, msg:str, p1:str=None, p2:str=None ):
        if this.messageQueue != None:
            this.messageQueue.append( MESSAGE( msg, p1, p2 ) )
        else:
            this.messages.append( MESSAGE( msg, p1, p2 ) )

    def sendDatagram( this, data ):
        if this.messageQueue != None:
            this.messageQueue.append( data )
        else:
            this.messages.append( data )
#endregion

# Static classes
#region
    def setConfig( gConfig ):
        """Initialize module' config variable for easier access """
        global config
        config = gConfig


    def loadAllTerminals():
        """Returns dictionary of terminals[terminalId]
        terminalId is a lowered terminal config file name
        """
        dir = os.path.join( ROOT_DIR,'lvt','server','terminals' )
        terminals = dict()

        files = os.listdir( dir )
        for file in files:
            path = os.path.join( dir, file )
            if os.path.isfile( path ) and file.lower().endswith( '.cfg' ):
                try: 
                    t = Terminal( path[len( ROOT_DIR ) + 1:] )
                    terminals[t.id] = t 
                except Exception as e:
                    print( f'Exception loading  "{file}" : {e}' )
                    pass
        return terminals
#endregion
