from genericpath import isfile
import time
import json
import hashlib
import wave
import psutil
from numpy import random
from threading import Lock, Thread
from lvt.const import *
from lvt.logger import *
from lvt.protocol import *
from lvt.server.grammar import *
import lvt.server.config as config
import lvt.server.speakers as speakers
import lvt.server.entities as entities
from lvt.server.skill import Skill
from lvt.server.skill_factory import SkillFactory
from lvt.server.tts import TTS

terminals = {}
states = {}

class Terminal():
    """Terminal class
    Properties
      * id: Unique terminal Id, used for client identification
      * password: Password for client identification
      * name: terminal name, speech-friendly Id
      * speaker: Speaker object containing last speaking person details if available
    """

#region init
    def __init__( self, id ):
        global states
        self.id = id
        self.logDebug( f'Initializing terminal' )
        
        self.password = config.terminals[id]['password']
        self.name = config.terminals[id]['name']
        self.locations = entities.get('location', id)
        self.defaultLocation = config.terminals[id]['location']

        #len()[l for l in self.locations if l.id==str(self.defaultLocation).lower()]>0)

        self.ipAddress = ''
        self.autoUpdate = config.terminals[id]['autoupdate']
        self.clientVersion = ""
        # Использовать "словарный" режим
        self.vocabulary = set()


        self.parsedLocations = []

        self.lastSound = 0
        self.lastAppealed = None
        self.appealPos = None
        self.isAppealed = False
        # messages are local output messages buffer used while terminal is
        # disconnected
        self.messages = list()

        # messageQueue is an external output message queue
        # It is assigned on terminal connection and invalidated (set to None)
        # on disconnection
        self.messageQueue = None

        # Speaker() class instance for last recognized speaker (if any)
        self.speaker = None

        self.sayOnConnect = None
        self.isConnected = False
        self.connectedOn = None
        self.disconnectedOn = None
        self.playAppealOffIfNotStopped = False
        self.answerPrefix = ''
        self.logDebug( 'Loading skills' )

        self.allTopics = set()
        self.skills = SkillFactory( self ).loadSkills()

        for skill in self.skills:
            self.logDebug( f'{skill.priority:6} {skill.name}' )
            self.allTopics = self.allTopics.union( skill.subscriptions )

        self.updateVocabulary()

        if config.ttsEngine:
            self.tts = TTS()
        else:
            self.tts = None

        self.lastAnimation = ''

        self.appeal = wordsToList( config.assistantNames )[0]

        self.__volume = 30
        self.__filter = 0
        if id in states:
            if 'Volume' in states[id]:
                self.__volume = int(states[id]['Volume'])
            if 'Filter' in states[id]:
                self.__filter = int(states[id]['Filter'])

        self.playerMuted = False
        self.reset()

    def reset( self ):
        self.topic = TOPIC_DEFAULT
        self.topicParams = None
        self.appealPos = None
        self.isAppealed = False
        self.words = list()
#endregion

#region sayAsync / playVoice / play
    def playerMute(self):
        if not self.playerMuted:
            self.playerMuted = True
            self.sendMessage(MSG_MUTE_PLAYER)

    def playerUnmute(self):
        if self.playerMuted:
            self.playerMuted = False
            self.sendMessage(MSG_UNMUTE_PLAYER)
    
    async def sayAsync( self, text ):
        """Проговорить сообщение на терминал. 
          Текст сообщения так же дублируется командой "Text"
        """
        if self.tts == None: return
        voice = await self.tts.textToSpeechAsync(text)
        self.playVoice(voice)

    def playVoice( self, voice ):
        if voice != None:
            self.playerMute()
            if time.time() - self.lastSound > 1 * 60:
                self.play("ding.wav")
            self.lastSound = time.time()
            self.sendDatagram( voice )
            self.playerUnmute()

    def play( self, waveFileName: str ):
        self.lastSound = time.time()
        """Проиграть wave файл на терминале. Максимальный размер файла 500к """
        fn, ext = os.path.splitext( waveFileName )
        if ext == '':
            ext = ".wav"
        waveFileName = fn + ext

        if os.path.dirname( waveFileName ) == '' :
            wfn = os.path.join( ROOT_DIR,'lvt','sounds',waveFileName )
            if isfile(wfn):
                waveFileName = wfn
            else:
                wfn = os.path.join( CONFIG_DIR, waveFileName )
                if isfile(wfn):
                    waveFileName = wfn
        with open( waveFileName, 'rb' ) as wave:
            pm = self.playerMuted
            if not pm:
                self.playerMute()
            self.sendDatagram( wave.read( 500 * 1024 ) )
            if not pm:
                self.playerUnmute()
