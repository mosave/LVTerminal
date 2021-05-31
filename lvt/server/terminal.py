import sys
import time
import datetime
import json
import hashlib
import wave
from numpy import random
from threading import Lock, Thread
from lvt.const import *
from lvt.logger import *
from lvt.protocol import *
from lvt.config_parser import ConfigParser
from lvt.server.grammar import *
from lvt.server.entities import Entities
from lvt.server.devices import Devices
from lvt.server.skill import Skill
from lvt.server.skill_factory import SkillFactory

#pip3 install pywin32
# win32 should be imported globally. No other options but tru/except found
try:
    import win32com.client
    import pythoncom
except:
    pass


config = None
terminals = list()
ttsRHVoice = None
ttsLock = Lock()
ttsLocked = set()


class Terminal():
    """Terminal class
    Properties
      * id: Unique terminal Id, used for client identification
      * password: Password for client identification
      * name: terminal name, speech-friendly Id
      * speaker: Speaker object containing last speaking person details if available
    """
### Terminal initialization ############################################################
#region
    def __init__( this, id ):
        global config
        this.id = id
        this.logDebug( f'Initializing terminal' )
        this.entities = Entities()
        
        this.password = config.terminals[id]['password']
        this.name = config.terminals[id]['name']
        this.defaultLocation = this.entities.findLocation(config.terminals[id]['location'])

        this.autoUpdate = config.terminals[id]['autoupdate']

        this.clientVersion = ""
        # Использовать "словарный" режим
        this.vocabularyMode = config.vocabularyMode
        this.usingVocabulary = config.vocabularyMode
        this.vocabulary = set()


        this.parsedLocations = []

        this.lastActivity = time.time()
        this.lastSound = 0
        this.lastAppealed = None
        this.appealPos = None
        this.isAppealed = False
        # messages are local output messages buffer used while terminal is
        # disconnected
        this.messages = list()

        # messageQueue is an external output message queue
        # It is assigned on terminal connection and invalidated (set to None)
        # on disconnection
        this.messageQueue = None

        # Speaker() class instance for last recognized speaker (if any)
        this.speaker = None

        this.sayOnConnect = None
        this.isConnected = False
        this.connectedOn = None
        this.disconnectedOn = None
        this.playAppealOffIfNotStopped = False
        this.logDebug( 'Loading skills' )

        this.allTopics = set()
        this.skills = SkillFactory( this ).loadSkills( config )

        for skill in this.skills:
            this.logDebug( f'{skill.priority:6} {skill.name}' )
            this.allTopics = this.allTopics.union( skill.subscriptions )

        this.updateVocabulary()

        this.lastAnimation = ''

        this.appeal = wordsToList( config.femaleAssistantNames +' ' + config.maleAssistantNames )[0]

        this.reset()

    def reset( this ):
        this.topic = TOPIC_DEFAULT
        this.topicParams = None
        this.appealPos = None
        this.isAppealed = False
        this.words = list()
