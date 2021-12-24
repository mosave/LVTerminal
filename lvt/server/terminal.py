import time
import datetime
import json
import hashlib
import wave
import psutil
from numpy import random
from threading import Lock, Thread
from lvt.const import *
from lvt.logger import *
from lvt.protocol import *
from lvt.config_parser import ConfigParser
from lvt.server.grammar import *
import lvt.server.config as config
import lvt.server.speakers as speakers
from lvt.server.entities import Entities
from lvt.server.skill import Skill
from lvt.server.skill_factory import SkillFactory

#pip3 install pywin32
# win32 should be imported globally. No other options but tru/except found
try:
    import win32com.client
    import pythoncom
except:
    pass

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

#region init
    def __init__( self, id ):
        self.id = id
        self.logDebug( f'Initializing terminal' )
        self.entities = Entities()
        
        self.password = config.terminals[id]['password']
        self.name = config.terminals[id]['name']
        self.defaultLocation = self.entities.findLocation(config.terminals[id]['location'])
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

        self.lastAnimation = ''

        self.appeal = wordsToList( config.assistantNames )[0]

        self.reset()

    def reset( self ):
        self.topic = TOPIC_DEFAULT
        self.topicParams = None
        self.appealPos = None
        self.isAppealed = False
        self.words = list()
#endregion

#region Say / Play
    def say( self, text ):
        """Проговорить сообщение на терминал. 
          Текст сообщения так же дублируется командой "Text"
        """
        global ttsRHVoice
        global ttsLock
        global ttsLocked

        if isinstance(text, list):
            text = text[random.randint(len(text))]

        self.logDebug( f'Say "{text}" with {config.ttsEngine}' )

        if not config.ttsEngine:
            return

        if time.time() - self.lastSound > 1 * 60:
            self.play("ding.wav")

        self.lastSound = time.time()

        wfn = hashlib.sha256((config.ttsEngine+'-'+config.voice+'-'+text).encode()).hexdigest()

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
            #self.sendMessage( MSG_TEXT
            #
            #, text )
            if not os.path.isfile(waveFileName): 
                self.log(f'generating wav, engine={config.ttsEngine} ')
                if (config.ttsEngine == TTS_RHVOICE) and (ttsRHVoice != None):
                    rhvParams = config.rhvParams
                    # https://pypi.org/project/rhvoice-wrapper/

                    frames = ttsRHVoice.get( text, 
                        voice= rhvParams['voice'],
                        format_='pcm', 
                        sets=rhvParams
                    )
                    fn = os.path.join( ROOT_DIR, 'logs', datetime.datetime.today().strftime(f'%Y%m%d_%H%M%S_say') )
                    f = open( fn+'.pcm','wb')
                    f.write(frames)
                    f.close()
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
                    ##self.sendMessage(MSG_MUTE)
                    #self.sendDatagram( wav )
                    ##self.sendMessage(MSG_UNMUTE)
                elif (config.ttsEngine == TTS_SAPI):
                    #https://docs.microsoft.com/en-us/previous-versions/windows/desktop/ms723602(v=vs.85)
                    pythoncom.CoInitialize()
                    sapi = win32com.client.Dispatch("SAPI.SpVoice")
                    sapiStream = win32com.client.Dispatch("SAPI.SpFileStream")
                    voices = sapi.GetVoices()
                    v = config.voice.lower().strip()
                    for voice in voices:
                        if voice.GetAttribute("Name").lower().strip().startswith(v):
                            sapi.Voice = voice
                    sapi.Rate = config.sapiRate
                    sapiStream.Open( waveFileName, 3 )
                    sapi.AudioOutputStream = sapiStream
                    sapi.Speak(text)
                    sapi.WaitUntilDone(-1)
                    sapiStream.Close()

            if os.path.isfile(waveFileName): 
                with open( waveFileName, 'rb' ) as f:
                    self.sendDatagram( f.read( 5000 * 1024 ) )
            else:
                self.logError(f'File {waveFileName} not found')
        except Exception as e:
            self.logError( f'TTS Engine exception: {e}' )

        ttsLock.acquire()
        ttsLocked.remove(wfn)
        ttsLock.release()


    def play( self, waveFileName: str ):
        self.lastSound = time.time()
        """Проиграть wave файл на терминале. Максимальный размер файла 500к """
        if os.path.dirname( waveFileName ) == '' :
           waveFileName = os.path.join( ROOT_DIR,'lvt','sounds',waveFileName )
        with open( waveFileName, 'rb' ) as wave:
            self.sendDatagram( wave.read( 500 * 1024 ) )
#endregion

#region Properties

    @property
    def locations( self ):
        """Список локаций, распознанные при анализе фразы либо локация, заданная в конфигурации терминала"""
        return ( self.parsedLocations if len( self.parsedLocations ) > 0 else [self.defaultLocation] )

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


#endregion

#region onConnect() / onDisconnect() 
    def onConnect( self, messageQueue ):
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
        self.sendMessage( MSG_LVT_STATUS, json.dumps(getLVTStatus()) )
        if self.sayOnConnect :
            self.sendMessage(MSG_MUTE)
            self.say(self.sayOnConnect)
            self.sendMessage(MSG_UNMUTE)
            self.sayOnConnect = None
        #self.say('Terminal Connected. Терминал подключен.')
    def onDisconnect( self ):
        """Вызывается при (после) завершения сессии"""
        self.log( 'Terminal disconnected' )
        self.isConnected = False
        self.disconnectedOn = time.time()
        self.messageQueue = None
#endregion

