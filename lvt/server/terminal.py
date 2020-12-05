import json
import sys
import time
import datetime
import pymorphy2
import rhvoice_wrapper # https://pypi.org/project/rhvoice-wrapper/
from lvt.const import *
from lvt.protocol import *
from lvt.config_parser import ConfigParser
from lvt.server.skill import Skill
from lvt.server.skill_factory import SkillFactory
import lvt.grammar as grammar

config = None
terminals = list()

########################################################################################
class Terminal():
    """Terminal class
    Properties
      * id: Unique terminal Id, used for client identification
      * password: Password for client identification
      * name: terminal name, speech-friendly Id
      * speaker: Speaker object containing last speaking person details if available
    """
    def __init__( this, terminalId: str, configParser: ConfigParser ):
        this.id = terminalId

        this.password = configParser.getValue( '','Password','' )
        if this.password == '': 
            this.raiseException(f'Termininal configuration error: Password is not defined')

        this.name = configParser.getValue( '','Name',this.id )
        this.logLevel = configParser.getIntValue( '', 'LogLevel', 0 )
        this.location = configParser.getValue( '','Location', '' )

        this.lastActivity = time.time()
        # messages are local output messages buffer used while terminal is
        # disconnected
        this.messages = list()
        this.logs = list()

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

        this.connectedOn = None
        this.disconnectedOn = None

        this.log('Loading skills')

        this.allTopics = set()
        this.skills = SkillFactory(this).loadSkills()
        for skill in this.skills:
            this.allTopics = this.allTopics.union(skill.subscriptions )

        this.reset()

    def reset(this):
        this.topic = TOPIC_DEFAULT
        this.isAppealed = False
        this.text = ''
        this.words = list()
        this.animate( ANIMATION_NONE )

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
        this.log('Terminal connected')
        this.connectedOn = time.time()
        this.messageQueue = messageQueue
        # В случае, если предыдущая сессия закончилась недавно
        if this.disconnectedOn != None and this.connectedOn - this.disconnectedOn < 60 :
            while len( this.messages ) > 0:
                messageQueue.append( this.messages[0] )
                this.messages.pop( 0 )
        else: # Необходимо переинициализировать состояние терминала
            this.reset()

        this.morphy = pymorphy2.MorphAnalyzer( lang=config.language )

    def onDisconnect( this ):
        """Вызывается при (после) завершения сессии"""
        this.log('Terminal disconnected')
        this.disconnectedOn = time.time()
        this.morphy = None
        this.messageQueue = None


    def parseWords(this, text:str):
        # морфологический разбор - для упрощения обработки фразы
        this.logDebug( f'Text: {text}')
        this.text = text
        this.words = list()
        wds = grammar.wordsToList( text )
        for w in wds: this.words.append( grammar.ParsedWord(w, this.morphy.parse( w ) ) )


    def onText( this, text:str, final:bool ):
        """Основная точка входа для обработки распознанного фрагмента """

        # обнаружено обращение
        # Провести морфологический разбор
        this.parseWords( text )

        for skill in this.skills:
            # Проверить, подписан ли скилл на текущий топик:
            if not skill.isSubscribed(this.topic) : 
                continue
            try:
                method = 'onText()'
                this.newTopic = None
                this.parsingStopped  = False
                this.newText = None
                wasAppealed = this.isAppealed
                if final: 
                    skill.onText()
                else: 
                    skill.onPartialText()

                # Среагировать на обнаружение обращения
                if this.isAppealed and not wasAppealed:
                    this.animate( ANIMATION_AWAKE )

                # Проверить, не изменился ли текст
                if this.newText != None and this.newText != text :
                    this.parseWords(text)

                method = 'onTopicChange()'
                # Проверить, не изменился ли топик
                if this.newTopic != None and this.newTopic != this.Topic :
                    this.LogDebug(f'{skill.name}: changing topic to {this.newTopic}')
                    for s in skills:
                        if s.isSubscribed(this.topic) or s.isSubscribed(this.newTopic):
                            s.onTopicChange( this.topic, this.newTopic)
                    this.topic = this.newTopic
                    this.newTopic = None

                # If current skill requested to abort further processing
                if this.parsingStopped: break
            except Exception as e:
                this.logError(f'{skill.name}.{method} exception: {e}')

        if final:
            if not this.parsingStopped:
                this.logDebug('Text not parsed')
            if this.isAppealed : this.animate( ANIMATION_NONE )
            this.isAppealed = False

    def onTimer( this ):
        for skill in this.skills: 
            try:
                skill.onTimer()
            except Exception as e:
                this.logError(f'{skill.name}.onTimer() exception: {e}')


    def getVocabulary( this ) -> str:
        """Возвращает полный текущий список слов для фильтрации распознавания речи 
           или пустую строку если фильтрация не используется
        """
        return this.vocabulary if this.usingVocabulary else ''

    def updateVocabulary( this ):
        words = grammar.normalizeWords( config.assistantName )
        words = grammar.joinWords( words, config.confirmationPhrases )
        words = grammar.joinWords( words, config.cancellationPhrases )
        #words = grammar.joinWords( words, this.wellKnownNames )

        this.vocabulary = words

    def loadEntities(this):
        this.wellKnownNames = this.loadEntity("well_known_names")
        this.devices = this.loadEntity("devices")
        this.locations = this.loadEntity("locations")
        this.actions = this.loadEntity("actions")

    def loadEntity( this, entityFileName ):
        entities = list()
        p = ConfigParser(  os.path.join( 'lvt','server','entities', entityFileName ) )
        for v in p.values:
            entity = list()
            for i in range(2,len(v)):
                entity.append(v[i])
            entities.append(entity)
        return entities


    def joinEntity(this, entity):
        pass