#endregion
### Say / Play #########################################################################
#region
    def say( this, text ):
        """Проговорить сообщение на терминал. 
          Текст сообщения так же дублируется командой "Text"
        """
        global ttsRHVoice
        global ttsLock
        global ttsLocked

        if isinstance(text, list):
            text = text[random.randint(len(text))]

        this.logDebug( f'Say "{text}" with {config.ttsEngine}' )

        if not config.ttsEngine:
            return

        if time.time() - this.lastSound > 1 * 60:
            this.play("ding.wav")

        this.lastSound = time.time()
        voice = ''
        if (config.ttsEngine == TTS_RHVOICE):
            voice = config.rhvParamsMale['voice'] if this.gender=='masc' else config.rhvParamsFemale['voice']
        elif (config.ttsEngine == TTS_SAPI):
            voice = config.sapiMaleVoice if this.gender=='masc' else config.sapiFemaleVoice

        wfn = hashlib.sha256((config.ttsEngine+'-'+voice+'-'+text).encode()).hexdigest()

        isLocked = True
        while isLocked:
            ttsLock.acquire()
            if not (wfn in ttsLocked):
                ttsLocked.add(wfn)
                isLocked = False
            ttsLock.release()
            if isLocked:
                time.sleep(0.1)
        try:
            waveFileName = os.path.join( ROOT_DIR,'cache', wfn+'.wav' )
            #print(f'wave file name= {waveFileName}')
            #this.sendMessage( MSG_TEXT, text )
            if not os.path.isfile(waveFileName): 
                if (config.ttsEngine == TTS_RHVOICE) and (ttsRHVoice != None):
                    rhvParams = config.rhvParamsMale if this.gender=='masc' else config.rhvParamsFemale
                    if rhvParams == None : rhvParams = config.rhvParamsMale 
                    if rhvParams == None : rhvParams = config.rhvParamsFemale
                    # https://pypi.org/project/rhvoice-wrapper/

                    frames = ttsRHVoice.get( text, 
                        voice= rhvParams['voice'],
                        format_='pcm', 
                        sets=rhvParams 
                    )
                    #fn = os.path.join( ROOT_DIR, 'logs', datetime.datetime.today().strftime(f'%Y%m%d_%H%M%S_say') )
                    #f = open( fn+'.pcm','wb')
                    #f.write(frames)
                    #f.close()
                    with wave.open( waveFileName, 'wb' ) as wav:
                        sampwidth = wav.setsampwidth(2)
                        nchannels = wav.setnchannels(1)
                        framerate = wav.setframerate(24000)
                        wav.writeframes( frames )

                    #ttsRHVoice.to_file( 
                    #    filename=waveFileName, 
                    #    text=text, 
                    #    voice=rhvParams['voice'], 
                    #    format_='wav',
                    #    sets=rhvParams )
                    #wav = ttsRHVoice.get( text, 
                    #    voice= rhvParams['voice'],
                    #    format_='wav', 
                    #    sets=rhvParams )
                    ##this.sendMessage(MSG_MUTE)
                    #this.sendDatagram( wav )
                    ##this.sendMessage(MSG_UNMUTE)
                elif (config.ttsEngine == TTS_SAPI):
                    #https://docs.microsoft.com/en-us/previous-versions/windows/desktop/ms723602(v=vs.85)
                    pythoncom.CoInitialize()
                    sapi = win32com.client.Dispatch("SAPI.SpVoice")
                    sapiStream = win32com.client.Dispatch("SAPI.SpFileStream")
                    voices = sapi.GetVoices()
                    v = (config.sapiMaleVoice if this.gender=='masc' else config.sapiFemaleVoice).lower().strip()
                    for voice in voices:
                        if voice.GetAttribute("Name").lower().strip().startswith(v):
                            sapi.Voice = voice
                    sapi.Rate = (config.sapiMaleRate if this.gender=='masc' else config.sapiFemaleRate)
                    sapiStream.Open( waveFileName, 3 )
                    sapi.AudioOutputStream = sapiStream
                    sapi.Speak(text)
                    sapi.WaitUntilDone(-1)
                    sapiStream.Close()

            if os.path.isfile(waveFileName): 
                with open( waveFileName, 'rb' ) as f:
                    this.sendDatagram( f.read( 5000 * 1024 ) )
            else:
                this.logError(f'File {waveFileName} not found')
        except Exception as e:
            this.logError( f'TTS Engine exception: {e}' )

        ttsLock.acquire()
        ttsLocked.remove(wfn)
        ttsLock.release()


    def play( this, waveFileName: str ):
        this.lastSound = time.time()
        """Проиграть wave файл на терминале. Максимальный размер файла 500к """
        if os.path.dirname( waveFileName ) == '' :
           waveFileName = os.path.join( ROOT_DIR,'lvt','sounds',waveFileName )
        with open( waveFileName, 'rb' ) as wave:
            this.sendDatagram( wave.read( 500 * 1024 ) )