#endregion

#region Properties
    @property
    def text( self ) -> str:
        """Сгенерировать текст фразы из разолранных слов """
        text = ''
        for w in self.words: text += w[0].word + ' '
        return text.strip()

    @text.setter 
    def text( self, newText: str ):
        # Кешируем морфологический разбор слов - для ускорения обработки фразы
        self.words = parseText( newText)

    @property
    def textUnfiltered( self ) -> str:
        """Сгенерировать текст фразы из разолранных слов """
        text = ''
        for w in self.wordsUnfiltered: text += w[0].word + ' '
        return text.strip()

    @textUnfiltered.setter 
    def textUnfiltered( self, newTextUnfiltered: str ):
        # Кешируем морфологический разбор слов - для ускорения обработки фразы
        self.wordsUnfiltered = parseText( newTextUnfiltered)

    @property
    def volume(self) -> int:
        return self.__volume

    @volume.setter
    def volume(self, newVolume: int ):
        newVolume = int(newVolume)
        if newVolume<0: newVolume=0
        if newVolume>100: newVolume = 100
        if self.__volume != newVolume:
            self.sendMessage( MSG_VOLUME, newVolume )
            self.__volume = newVolume
            self.getState()

    @property
    def filter(self) -> int:
        return self.__filter

    @filter.setter
    def filter(self, newFilter: int ):
        newFilter = int(newFilter)
        if newFilter<0: newFilter=0
        if newFilter>4: newFilter = 4
        if self.__filter != newFilter:
            self.__filter = newFilter
            self.getState()

#endregion

#region onConnect() / onDisconnect() 
    async def onConnect( self, messageQueue ):
        """Метод вызывается при подключении терминального клиента
          messageQueue is synchronous message output queue
        """
        self.log( f'Terminal connected, client version {self.clientVersion}' )
        self.isConnected = True
        self.connectedOn = time.time()
        self.messageQueue = messageQueue
        # В случае, если предыдущая сессия закончилась недавно
        if self.disconnectedOn != None and self.connectedOn - self.disconnectedOn < 60 :
            while len( self.messages ) > 0:
                messageQueue.append( self.messages[0] )
                self.messages.pop( 0 )
        else: # Необходимо переинициализировать состояние терминала
            self.reset()

        self.sendMessage( MSG_ANIMATE, ANIMATION_NONE )
        self.sendMessage( MSG_LVT_STATUS, json.dumps(getState()) )
        if self.sayOnConnect :
            self.sendMessage(MSG_MUTE)
            await self.sayAsync(self.sayOnConnect)
            self.sendMessage(MSG_UNMUTE)
            self.sayOnConnect = None
        #await self.sayAsync('Terminal Connected. Терминал подключен.')
    def onDisconnect( self ):
        """Вызывается при (после) завершения сессии"""
        self.log( 'Terminal disconnected' )
        self.isConnected = False
        self.disconnectedOn = time.time()
        self.messageQueue = None
#endregion

#region onText()
    async def onText( self, voice, text:str, textUnfiltered: str, speakerSignature ) -> bool:
        """Основная точка входа для обработки полностью распознанного фрагмента """
        self.voice = voice
        # Морфологический разбор слов текста (words и wordsUnfiltered)
        self.text = text
        self.originalText = text
        self.textUnfiltered = textUnfiltered
        self.originalTextUnfiltered = textUnfiltered

        if len( speakerSignature ) > 0 : # Идентифицировать говоращего по сигнатуре
            self.speaker = speakers.identify( speakerSignature )
        else:
            self.speaker = None

        speakerName = self.speaker.name if self.speaker != None else 'Человек'
        self.logDebug( f'{speakerName}: "{text}"' )

        processed = False
        t0 = self.text
        while True:
            self.appealPos = None
            self.isAppealed = False
            self.parsedLocations = []
            self.newTopic = None
            self.newTopicParams = {}
            self.parsingStopped = False
            self.parsingRestart = False
            for skill in self.skills:
                # Пропускать скиллы, не подписанные на текущий топик:
                if skill.isSubscribed( self.topic ) : 
                    try:
                        # Отработать onText
                        await skill.onText()
                        t1 = self.text
                        if t1 != t0:
                            self.logDebug( f'{skill.name}.onText(): text changed to "{text}"' )
                            t0 = t1

                        if self.parsingStopped : 
                            processed = True
                            self.logDebug( f'{skill.name}.onText(): Анализ фразы завершен' )
                            break

                    except Exception as e:
                        self.logError( f'{skill.name}.onText() exception: {e}' )

            await self.processTopicChange()

            if not self.parsingRestart: break
            self.logDebug( 'Перезапуск анализа фразы' )

        if not self.parsingStopped : 
            self.logDebug( 'Анализ фразы завершен' )
            if self.playAppealOffIfNotStopped :
                self.playAppealOffIfNotStopped = False
                self.play( 'appeal_off.wav' )
        

        if self.topic == TOPIC_DEFAULT and self.lastAnimation != ANIMATION_NONE : 
            self.animate( ANIMATION_NONE )

        return processed
