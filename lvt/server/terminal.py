import sys
import time
import datetime
import json
import pymorphy2
from lvt.const import *
from lvt.logger import *
from lvt.protocol import *
from lvt.server.grammar import *
from lvt.config_parser import ConfigParser
from lvt.server.skill import Skill
from lvt.server.skill_factory import SkillFactory

config = None
terminals = list()
rhvoiceTTS = None

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
        this.logDebug(f'Initializing terminal')

        this.password = configParser.getValue( '','Password','' )
        if this.password == '': 
            this.raiseException( f'Termininal configuration error: Password is not defined' )

        this.clientVersion = ""
        this.usingVocabulary = False
        this.vocabulary = ""

        this.name = configParser.getValue( '','Name',this.id )
        this.defaultLocation = configParser.getValue( '','Location', '' ).lower()
        this.autoUpdate = (configParser.getIntValue( '', 'AutoUpdate', 1 ) != 0)

        this.parsedLocations = []

        this.lastActivity = time.time()
        this.appealPos = None
        # messages are local output messages buffer used while terminal is
        # disconnected
        this.messages = list()

        # messageQueue is an external output message queue
        # It is assigned on terminal connection and invalidated (set to None)
        # on disconnection
        this.messageQueue = None

        this.morphy = pymorphy2.MorphAnalyzer( lang=config.language )
        # Speaker() class instance for last recognized speaker (if any)
        this.speaker = None

        this.connectedOn = None
        this.disconnectedOn = None

        this.logDebug( 'Loading skills' )

        this.allTopics = set()
        this.skills = SkillFactory( this ).loadSkills()

        for skill in this.skills:
            this.logDebug( f'{skill.priority:6} {skill.name}' )
            this.allTopics = this.allTopics.union( skill.subscriptions )

        this.acronyms = this.loadEntities( 'acronyms' )
        this.knownLocations = this.loadEntities( 'locations' )

        this.lastAnimation = ''

        #if config.ttsEngine == TTS_RHVOICE :
        #    import rhvoice_wrapper # https://pypi.org/project/rhvoice-wrapper/


        this.reset()

    def reset( this ):
        this.topic = TOPIC_DEFAULT
        this.appeal = wordsToList( config.assistantName )[0]
        this.appealPos = -1
        this.words = list()
        this.animate( ANIMATION_NONE )

    def say( this, text ):
        """Проговорить сообщение на терминал. 
          Текст сообщения так же дублируется командой "Text"
        """
        #this.sendMessage( MSG_TEXT, f'Say {text}' )
        this.logDebug(f'Say "{text}"')
        if( config.ttsEngine == TTS_RHVOICE ):
            this.sendMessage(MSG_MUTE)
            if rhvoiceTTS != None :
                waveData = rhvoiceTTS.get( text, 
                    voice=config.rhvVoice, 
                    format_='wav', 
                    sets=config.rhvParams, )
                this.sendDatagram( waveData )
            this.sendMessage(MSG_UNMUTE)


    def play( this, waveFileName: str ):
        """Проиграть wave файл на терминале. Максимальный размер файла 500к """
        this.sendMessage( MSG_TEXT, f'Playing "{waveFileName}"' )
        if os.path.dirname( waveFileName ) == '' :
           waveFileName = os.path.join( ROOT_DIR,'lvt','sounds',waveFileName )
        with open( waveFileName, 'rb' ) as wave:
            this.sendDatagram( wave.read( 500 * 1024 ) )
    @property
    def config( this ):
        """Возвращает Config"""
        global config
        return config

    @property
    def isActive( this ) -> bool:
        """Терминал способен передавать команды (в онлайне) """
        return ( time.time() - this.lastActivity < 1 * 60 )

    @property
    def locations( this ) -> str:
        """Локация, распознанная в процессе анализа фразы либо локация по умолчанию, заданная в конфигурации терминала"""
        return ( this.parsedLocations if len( this.parsedLocations ) > 0 else [this.defaultLocation] )

    @property
    def isAppealed( this ) -> bool:
        return this.appealPos != None

    @property
    def text( this ) -> str:
        """Сгенерировать текст фразы из разолранных слов """
        text = ''
        for w in this.words: text += w[0].word + ' '
        return text.strip()

    @text.setter 
    def text( this, newText ):
        # Кешируем морфологический разбор слов - для ускорения обработки фразы
        newText = normalizeWords( newText )
        this.words = list()
        wds = wordsToList( newText )
        for w in wds: 
            parses = this.morphy.parse( w )
            #Проигнорировать предикативы, наречия, междометия и частицы
            if {'PRED'} not in parses[0].tag and {'ADVB'} not in parses[0].tag and {'INTJ'} not in parses[0].tag and {'PRCL'} not in parses[0].tag :
                this.words.append( parses )

    def onConnect( this, messageQueue:list() ):
        """Метод вызывается при подключении терминального клиента
          messageQueue is synchronous message output queue
        """
        this.log( f'Terminal connected, client version {this.clientVersion}' )
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

    def onText( this, text:str, final:bool ):
        """Основная точка входа для обработки распознанного фрагмента """
        text = normalizeWords( text )

        if final : 
            this.originalText = text
            speakerName = this.speaker.name if this.speaker != None else 'Человек'
            this.logDebug( f'{speakerName}: "{text}"' )
        else:
            this.originalText = ""

        # Провести морфологический разбор слов текста
        this.text = text
        if final and text != this.text :
            this.logDebug( f'Вычищенный текст: "{this.text}"' )

        while True:
            this.parsedLocations = []
            wasAppealed = this.isAppealed
            for skill in this.skills:
                # Проверить, подписан ли скилл на текущий топик:
                if not skill.isSubscribed( this.topic ) : 
                    continue
                try:
                    method = 'onText()'
                    this.newTopic = None
                    this.parsingStopped = False
                    this.parsingRestart = False
                    _text = this.text
                    if final: 
                        skill.onText()
                    else: 
                        skill.onPartialText()
                    text = this.text
                    if text != _text and final:
                        this.logDebug( f'{skill.name}: changing text to "{text}"' )


                    method = 'onTopicChange()'
                    # Проверить, не изменился ли топик
                    if this.newTopic != None and this.newTopic != this.topic :
                        this.logDebug( f'{skill.name}: changing topic to "{this.newTopic}"' )
                        for s in this.skills:
                            if s.isSubscribed( this.topic ) or s.isSubscribed( this.newTopic ):
                                s.onTopicChange( this.topic, this.newTopic )
                        this.topic = this.newTopic
                        this.newTopic = None

                    # If current skill requested to abort further processing
                    if this.parsingRestart: 
                        this.logDebug( 'Перезапуск анализа фразы' )
                        break
                    if this.parsingStopped: 
                        this.logDebug( 'Анализ фразы прерван' )
                        break
                except Exception as e:
                    this.logError( f'{skill.name}.{method} exception: {e}' )
            if not this.parsingRestart : break

        if final:
            if this.topic == TOPIC_DEFAULT and this.lastAnimation == ANIMATION_AWAKE : 
                this.animate( ANIMATION_NONE )
        else:
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

    def extendVocabulary(this, words ) :
        """Расширить словарь. Принимает списки слов как в виде строк так и в виде массивов (рекурсивно)"""
        if isinstance( words, list) :
            for word in words : this.extendVocabulary( word )
        elif isinstance( words, str ):
            this.vocabulary = joinWords( this.vocabulary, words )

    def getVocabulary( this ) -> str:
        """Возвращает полный текущий список слов для фильтрации распознавания речи 
           или пустую строку если фильтрация не используется
        """
        return this.vocabulary if this.usingVocabulary else ''

    def loadEntities( this, entityFileName ):
        entities = list()
        p = ConfigParser( os.path.join( 'lvt','entities', entityFileName ) )
        for v in p.values:
            entity = list()
            for i in range( 2,len( v ) ):
                entity.append( v[i] )
            entities.append( entity )
        return entities