# Logging
#region
    def logError(this, message:str):
        print(message)
        if this.logLevel >= LOGLEVEL_ERROR :
            this.logs.append(f'E {message}')

    def log(this, message:str):
        if this.logLevel >= LOGLEVEL_INFO :
            print(message)
            this.logs.append(f'I {message}')

    def logDebug(this, message:str):
        if this.logLevel >= LOGLEVEL_DEBUG :
            print(message)
            this.logs.append(f'D {message}')

    def raiseException(this, message ):
        this.logError(message)
        raise Exception( message )
#endregion

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
        js += f'"UsingVocabulary":"{this.usingVocabulary}",'
        if this.usingVocabulary :
            js += f'"Vocabulary":' + json.dumps( this.vocabulary, ensure_ascii=False ) + ', '
        js += f'"Active":"{this.isActive}" '
        js += '}'
        return js

    def animate( this, animation ):
        """Передать слиенту запрос на анимацию"""
        this.sendMessage( MSG_ANIMATE, animation )

    def sendMessage( this, msg:str, p1:str=None, p2:str=None ):
        message = MESSAGE( msg, p1, p2 )
        this.logDebug(f'Message: {message}')
        if this.messageQueue != None:
            this.messageQueue.append( message )
        else:
            this.messages.append( message )

    def sendDatagram( this, data ):
        if this.messageQueue != None:
            this.messageQueue.append( data )
        else:
            this.messages.append( data )
#endregion

# Static methods
#region
    def loadDatabase():
        """Кеширует в память список сконфигурированных терминалов"""
        global config
        global terminals
        """Returns dictionary of terminals[terminalId]
        terminalId is a lowered terminal config file name
        """
        dir = os.path.join( 'lvt','server','terminals' )
        terminals = list()

        files = os.listdir( os.path.join( ROOT_DIR, dir ) )
        for file in files:
            path = os.path.join( dir, file )
            if os.path.isfile( path ) and file.lower().endswith( '.cfg' ):
                try: 
                    terminalId = os.path.splitext( file )[0].lower()
                    configParser = ConfigParser( path )
                    if configParser.getValue('','Enable','1') == '1':
                        terminals.append( Terminal( terminalId, configParser ) )
                    configParser = None
                except Exception as e:
                    this.logError( f'Exception loading  "{file}" : {e}' )

    def authorize( terminalId:str, password:str ):
        """Авторизация терминала по terminalId и паролю"""
        terminalId = str(terminalId).lower()
        for t in terminals :
            if t.id == terminalId and t.password == password: 
                return(t)
        return None

    def Initialize( gConfig ):
        """Initialize module' config variable for easier access """
        global config
        global terminals
        config = gConfig
        Terminal.loadDatabase()

#endregion
