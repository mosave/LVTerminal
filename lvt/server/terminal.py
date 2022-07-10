from genericpath import isfile
import time
import json
import psutil
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
        #self.logDebug( f'Initializing terminal' )
        
        self.password = config.terminals[id]['password']
        self.name = config.terminals[id]['name']
        self.locations = entities.get('location', id)
        self.location = config.terminals[id]['location']

        self.ipAddress = ''
        self.autoUpdate = config.terminals[id]['autoupdate']
        self.clientVersion = ""
        # Использовать "словарный" режим
        self.useVocabulary = True
        self.preferFullModel = True

        self.lastSound = 0
        self.lastAppealed = None
        self.isAppealed = False
        self.isReacted = False
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
        self.connected = False
        self.connectedOn = None
        self.disconnectedOn = None
        self.playAppealOffIfNotStopped = False
        #self.logDebug( 'Loading skills' )

        self.allTopics = set()
        self.skills = SkillFactory( self ).loadSkills()

        for skill in self.skills:
            #self.logDebug( f'{skill.priority:6} {skill.name}' )
            self.allTopics = self.allTopics.union( skill.subscriptions )

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

        self.playerMuted = 0
        self.reset()

    def reset( self ):
        self.topic = TOPIC_DEFAULT
        self.topicParams = None
        self.isAppealed = False
        self.words = []
        self.originalText = ''
#endregion

#region sayAsync / playVoiceAsync / playAsync / playerMute / playerUnmute
    def playerMute(self):
        if self.playerMuted<=0:
            self.sendMessage(MSG_MUTE_PLAYER)
        self.playerMuted += 1

    def playerUnmute(self):
        if self.playerMuted>0:
            self.playerMuted -= 1
            if self.playerMuted==0:
                self.sendMessage(MSG_UNMUTE_PLAYER)
    
    async def sayAsync( self, text ):
        """Проговорить сообщение на терминал. 
          Текст сообщения так же дублируется командой "Text"
        """
        if self.tts is None: return
        voice = await self.tts.textToSpeechAsync(text)
        await self.playVoiceAsync(voice)

    async def playVoiceAsync( self, voice ):
        if voice is not None:
            self.playerMute()
            try:
                if time.time() - self.lastSound > 1 * 60:
                    await self.playAsync("ding.wav")
                self.lastSound = time.time()
                self.sendDatagram( voice )
            finally:
                self.playerUnmute()

    async def playAsync( self, waveFileName: str ):
        """Проиграть wave файл на терминале. Максимальный размер файла 500к """

        self.lastSound = time.time()
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
        self.playerMute()
        try:
            with open( waveFileName, 'rb' ) as wave:
                self.sendDatagram( wave.read( 500 * 1024 ) )
        finally:
            self.playerUnmute()
#endregion

#region Properties
    @property
    def text( self ) -> str:
        """Сгенерировать текст фразы из разобранных слов """
        return ' '.join([w[0].word for w in self.words])

    @text.setter 
    def text( self, newText: str ):
        # Кешируем морфологический разбор слов - для ускорения обработки фразы
        self.words = parseText( newText)

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

#region skills access
    def getSkill(self, skillName:str)-> Skill:
        for skill in self.skills:
            if skill.name.lower() == str(skillName).lower():
                return skill
        return None
#endregion

#region onConnectAsync() / onDisconnectAsync() 
    async def onConnectAsync( self, messageQueue ):
        """Метод вызывается при подключении терминального клиента
          messageQueue is synchronous message output queue
        """
        self.log( f'Terminal connected, client version {self.clientVersion}' )
        self.connected = True
        self.connectedOn = time.time()
        self.messageQueue = messageQueue
        self.playerMuted = 0
        # В случае, если предыдущая сессия закончилась недавно
        if self.disconnectedOn is not None and self.connectedOn - self.disconnectedOn < 60 :
            while len( self.messages ) > 0:
                messageQueue.append( self.messages[0] )
                self.messages.pop( 0 )
        else: # Необходимо переинициализировать состояние терминала
            self.reset()

        self.sendMessage( MSG_ANIMATE, ANIMATION_NONE )
        self.sendMessage( MSG_LVT_STATUS, json.dumps(getState()) )
        if bool(self.sayOnConnect) :
            self.sendMessage(MSG_MUTE)
            await self.sayAsync(self.sayOnConnect)
            self.sendMessage(MSG_UNMUTE)
            self.sayOnConnect = None
        #await self.sayAsync('Terminal Connected. Терминал подключен.')

    async def onDisconnectAsync( self ):
        """Вызывается при (после) завершения сессии"""
        self.log( 'Terminal disconnected' )
        self.connected = False
        self.disconnectedOn = time.time()
        self.messageQueue = None