#endregion
### Properties #########################################################################
#region
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
    def locations( this ):
        """Список локаций, распознанные при анализе фразы либо локация, заданная в конфигурации терминала"""
        return ( this.parsedLocations if len( this.parsedLocations ) > 0 else [this.defaultLocation] )

    @property
    def gender( this ):
        """Пол ассистента. Определяется по последнему обращению."""
        global config
        return 'masc' if this.appeal in wordsToList(config.maleAssistantNames) else 'femn'

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
            parses = parseWord( w )
            #Проигнорировать предикативы, наречия, междометия и частицы
            #if {'PRED'} not in parses[0].tag and {'ADVB'} not in parses[0].tag
            #and {'INTJ'} not in parses[0].tag and {'PRCL'} not in
            #parses[0].tag :
            #Проигнорировать междометия
            if {'INTJ'} not in parses[0].tag :
                this.words.append( parses )
#endregion
### onConnect() / onDisconnect() #######################################################
#region
    def onConnect( this, messageQueue:list() ):
        """Метод вызывается при подключении терминального клиента
          messageQueue is synchronous message output queue
        """
        this.log( f'Terminal connected, client version {this.clientVersion}' )
        this.isConnected = True
        this.connectedOn = time.time()
        this.messageQueue = messageQueue
        # В случае, если предыдущая сессия закончилась недавно
        if this.disconnectedOn != None and this.connectedOn - this.disconnectedOn < 60 :
            while len( this.messages ) > 0:
                messageQueue.append( this.messages[0] )
                this.messages.pop( 0 )
        else: # Необходимо переинициализировать состояние терминала
            this.reset()

        this.sendMessage( MSG_ANIMATE, ANIMATION_NONE )
        this.sendMessage( MSG_CONFIG, config.getJson() )
        if this.sayOnConnect :
            this.sendMessage(MSG_MUTE)
            this.say(this.sayOnConnect)
            this.sendMessage(MSG_UNMUTE)
            this.sayOnConnect = None
        #this.say('Terminal Connected. Терминал подключен.')
    def onDisconnect( this ):
        """Вызывается при (после) завершения сессии"""
        this.log( 'Terminal disconnected' )
        this.isConnected = False
        this.disconnectedOn = time.time()
        this.messageQueue = None
#endregion
### onText() ###########################################################################
#region
    def onText( this, text:str ):
        """Основная точка входа для обработки полностью распознанного фрагмента """
        text = normalizeWords( text )

        this.originalText = text
        speakerName = this.speaker.name if this.speaker != None else 'Человек'
        this.logDebug( f'{speakerName}: "{text}"' )

        # Провести морфологический разбор слов текста
        this.text = text
        if text != this.text :
            text = this.text
            this.logDebug( f'Вычищенный текст: "{text}"' )

        while True:
            this.appealPos = None
            this.isAppealed = False
            this.parsedLocations = []
            this.newTopic = None
            this.newTopicParams = {}
            this.parsingStopped = False
            this.parsingRestart = False
            for skill in this.skills:
                # Пропускать скиллы, не подписанные на текущий топик:
                if skill.isSubscribed( this.topic ) : 
                    try:
                        # Отработать onText / onPartialText
                        skill.onText()
                        if text != this.text:
                            text = this.text
                            this.logDebug( f'{skill.name}.onText(): text changed to "{text}"' )
                        if this.parsingStopped : 
                            this.logDebug( f'{skill.name}.onText(): Анализ фразы завершен' )
                            break
                    except Exception as e:
                        this.logError( f'{skill.name}.onText() exception: {e}' )

            this.processTopicChange()

            if not this.parsingRestart: break
            this.logDebug( 'Перезапуск анализа фразы' )

        if not this.parsingStopped : 
            this.logDebug( 'Анализ фразы завершен' )
            if this.playAppealOffIfNotStopped :
                this.playAppealOffIfNotStopped = False
                this.play( 'appeal_off.wav' )
        
        if this.topic == TOPIC_DEFAULT :
            this.usingVocabulary = this.vocabularyMode

        if this.topic == TOPIC_DEFAULT and this.lastAnimation != ANIMATION_NONE : 
            this.animate( ANIMATION_NONE )

