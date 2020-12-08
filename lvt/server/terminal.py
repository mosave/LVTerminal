import json
import sys
import time
import datetime
import pymorphy2
from lvt.const import *
from lvt.protocol import *
from lvt.server.grammar import *
from lvt.config_parser import ConfigParser
from lvt.server.skill import Skill
from lvt.server.skill_factory import SkillFactory

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
            this.raiseException( f'Termininal configuration error: Password is not defined' )

        this.name = configParser.getValue( '','Name',this.id )
        this.logLevel = configParser.getIntValue( '', 'LogLevel', 0 )
        this.location = configParser.getValue( '','Location', '' )

        this.lastActivity = time.time()
        this.appealPos = None
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

        this.updateVocabulary()

        this.morphy = pymorphy2.MorphAnalyzer( lang=config.language )
        # Speaker() class instance for last recognized speaker (if any)
        this.speaker = None

        this.connectedOn = None
        this.disconnectedOn = None

        this.log( 'Loading skills' )

        this.allTopics = set()
        this.skills = SkillFactory( this ).loadSkills()

        for skill in this.skills:
            this.logDebug(f'{skill.priority:6} {skill.name}')
            this.allTopics = this.allTopics.union( skill.subscriptions )

        this.acronyms = this.loadEntities('acronyms')


        this.reset()

    def reset( this ):
        this.topic = TOPIC_DEFAULT
        this.appeal = wordsToList(config.assistantName)[0]
        this.appealPos = -1
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
        if os.path.dirname(waveFileName) == '' :
           waveFileName = os.path.join(ROOT_DIR,'lvt','server','sounds',waveFileName)
        this.logDebug(f'play("{waveFileName}")')
        with open( waveFileName, 'rb' ) as wave:
            this.sendDatagram( wave.read( 500 * 1024 ) )

    def getConfig(this):
        global config
        return config

    @property
    def isActive( this ) -> bool:
        """Терминал способен передавать команды (в онлайне) """
        return ( time.time() - this.lastActivity < 1 * 60 )

    @property
    def isAppealed(this)->bool:
        return this.appealPos!=None

    def onConnect( this, messageQueue:list() ):
        """Метод вызывается при подключении терминального клиента
          messageQueue is synchronous message output queue
        """
        this.log( 'Terminal connected' )
        this.connectedOn = time.time()
        this.messageQueue = messageQueue
        # В случае, если предыдущая сессия закончилась недавно
        if this.disconnectedOn != None and this.connectedOn - this.disconnectedOn < 60 :
            while len( this.messages ) > 0:
                messageQueue.append( this.messages[0] )
                this.messages.pop( 0 )
        else: # Необходимо переинициализировать состояние терминала
            this.reset()

    def onDisconnect( this ):
        """Вызывается при (после) завершения сессии"""
        this.log( 'Terminal disconnected' )
        this.disconnectedOn = time.time()
        this.messageQueue = None

    def parseWords( this, text:str ):
        # Кешируем морфологический разбор слов - для ускорения обработки фразы
        this.text = normalizeWords( text )
        this.words = list()
        wds = wordsToList( this.text )
        for w in wds: 
            this.words.append( this.morphy.parse( w ) )

    def onText( this, text:str, final:bool ):
        """Основная точка входа для обработки распознанного фрагмента """
        if final : 
            speakerName = this.speaker.name if this.speaker != None else 'Человек'
            this.logDebug( f'{speakerName}: {text}' )
        else:
            pass

        wasAppealed = this.isAppealed
        # Провести морфологический разбор слов текста
        this.parseWords( text )
        while True:
            for skill in this.skills:
                # Проверить, подписан ли скилл на текущий топик:
                if not skill.isSubscribed( this.topic ) : 
                    continue
                try:
                    method = 'onText()'
                    this.newTopic = None
                    this.parsingStopped = False
                    this.newText = None
                    this.parsingRestart = False
                    if final: 
                        skill.onText()
                    else: 
                        skill.onPartialText()

                    # Проверить, не изменился ли текст
                    if this.newText != None and this.newText != text :
                        this.parseWords( text )

                    method = 'onTopicChange()'
                    # Проверить, не изменился ли топик
                    if this.newTopic != None and this.newTopic != this.topic :
                        this.logDebug( f'{skill.name}: changing topic to {this.newTopic}' )
                        for s in this.skills:
                            if s.isSubscribed( this.topic ) or s.isSubscribed( this.newTopic ):
                                s.onTopicChange( this.topic, this.newTopic )
                        this.topic = this.newTopic
                        this.newTopic = None

                    # If current skill requested to abort further processing
                    if this.parsingStopped: break
                except Exception as e:
                    this.logError( f'{skill.name}.{method} exception: {e}' )
            if not this.parsingRestart : break

        if final:
            #if this.isAppealed and this.topic==TOPIC_DEFAULT :
            #    this.animate( ANIMATION_NONE )
            pass
        else:
            # Среагировать на обнаружение обращения
            #if this.isAppealed and not wasAppealed:
            #    this.animate( ANIMATION_AWAKE )
            pass


    def onTimer( this ):
        for skill in this.skills: 
            try:
                this.newTopic = None

                skill.onTimer()

                if this.newTopic != None and this.newTopic != this.topic :
                    this.logDebug( f'{skill.name}.onTimer(): changing topic to {this.newTopic}' )
                    for s in this.skills:
                        if s.isSubscribed( this.topic ) or s.isSubscribed( this.newTopic ):
                            s.onTopicChange( this.topic, this.newTopic )
                    this.topic = this.newTopic
                    this.newTopic = None

            except Exception as e:
                this.logError( f'{skill.name}.onTimer() exception: {e}' )


    def getVocabulary( this ) -> str:
        """Возвращает полный текущий список слов для фильтрации распознавания речи 
           или пустую строку если фильтрация не используется
        """
        return this.vocabulary if this.usingVocabulary else ''

    def updateVocabulary( this ):
        words = normalizeWords( config.assistantName )
        words = joinWords( words, config.confirmationPhrases )
        words = joinWords( words, config.cancellationPhrases )

        this.vocabulary = words

    def loadEntities( this, entityFileName ):
        entities = list()
        p = ConfigParser( os.path.join( 'lvt','server','entities', entityFileName ) )
        for v in p.values:
            entity = list()
            for i in range( 2,len( v ) ):
                entity.append( v[i] )
            entities.append( entity )
        return entities