#endregion

#region onTimer()
    async def onTimer( self ):

        self.newTopic = None
        self.newTopicParams = {}
        for skill in self.skills: 
            try:
                await skill.onTimer()
            except Exception as e:
                self.logError( f'{skill.name}.onTimer() exception: {e}' )
        await self.processTopicChange()
#endregion

#region changeTopic / processTopicChange()
    async def processTopicChange( self ):
        # Обработать изменения топика
        while self.newTopic != None and self.newTopic != self.topic:
            newTopic = self.newTopic
            newTopicParams = self.newTopicParams
            self.newTopic = None
            self.newTopicParams = {}
            self.logDebug( f'New topic "{newTopic}"' )

            # Дернуть скилы, подписанные на текущий или новый топик
            for skill in self.skills:
                try:
                    if skill.isSubscribed( self.topic ) or skill.isSubscribed( newTopic ):
                        await skill.onTopicChange( newTopic, newTopicParams )
                except Exception as e:
                    self.logError( f'{skill.name}.onTopicChange() exception: {e}' )

            self.topic = newTopic

    async def changeTopic( self, newTopic, *params, **kwparams ):
        """Изменить текущий топик. Выполняется ПОСЛЕ выхода из обработчика onText"""
        self.newTopic = str( newTopic )

        p = kwparams
        if len( params ) == 1 and isinstance( params[0],dict ) : 
            p.update( params[0] )
        elif len( params ) > 0 : 
            p.update( {'params':params} )
        self.newTopicParams = p
        self.logDebug( f'{self.name}.changeTopic("{newTopic}", {p}) ]' )
        await self.processTopicChange()
#endregion

#region Vocabulary manipulations
    def extendVocabulary( self, words, tags=None ) :
        """Расширить словарь словоформами, удовлетворяющим тегам
        По умолчанию (tags = None) слова добавляется в том виде как они были переданы
        Принимает списки слов как в виде строк так и в виде массивов (рекурсивно)
        """
        self.vocabulary.update( wordsToVocabulary( words, tags ) )

    def getVocabulary( self ):
        """Возвращает полный текущий список слов для фильтрации распознавания речи 
           или пустую строку если фильтрация не используется
        """
        return self.vocabulary

    def updateVocabulary( self ):
        self.vocabulary = set()

        #self.extendVocabulary( self.name )
        self.extendVocabulary( config.assistantNames, {'NOUN', 'nomn', 'sing'} )

        self.extendVocabulary( 'эй слушай' )

        self.extendVocabulary( self.locations.getVocabulary() )
      
        for skill in self.skills:
            self.vocabulary.update( skill.vocabulary )
#endregion

#region Updating client
    async def updateClient( self ):
        def packageFile( fileName ):
            with open( os.path.join( ROOT_DIR, fileName ), "r", encoding='utf-8' ) as f:
                package.append( (fileName, f.readlines()) )
        def packageDirectory( dir ):
            files = os.listdir( os.path.join( ROOT_DIR, dir ) )
            for file in files:
                if file.endswith( '.py' ) : 
                    packageFile( os.path.join( dir, file ) )

        await self.sayAsync("Обновление терминала.")

        package = []
        packageFile( 'lvt_client.py' )
        packageDirectory( 'lvt' )
        packageDirectory( os.path.join( 'lvt','client' ) )
        self.sendMessage( MSG_UPDATE, json.dumps( package, ensure_ascii=False ) )
        self.sayOnConnect = 'Терминал обновлен.'
#endregion

#region Log wrappers
    def logError( self, message:str ):
        logError( f'[{self.id}] {message}' )

    def log( self, message:str ):
        print( f'[{self.id}] {message}' )
            
    def logDebug( self, message:str ):
        logDebug( f'[{self.id}] {message}' )

    def raiseException( self, message ):
        self.logError( message )
        raise Exception( message )