#region onText()
    def onText( self, voice, text:str, textUnfiltered: str, speakerSignature ) -> bool:
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
                        skill.onText()
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

            self.processTopicChange()

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
    def onTimer( self ):

        self.newTopic = None
        self.newTopicParams = {}
        for skill in self.skills: 
            try:
                skill.onTimer()
            except Exception as e:
                self.logError( f'{skill.name}.onTimer() exception: {e}' )
        self.processTopicChange()
#endregion

#region changeTopic / processTopicChange()
    def processTopicChange( self ):
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
                        skill.onTopicChange( newTopic, newTopicParams )
                except Exception as e:
                    self.logError( f'{skill.name}.onTopicChange() exception: {e}' )

            self.topic = newTopic

    def changeTopic( self, newTopic, *params, **kwparams ):
        """Изменить текущий топик. Выполняется ПОСЛЕ выхода из обработчика onText"""
        self.newTopic = str( newTopic )

        p = kwparams
        if len( params ) == 1 and isinstance( params[0],dict ) : 
            p.update( params[0] )
        elif len( params ) > 0 : 
            p.update( {'params':params} )
        self.newTopicParams = p
        self.logDebug( f'{self.name}.changeTopic("{newTopic}", {p}) ]' )
        self.processTopicChange()
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

        self.extendVocabulary( self.entities.vocabulary )
        self.extendVocabulary( self.entities.acronyms )
        self.extendVocabulary( self.entities.locations )
        
        for skill in self.skills:
            self.vocabulary.update( skill.vocabulary )
#endregion

#region Updating client
    def updateClient( self ):
        def packageFile( fileName ):
            with open( os.path.join( ROOT_DIR, fileName ), "r", encoding='utf-8' ) as f:
                package.append( (fileName, f.readlines()) )
        def packageDirectory( dir ):
            files = os.listdir( os.path.join( ROOT_DIR, dir ) )
            for file in files:
                if file.endswith( '.py' ) : 
                    packageFile( os.path.join( dir, file ) )

        self.say("Обновление терминала.")

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

#region Messages, animate, getStatus
    def getStatus( self ):
        """JSON строка с описанием текущего состояния терминала на стороне сервера
          Используется для передачи на сторону клиента.
          Клиент при этом уже авторизован паролем
        """
        return {
            'Terminal':self.id,
            'Name':self.name,
            'Location': self.defaultLocation,
            'Connected':bool(self.isConnected),
            'Address':self.ipAddress,
        }


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
def TerminalAuthorize( terminalId:str, password:str, clientVersion ):
    """Авторизация терминала по terminalId и паролю"""
    terminalId = str( terminalId ).lower()
    for t in terminals :
        if t.id == terminalId and t.password == password: 
            t.clientVersion = clientVersion
            return( t )
    return None

def TerminalFind( terminalId:str ):
    """Авторизация терминала по terminalId и паролю"""
    terminalId = str( terminalId ).lower()
    for t in terminals :
        if t.id == terminalId :
            return( t )
    return None

def TerminalInit():
    """Initialize module' config variable for easier access """
    global terminals
    global ttsRHVoice
        
    if config.ttsEngine == TTS_RHVOICE :
        import rhvoice_wrapper as rhvoiceWrapper # https://pypi.org/project/rhvoice-wrapper/
        try:
            ttsRHVoice = rhvoiceWrapper.TTS( 
                threads = 1,
                lib_path = config.rhvParams['lib_path'] if 'lib_path' in config.rhvParams else object(),
                data_path = config.rhvParams['data_path'] if 'data_path' in config.rhvParams else object(), 
                resources = config.rhvParams['resources'] if 'resources' in config.rhvParams else object(),
                lame_path = config.rhvParams['lame_path'] if 'lame_path' in config.rhvParams else object(),
                opus_path = config.rhvParams['opus_path'] if 'opus_path' in config.rhvParams else object(),
                flac_path = config.rhvParams['flac_path'] if 'flac_path' in config.rhvParams else object(),
                quiet = True,
                config_path = config.rhvParams['config_path'] if '' in config.rhvParams else object()
                )
                
        except Exception as e:
            logError( f'Exception initializing RHVoice engine: {e}' )
    elif config.ttsEngine == TTS_SAPI:
        pass
    else:
        pass

    terminals = list()
    for id in config.terminals: 
        terminals.append( Terminal( id ) )


def TerminalDispose():
    if config.ttsEngine == TTS_RHVOICE :
        try: ttsRHVoice.join()
        except: pass
    else:
        pass

#endregion 


#region getLVTStatus() 
def getLVTStatus():
    global terminals
    """Returns 'public' options and system state suitable for sending to terminal client """
    def formatSize( bytes, suffix='B' ):
        """ '1.20MB', '1.17GB'..."""
        factor = 1024
        for unit in ['', 'K', 'M', 'G', 'T', 'P']:
            if bytes < factor:
                return f'{bytes:.2f}{unit}{suffix}'
            bytes /= factor

    cpufreq = psutil.cpu_freq()
    svmem = psutil.virtual_memory()
    terminalsTotal = 0
    terminalsConnected = 0
    trms = dict()
    if terminals != None :
        for t in terminals :
            if t.isConnected : terminalsConnected += 1
            trms[t.id] = t.getStatus()
        terminalsTotal = len(terminals)

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
        'TerminalsTotal': terminalsTotal,
        'TerminalsConnected': terminalsConnected,
        'Terminals': trms,
        'CpuCores': os.cpu_count(),
        'CpuFreq':f"{cpufreq.current:.2f}Mhz",
        'CpuLoad': f"{psutil.cpu_percent()}%",
        'MemTotal':formatSize(svmem.total),
        'MemAvail':formatSize(svmem.available),
        'MemUsed':formatSize(svmem.used),
        'MemLoad':f"{svmem.percent}%"
    }

#endregion