#endregion

#region onTextAsync()
    async def onTextAsync( self, text:str, speakerSignature ) -> bool:
        """Основная точка входа для обработки полностью распознанного фрагмента """
        # Морфологический разбор слов текста
        self.text = text
        self.originalText = text

        if len( speakerSignature ) > 0 : # Идентифицировать говоращего по сигнатуре
            self.speaker = speakers.identify( speakerSignature )
        else:
            self.speaker = None

        speakerName = self.speaker.name if self.speaker is not None else 'Человек'
        self.logDebug( f'{speakerName}: "{text}"' )
        self.isReacted = False

        self.isAppealed = False
        processed = False
        t0 = self.text
        while True:
            self.newTopic = None
            self.newTopicParams = {}
            self.parsingStopped = False
            self.parsingRestart = False
            for skill in self.skills:
                # Пропускать скиллы, не подписанные на текущий топик:
                if skill.isSubscribed( self.topic ) : 
                    try:
                        # Отработать onText
                        await skill.onTextAsync()
                        t1 = self.text
                        if t1 != t0:
                            self.logDebug( f'{skill.name}.onTextAsync(): text changed to "{self.text}"' )
                            t0 = t1

                        if self.parsingStopped:
                            processed = True
                            self.logDebug( f'{skill.name}.onTextAsync(): Анализ фразы завершен' )
                            break

                    except Exception as e:
                        self.logError( f'{skill.name}.onTextAsync() exception: {e}' )

            if not self.parsingRestart: break
            self.logDebug( 'Перезапуск анализа фразы' )

        if not self.parsingStopped : 
            self.logDebug( 'Анализ фразы завершен' )
            if self.playAppealOffIfNotStopped :
                self.playAppealOffIfNotStopped = False
                await self.playAsync( 'appeal_off.wav' )

        if self.isAppealed and not self.isReacted and (len(self.words)>0):
            if self.parsingStopped : 
                await self.playAsync('asr_ok.wav')
            else:
                await self.playAsync( 'asr_error.wav' )

       

        if self.topic == TOPIC_DEFAULT and self.lastAnimation != ANIMATION_NONE : 
            self.animate( ANIMATION_NONE )

        self.originalText = ''

        return processed
#endregion

#region onTimerAsync()
    async def onTimerAsync( self ):
        for skill in self.skills: 
            try:
                await skill.onTimerAsync()
            except Exception as e:
                self.logError( f'{skill.name}.onTimerAsync() exception: {e}' )
#endregion

#region changeTopicAsync
    async def changeTopicAsync( self, newTopic, params = None ):
        """Изменить текущий топик после завершения обработчика onText
         newTopic: новый топик, который требуется установить
         params: необязательные параметры
        """
        newTopic = str( newTopic )
        oldTopic = self.topic
        # if newTopic not in self.allTopics:
        #     raise ArgumentError(f'На топик "{newTopic}" отсутствуют подписки')

        self.logDebug( f'{self.name}.changeTopicAsync("{newTopic}", {params})' )

        # Обработать изменения топика
        if newTopic is not None and newTopic != oldTopic:
            self.logDebug( f'Topic: "{oldTopic }" =>  "{newTopic}"' )
            self.useVocabulary = True
            self.preferFullModel = True

            # Дернуть скилы, подписанные на текущий или новый топик
            for skill in self.skills:
                try:
                    if skill.isSubscribed( oldTopic ) or skill.isSubscribed( newTopic ):
                        await skill.onTopicChangeAsync( newTopic, params )
                except Exception as e:
                    self.logError( f'{skill.name}.onTopicChangeAsync() exception: {e}' )

            self.topic = newTopic

            if oldTopic == TOPIC_DEFAULT and self.topic != TOPIC_DEFAULT:
                self.playerMute()
            elif oldTopic != TOPIC_DEFAULT and self.topic == TOPIC_DEFAULT:
                self.playerUnmute()