# Logging
#region
    def logError( this, message:str ):
        print( f'E {message}' )
        if this.logLevel >= LOGLEVEL_ERROR :
            this.logs.append( f'E {message}' )

    def log( this, message:str ):
        if this.logLevel >= LOGLEVEL_INFO :
            print( f'I {message}' )
            this.logs.append( f'I {message}' )

    def logDebug( this, message:str ):
        if this.logLevel >= LOGLEVEL_DEBUG :
            print( f'D {message}' )
            this.logs.append( f'D {message}' )

    def raiseException( this, message ):
        this.logError( message )
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
        this.logDebug( f'Message: {message}' )
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
                    if configParser.getValue( '','Enable','1' ) == '1':
                        terminals.append( Terminal( terminalId, configParser ) )
                    configParser = None
                except Exception as e:
                    this.logError( f'Exception loading  "{file}" : {e}' )

    def authorize( terminalId:str, password:str ):
        """Авторизация терминала по terminalId и паролю"""
        terminalId = str( terminalId ).lower()
        for t in terminals :
            if t.id == terminalId and t.password == password: 
                return( t )
        return None

    def initialize( gConfig ):
        """Initialize module' config variable for easier access """
        global config
        global terminals
        config = gConfig
        if config.ttsEngine == TTS_RHVOICE :
            import rhvoice_wrapper # https://pypi.org/project/rhvoice-wrapper/
        else:
            pass

        Terminal.loadDatabase()

#endregion