# UpdateClient
#region
    def updateClient(this):
        def packageFile( fileName ):
            with open( os.path.join( ROOT_DIR, fileName), "r", encoding='utf-8' ) as f:
                package.append( (fileName, f.readlines() ) )
        def packageDirectory( dir ):
            files = os.listdir( os.path.join( ROOT_DIR, dir ) )
            for file in files:
                if file.endswith('.py') : 
                    packageFile( os.path.join( dir, file ) )

        package = []
        packageFile('lvt_client.py')
        packageDirectory( 'lvt' )
        packageDirectory( os.path.join( 'lvt','client' ) )
        this.sendMessage( MSG_UPDATE, json.dumps( package, ensure_ascii=False ))

#endregion
# Logging
#region
    def logError( this, message:str ):
        printDebug( f'[{this.id}] {message}' )

    def log( this, message:str ):
        print( f'{this.id}] {message}' )
            
    def logDebug( this, message:str ):
        logDebug( f'[{this.id}] {message}' )

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

    def animate( this, animation:str, force:bool=False ):
        """Передать слиенту запрос на анимацию"""
        if force or animation != this.lastAnimation:
            this.lastAnimation = animation
            this.sendMessage( MSG_ANIMATE, animation )

    def sendMessage( this, msg:str, p1:str=None, p2:str=None ):
        message = MESSAGE( msg, p1, p2 )
        m = message if len(message)<80 else message[:80]+'...'
        this.logDebug( f'Message: {m}' )
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
    def loadTerminals():
        """Кеширует в память список сконфигурированных терминалов"""
        global config
        global terminals
        """Returns dictionary of terminals[terminalId]
        terminalId is a lowered terminal config file name
        """
        dir = os.path.join( 'lvt','terminals' )
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
                    print( f'Exception loading  "{file}" : {e}' )

    def authorize( terminalId:str, password:str, clientVersion ):
        """Авторизация терминала по terminalId и паролю"""
        terminalId = str( terminalId ).lower()
        for t in terminals :
            if t.id == terminalId and t.password == password: 
                t.clientVersion = clientVersion
                return( t )
        return None

    def initialize( gConfig ):
        """Initialize module' config variable for easier access """
        global config
        global terminals
        global rhvoiceTTS
        config = gConfig
        if config.ttsEngine == TTS_RHVOICE :
            import rhvoice_wrapper as rhvoiceWrapper # https://pypi.org/project/rhvoice-wrapper/
            try:
                rhvoiceTTS = rhvoiceWrapper.TTS( threads=1, 
                    data_path=config.rhvDataPath, 
                    config_path=config.rhvConfigPath,
                    lame_path=None, opus_path=None, flac_path=None,
                    quiet=True )
                
            except Exception as e:
                printError(f'Exception initializing RHVoice engine')
        else:
            pass

        Terminal.loadTerminals()
    def dispose():
        if config.ttsEngine == TTS_RHVOICE :
            try: rhvoiceTTS.join()
            except: pass
        else:
            pass

#endregion