#endregion

#region Vocabulary manipulations
    def getVocabulary( self ):
        """Возвращает полный текущий список слов для фильтрации распознавания речи 
           или пустую строку если фильтрация не используется
        """
        vocabulary = set()
        if self.topic == TOPIC_DEFAULT:
            vocabulary.update( wordsToVocabulary( config.assistantNames ) )
            vocabulary.update( wordsToVocabulary(' эй слушай' ) )
        for skill in self.skills:
            vocabulary.update( skill.getVocabulary(self.topic) )
        return vocabulary
#endregion

#region grammar helpers
    def conformToAppeal( self, text ) -> str:
        return inflectText(text, {config.gender})
        # p = parseWord( self.appeal )
        # gender = p[0].tag.gender if p is not None else None
        # if gender is None: gender = 'masc'
        # return inflectText(text, {gender})

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
            'Location': self.location,
            'Connected':bool(self.connected),
            'IPAddress': self.ipAddress,
            'Version': self.clientVersion,
            'Address':self.ipAddress,
            'Volume': self.volume,
            'Filter': self.filter
        }
        return states[self.id]

    def animate( self, animation:str ):
        """Передать клиенту запрос на анимацию"""
        if animation != self.lastAnimation:
            self.lastAnimation = animation if animation in ANIMATION_STICKY  else ANIMATION_NONE
            self.sendMessage( MSG_ANIMATE, animation )

    def sendMessage( self, msg:str, p1:str=None, p2:str=None ):
        message = MESSAGE( msg, p1, p2 )
        m = message if len( message ) < 80 else message[:80] + '...'
        self.logDebug( f'Message: {m}' )
        if self.messageQueue is not None:
            self.messageQueue.append( message )
        else:
            self.messages.append( message )

    def sendDatagram( self, data ):
        self.logDebug( f'Datagram: {int(len(data)/1024)}kB' )
        self.isReacted = True
        if self.messageQueue is not None:
            self.messageQueue.append( data )
        else:
            self.messages.append( data )

    async def reboot(self, say: str = None, sayOnConnect: str = None):
        if bool(say):
            await self.sayAsync(say)
        self.sendMessage(MSG_REBOOT)
        self.sayOnConnect = sayOnConnect
        
#endregion

#region Updating client
    async def updateClient( self, say='Обновление терминала', sayOnConnect='Терминал обновлен' ):
        def packageFile( fileName, targetFileName=None ):
            with open( os.path.join( ROOT_DIR, fileName ), "r", encoding='utf-8' ) as f:
                package.append( (targetFileName if bool(targetFileName) else fileName, f.readlines()) )
        def packageDirectory( dir ):
            files = os.listdir( os.path.join( ROOT_DIR, dir ) )
            for file in files:
                if file.endswith( '.py' ) : 
                    packageFile( os.path.join( dir, file ) )
        if bool(say):
            await self.sayAsync(say)
        package = []
        packageFile( 'lvt_client.py' )
        #packageFile( 'lvt_client.sh' )
        packageFile( 'requirements_client.txt' )
        packageDirectory( 'lvt' )
        packageDirectory( os.path.join( 'lvt','client' ) )
        cfg = os.path.join(CONFIG_DIR,f"client_{self.id}.cfg")
        if os.path.isfile(cfg):
            packageFile( cfg, os.path.join('config',f"client_{self.id}.cfg"))
            packageFile( cfg, os.path.join('config','client.cfg'))
        self.sendMessage( MSG_UPDATE, json.dumps( package, ensure_ascii=False ) )
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
        if t.connected : terminalsConnected += 1
        t.getState()

    return {
        'Model': config.model,
        'GModel': config.gModel,
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