#endregion
### onPartialText() ####################################################################
#region
    def onPartialText( this, text:str ):
        """Основная точка входа для обработки частично распознанного фрагмента """
        this.originalText = ''
        this.appealPos = None
        this.isAppealed = False
        # Провести морфологический разбор слов текста
        this.text = normalizeWords( text )
        this.parsingStopped = False
        for skill in this.skills:
            # Пропускать скиллы, не подписанные на текущий топик:
            if skill.isSubscribed( this.topic ) : 
                try:
                    skill.onPartialText()
                except Exception as e:
                    this.logError( f'{skill.name}.onPartialText() exception: {e}' )

#endregion
### onTimer() ##########################################################################
#region
    def onTimer( this ):

        this.newTopic = None
        this.newTopicParams = {}
        for skill in this.skills: 
            try:
                skill.onTimer()
            except Exception as e:
                this.logError( f'{skill.name}.onTimer() exception: {e}' )
        this.processTopicChange()
#endregion
### processTopicChange() ###############################################################
#region
    def processTopicChange( this ):
        # Обработать изменения топика
        while this.newTopic != None and this.newTopic != this.topic:
            newTopic = this.newTopic
            newTopicParams = this.newTopicParams
            this.newTopic = None
            this.newTopicParams = {}
            this.logDebug( f'New topic "{newTopic}"' )

            # Дернуть скилы, подписанные на текущий или новый топик
            for skill in this.skills:
                try:
                    if skill.isSubscribed( this.topic ) or skill.isSubscribed( newTopic ):
                        skill.onTopicChange( newTopic, newTopicParams )
                except Exception as e:
                    this.logError( f'{skill.name}.onTopicChange() exception: {e}' )

            this.topic = newTopic

#endregion
### Vocabulary manipulations ###########################################################
#region
    def extendVocabulary( this, words, tags=None ) :
        """Расширить словарь словоформами, удовлетворяющим тегам
        По умолчанию (tags = None) слова добавляется в том виде как они были переданы
        Принимает списки слов как в виде строк так и в виде массивов (рекурсивно)
        """
        this.vocabulary.update( wordsToVocabulary( words, tags ) )

    def getVocabulary( this ) -> str:
        """Возвращает полный текущий список слов для фильтрации распознавания речи 
           или пустую строку если фильтрация не используется
        """
        return this.vocabulary if this.usingVocabulary else ''

    def updateVocabulary( this ) -> str:
        this.vocabulary = set()

        #this.extendVocabulary( this.name )
        this.extendVocabulary( config.femaleAssistantNames, {'NOUN', 'nomn', 'sing'} )
        this.extendVocabulary( config.maleAssistantNames, {'NOUN', 'nomn', 'sing'} )

        this.extendVocabulary( 'эй слушай' )

        this.extendVocabulary( this.entities.vocabulary )
        this.extendVocabulary( this.entities.acronyms )
        this.extendVocabulary( this.entities.locations )
        devices = Devices()
        for dt in devices.deviceTypes:
            this.extendVocabulary( dt.names )
        for d in devices.devices.values():
            this.extendVocabulary( d.names )
        
        for skill in this.skills:
            this.vocabulary.update( skill.vocabulary )

