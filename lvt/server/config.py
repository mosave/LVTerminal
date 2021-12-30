import sys
import time
import os
import getopt
from lvt.const import *
from lvt.logger import *
from lvt.server.grammar import *
from lvt.config_parser import ConfigParser

fileName : str = 'server.cfg'
serverAddress : str = '0.0.0.0'
serverPort : int = 2700
apiServerPort : int = 7999
sslCertFile = None
sslKeyFile = None
model = None
fullModel = None
storeAudio = False
recognitionThreads : int = 4

# Распознавание голоса
spkModel = None
voiceSimilarity : float = 0.6
voiceSelectivity : float = 0.2
assistantNames = 'мажордом'
gender = 'masc'

logFileName = os.path.join( ROOT_DIR, "logs", "server.log")
logLevel = None
printLevel = None

voiceLogLevel = None
voiceLogDir = os.path.join( ROOT_DIR, "logs")

ttsEngine = None
voice = ''
rhvParams = dict()
sapiRate = 0.0

terminals = dict()
skills = dict()

def init():
    """Load LVT Server configuration.
    """
    global fileName
    global serverAddress
    global serverPort
    global apiServerPort
    global sslCertFile
    global sslKeyFile
    global model
    global gModel 
    global storeAudio
    global recognitionThreads

    global spkModel
    global voiceSimilarity
    global voiceSelectivity

    global assistantNames
    global gender

    global logFileName
    global logLevel
    global printLevel 
    global voiceLogLevel
    global voiceLogDir

    global ttsEngine
    global voice
    global rhvParams
    global sapiRate
    global terminals
    global skills

    withConfig = False

    for arg in sys.argv[1:]:
        a = arg.strip().lower()
        if ( a.startswith('-c=') or a.startswith('--config=') ) :
            fileName = a.split('=')[1]
            withConfig = True

    if not withConfig:
        ConfigParser.checkConfigFiles( [
            'server.cfg',
            'location.entity'
            ])
    p = ConfigParser( fileName )
    section = 'LVTServer'
    ### Network configuration
    serverAddress = p.getValue( section, 'ServerAddress','0.0.0.0' )
    serverPort = p.getIntValue( section, 'ServerPort',2700 )
    apiServerPort = p.getIntValue( section, 'APIServerPort', 7999 )
    sslCertFile = p.getValue( section, 'SSLCertFile','' )
    sslKeyFile = p.getValue( section, 'SSLKeyFile','' )

    storeAudio = bool(p.getValue(section,'StoreAudio','0') != '0')

    ### Voice recognition configuration 
    recognitionThreads = p.getIntValue( section, 'RecognitionThreads',int(str(os.cpu_count())) )
    if( recognitionThreads < 2 ): recognitionThreads = 2

    model = p.getValue( section, 'Model','' ).strip()
    gModel = p.getValue( section, 'GModel','' ).strip()
    if model=='' and gModel == '':
        __error( 'Необходимо указать хотя бы одну голосовую модель для распознавания', 'Model, GModel', section )


    ### Speaker identification config
    spkModel = p.getValue( section, 'SpkModel','' ).strip()
    if( spkModel != '' ) :
        if model=='' :
            __error( 'Идентификация по голосу работает только совместно с "полной" голосовой модель (параметр Model)', 'SpkModel', section )

        voiceSimilarity = p.getFloatValue( section, 'VoiceSimilarity', 0.6 )
        if( voiceSimilarity<0.1 or voiceSimilarity>1 ): 
            __error( '"Коэффициент похожести" голоса должен находиться в диапазоне 0.1 .. 1.0', 'VoiceSimilarity', section )

        voiceSelectivity = p.getFloatValue( section, 'VoiceSelectivity', 0.2 )
        if( voiceSelectivity<0 or voiceSelectivity>1.0 ): 
            __error( '"Коэффициент похожести" голоса должен находиться в диапазоне 0 .. 1.0', 'voiceSelectivity', section )

    ### Assistant configuration
    aNames = wordsToList(normalizeWords(p.getValue( section, 'AssistantNames','' )))
          
    if len( aNames ) == 0 : 
        __error( 'Необходимо задать хотя бы одно имя для ассистента', 'AssistantNames', section )

    assistantNames = ''
    for aName in aNames:
        assistantNames = (assistantNames + ' ' + normalFormOf( str(aName), {'NOUN','nomn','sing'} )).strip()

    gender = p.getValue( section, 'Gender','' ).strip().lower()
    if gender not in {'m','f'} :
        __error( 'Необходимо указать пол ассистента [M, F]', 'Gender', section )
    gender = 'masc' if gender=='m' else 'femn'


    ### Logging
    logFileName = p.getValue( section, "Log", None )
    if not bool(logFileName) :
        logFileName = "server.log"
    if os.path.dirname(logFileName) == '':
        logFileName = os.path.join( ROOT_DIR, "logs", logFileName)

    logLevel = p.getIntValue( section, "LogLevel",20 )
    printLevel = p.getIntValue( section, "PrintLevel",20 )

    voiceLogDir = p.getValue( section, "VoiceLogDir", None )
    if not bool(voiceLogDir) :
        voiceLogDir = os.path.join( ROOT_DIR, "logs")
    voiceLogLevel = p.getIntValue( section, "VoiceLogLevel",None )

    ### TTS Engine
    ttsEngine = p.getValue( section, 'TTSEngine', '' )

    if( ttsEngine.lower().strip() == TTS_RHVOICE.lower() ):
        ttsEngine = TTS_RHVOICE
        section = TTS_RHVOICE
        rhvParams = p.getValues( section )
        voice = str(p.getValue( section, 'Voice', '' )).strip()
        if voice == '' : __error(f'Не определена переменная Voice', 'Voice',  section )

    elif( ttsEngine.lower().strip() == TTS_SAPI.lower() ):
        ttsEngine = TTS_SAPI
        section = TTS_SAPI
        voice = str(p.getValue( section, 'Voice', '' )).strip()

        if voice=='' : __error( 'Не определена переменная Voice','Voice', section )

        sapiRate = p.getIntValue( section, "Rate", 0 )
        if (sapiRate<-10) or (sapiRate>10): sapiRate = 0
    else:
        __error( f'Неверное значение [{TTS_RHVOICE}, {TTS_SAPI}]','TTSEngine', section )


    ### Terminals
    terminals = dict()
    for section in p.sections :
        if section.lower().startswith("terminal|") :
            id = p.getValue(section,'ID','').strip().lower()
            pwd = p.getValue(section,'Password','')
            if id=='' or pwd=='':
                __error( 'Необходимо задать значения параметров ID и Password')
            terminals[id] = {
                'password': pwd,
                'name': p.getValue(section,'Name',id),
                'location': p.getValue(section,'Location',''),
                'autoupdate': p.getIntValue(section,'AutoUpdate',1)
            }
            if terminals[id]['autoupdate'] not in [0,1,2] :
                __error( 'Неверное значение','AutoUpdate')
    ### Skills
    skills = dict()
    for section in p.sections :
        if section.lower().find("skill|")>0 :
            cfg = p.getRawValues(section)
            cfg['enable'] = bool(p.getValue(section,'Enable','1')!='0')
            skills[section.split('|')[0].lower()] = cfg

    loggerInit( sys.modules[__name__] )

def __error(message:str, parameter:str = '', section:str = ''):
    s = os.path.basename(fileName)
    if str(section)!="" : s = s + str("=>"+section)
    if str(parameter)!="" : s = s + str("=>"+parameter)
    print(f'{s}: {message}')
    fatalError( message )