#endregion

#region Messages, animate, getState
    def getState( self ):
        """JSON строка с описанием текущего состояния терминала на стороне сервера
        """
        global states
        states[self.id] = {
            'Id':self.id,
            'Name':self.name,
            'Location': self.defaultLocation,
            'Connected':bool(self.isConnected),
            'IPAddress': self.ipAddress,
            'Version': self.clientVersion,
            'Address':self.ipAddress,
            'Volume': self.volume,
            'Filter': self.filter
        }
        return states[self.id]

    def animate( self, animation:str ):
        """Передать слиенту запрос на анимацию"""
        if animation != self.lastAnimation:
            self.lastAnimation = animation if animation in ANIMATION_STICKY  else ANIMATION_NONE
            self.sendMessage( MSG_ANIMATE, animation )

    def sendMessage( self, msg:str, p1:str=None, p2:str=None ):
        message = MESSAGE( msg, p1, p2 )
        m = message if len( message ) < 80 else message[:80] + '...'
        self.logDebug( f'Message: {m}' )
        if self.messageQueue != None:
            self.messageQueue.append( message )
        else:
            self.messages.append( message )

    def sendDatagram( self, data ):
        self.logDebug( f'Datagram: {int(len(data)/1024)}kB' )
        if self.messageQueue != None:
            self.messageQueue.append( data )
        else:
            self.messages.append( data )
    def reboot(self, sayOnConnect: str = None):
        self.sendMessage(MSG_REBOOT)
        self.sayOnConnect = sayOnConnect
#endregion

#region Static methods
def authorize( terminalId:str, password:str, clientVersion ):
    """Авторизация терминала по terminalId и паролю"""
    terminalId = str( terminalId ).lower()
    if terminalId in terminals:
        terminal = terminals[terminalId]
        if terminal.password == password: 
            terminal.clientVersion = clientVersion
            return( terminal )
    return None

def get( terminalId:str ):
    """Авторизация терминала по terminalId и паролю"""
    terminalId = str( terminalId ).lower()
    if terminalId in terminals:
        return( terminals[terminalId] )
    return None

def init():
    """Initialize module' config variable for easier access """
    global terminals
    global states

    terminals = {}
    for id in config.terminals: 
        terminals[id] = Terminal( id )
    states = {}
    for _, t in terminals.items():
        t.getState()


#endregion 

#region getState(), getUpdates

def getState( ) -> dict:
    global terminals
    global states
    """Returns 'public' options and state suitable for sending to terminal client """
    def formatSize( bytes, suffix='B' ):
        """ '1.20MB', '1.17GB'..."""
        factor = 1024
        for unit in ['', 'K', 'M', 'G', 'T', 'P']:
            if bytes < factor:
                return f'{bytes:.2f}{unit}{suffix}'
            bytes /= factor

    cpufreq = psutil.cpu_freq()
    svmem = psutil.virtual_memory()
    terminalsConnected = 0
    for _, t in terminals.items() :
        if t.isConnected : terminalsConnected += 1
        t.getState()

    return {
        'Model': config.model,
        'FullModel': config.fullModel,
        'SpkModel': config.spkModel,
        'SampleRate': VOICE_SAMPLING_RATE,
        'RecognitionThreads':config.recognitionThreads,
        'AssistantNames': normalizeWords(config.assistantNames ),
        'VoiceEngine': config.ttsEngine,
        'LogLevel': config.logLevel,
        'PrintLevel': config.printLevel,
        'StoreAudio':config.storeAudio,
        'TerminalsTotal': len(terminals),
        'TerminalsConnected': terminalsConnected,
        'Terminals': states,
        'CpuCores': os.cpu_count(),
        'CpuFreq':f"{cpufreq.current:.2f}Mhz",
        'CpuLoad': f"{psutil.cpu_percent()}%",
        'MemTotal':formatSize(svmem.total),
        'MemAvail':formatSize(svmem.available),
        'MemUsed':formatSize(svmem.used),
        'MemLoad':f"{svmem.percent}%"
    }

def getUpdates() ->dict:
    global terminals
    global __trmsCache
    updates = dict()
    for _, t in terminals.items() :
        tStatus = t.getState()
        if t.id not in __trmsCache:
            __trmsCache[t.id] = tStatus
            updates[t.id] = tStatus
        elif tStatus != __trmsCache[t.id]:
            __trmsCache[t.id] = tStatus
            updates[t.id] = tStatus
    return updates

#endregion

