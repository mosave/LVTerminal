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
        if this.password == '': raise Exception( f'Termininal configuration error: Password is not defined' )
        this.name = configParser.getValue( '','Name',this.id )
        this.verbose = configParser.getIntValue( '', 'verbose', 0 ) == '1'
        this.location = configParser.getValue( '','Location', '' )

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

        this.connectedOn = None
        this.disconnectedOn = None

        this.states = set()

        f = SkillFactory(this)
        this.skills = f.loadSkills()
        for skill in this.skills:
            this.states = this.states.union(skill.subscriptions )



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

        if final:
            print(text)

            if this.verbose : this.sendMessage( MSG_TEXT,f'Распознано: "{text}"' )
            this.isAwaken = False
            this.animate( ANIMATION_NONE )

    def onTimer( this ):
        #print('onTimer')
        pass


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
                    print( f'Exception loading  "{file}" : {e}' )
                    pass

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