#endregion
### Updating client ####################################################################
#region
    def updateClient( this ):
        def packageFile( fileName ):
            with open( os.path.join( ROOT_DIR, fileName ), "r", encoding='utf-8' ) as f:
                package.append( (fileName, f.readlines()) )
        def packageDirectory( dir ):
            files = os.listdir( os.path.join( ROOT_DIR, dir ) )
            for file in files:
                if file.endswith( '.py' ) : 
                    packageFile( os.path.join( dir, file ) )

        this.say("Обновление терминала.")

        package = []
        packageFile( 'client.py' )
        packageDirectory( 'lvt' )
        packageDirectory( os.path.join( 'lvt','client' ) )
        this.sendMessage( MSG_UPDATE, json.dumps( package, ensure_ascii=False ) )
        this.sayOnConnect = 'Терминал обновлен.'

#endregion
### Log wrappers #######################################################################
#region
    def logError( this, message:str ):
        logError( f'[{this.id}] {message}' )

    def log( this, message:str ):
        print( f'[{this.id}] {message}' )
            
    def logDebug( this, message:str ):
        logDebug( f'[{this.id}] {message}' )

    def raiseException( this, message ):
        this.logError( message )
        raise Exception( message )
#endregion
### Messages, animate, getStatus #######################################################
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
        #if this.usingVocabulary :
        #    js += f'"Vocabulary":' + json.dumps( list(this.vocabulary),
        #    ensure_ascii=False ) + ', '
        js += f'"Active":"{this.isActive}" '
        js += '}'
        return js

    def animate( this, animation:str ):
        """Передать слиенту запрос на анимацию"""
        if animation != this.lastAnimation:
            this.lastAnimation = animation if animation in ANIMATION_STICKY  else ANIMATION_NONE
            this.sendMessage( MSG_ANIMATE, animation )

    def sendMessage( this, msg:str, p1:str=None, p2:str=None ):
        message = MESSAGE( msg, p1, p2 )
        m = message if len( message ) < 80 else message[:80] + '...'
        this.logDebug( f'Message: {m}' )
        if this.messageQueue != None:
            this.messageQueue.append( message )
        else:
            this.messages.append( message )

    def sendDatagram( this, data ):
        this.logDebug( f'Datagram: {int(len(data)/1024)}kB' )
        if this.messageQueue != None:
            this.messageQueue.append( data )
        else:
            this.messages.append( data )
    def reboot(this, sayOnConnect: str = None):
        this.sendMessage(MSG_REBOOT)
        this.sayOnConnect = sayOnConnect

#endregion
### Static methods #####################################################################
#region
    def authorize( terminalId:str, password:str, clientVersion ):
        """Авторизация терминала по terminalId и паролю"""
        terminalId = str( terminalId ).lower()
        for t in terminals :
            if t.id == terminalId and t.password == password: 
                t.clientVersion = clientVersion
                return( t )
        return None

    def find( terminalId:str ):
        """Авторизация терминала по terminalId и паролю"""
        terminalId = str( terminalId ).lower()
        for t in terminals :
            if t.id == terminalId :
                return( t )
        return None

    def initialize( gConfig ):
        """Initialize module' config variable for easier access """
        global config
        global terminals
        global ttsRHVoice
        global sapiTTS
        global sapiStream
        global sapiMaleVoice
        global sapiFemaleVoice
        
        config = gConfig
        if config.ttsEngine == TTS_RHVOICE :
            import rhvoice_wrapper as rhvoiceWrapper # https://pypi.org/project/rhvoice-wrapper/
            try:
                ttsRHVoice = rhvoiceWrapper.TTS( threads=1, 
                    data_path=config.rhvDataPath, 
                    config_path=config.rhvConfigPath,
                    lame_path=None, opus_path=None, flac_path=None,
                    quiet=True )
                
            except Exception as e:
                this.logError( f'Exception initializing RHVoice engine' )
        elif config.ttsEngine == TTS_SAPI:
            pass
        else:
            pass

        terminals = list()
        for id in config.terminals: 
            terminals.append( Terminal( id ) )


    def dispose():
        if config.ttsEngine == TTS_RHVOICE :
            try: ttsRHVoice.join()
            except: pass
        else:
            pass

#endregion
