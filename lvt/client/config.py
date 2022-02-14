import sys
import time
import os
import pyaudio
from lvt.const import *
from lvt.logger import *
from lvt.config_parser import ConfigParser

fileName = 'client.cfg'
serverAddress : str = ''
serverPort : int = 2700

terminalId : str = ''
password : str = ''

ssl = False
sslAllowAny = True

logFileName = os.path.join( ROOT_DIR, "logs", "client.log")
logLevel = 20
printLevel = 20

audioOutputDevice = None
audioOutputName = None

audioInputDevice = None
audioInputName = None

volumeCardIndex = 0
volumeControl = None
volumeControlPlayer = None

lmsAddress = None
lmsPort = 9000
lmsUser = None
lmsPassword = None
lmsPlayer = None
lmsMode = LMS_MODE_PAUSE

channels = 1
microphones = [1]
micSelection = 'avg'

noiseThreshold = 200
vadSelectivity = 3
vadConfidence = 80

animator = 'text'
apa102LedCount = 3
apa102MuteLeds = [0]

def init( audio: pyaudio.PyAudio ):
    global fileName
    global serverAddress
    global serverPort
    global terminalId
    global password
    global ssl
    global sslAllowAny
    global logFileName
    global logLevel
    global printLevel
    global audioOutputDevice
    global audioOutputName
    global audioInputDevice 
    global audioInputName

    global volumeCardIndex
    global volumeControl
    global volumeControlPlayer

    global lmsAddress
    global lmsPort
    global lmsUser
    global lmsPassword
    global lmsPlayer
    global lmsMode

    global channels
    global microphones
    global noiseThreshold
    global vadSelectivity
    global vadConfidence
    global animator
    global apa102LedCount
    global apa102MuteLeds

    withConfig = False

    fileName = 'client.cfg'
    fileName = 'client.cfg'
    for arg in sys.argv[1:]:
        a = arg.strip().lower()
        if ( a.startswith('-c=') or a.startswith('--config=') ) :
            fileName = arg.strip().split('=')[1]
            withConfig = True

    if not withConfig:
        ConfigParser.checkConfigFiles( ['client.cfg'])

    p = ConfigParser( fileName )

    serverAddress = p.getValue( '', "serverAddress","" )
    if not bool( serverAddress.strip() ):
        __error( "Не задан адрес сервера","serverAddress" )
    serverPort = p.getIntValue( '', "ServerPort", 2700 )
    terminalId = p.getValue( '', "TerminalId", '' ).replace( ' ','' ).lower()
    if not bool( terminalId ):
        __error( "Не задан ID терминала","TerminalId" )

    password = p.getValue( '', "Password",'' ).replace( ' ','' )

    if not bool( password ) :
        __error( "Не задан пароль","Password" )

    ssl = bool( p.getIntValue( '', "UseSSL",0 ) )
    sslAllowAny = bool( p.getIntValue( '', "AllowAnyCert",0 ) )
    # audioInput and

    logFileName = p.getValue( '', "Log", None )
    if not bool(logFileName): logFileName = "client.log"
    if os.path.dirname(logFileName) == '':
        logFileName = os.path.join( ROOT_DIR, "logs", logFileName)

    logLevel = p.getIntValue( '', "LogLevel", None )
    printLevel = p.getIntValue( '', "PrintLevel", None )

    #Audio output settings
    (audioOutputDevice, audioOutputName ) = __getAudioDevice( audio, p.getValue( "", 'AudioOutputDevice', None ), False )

    volumeControl = p.getValue("","VolumeControl",None)
    volumeControlPlayer = p.getValue("","PlayerVolumeControl",None)
    volumeCardIndex = p.getIntValue("", "VolumeCardIndex", 0 )

    lmsAddress = p.getValue("","LMSAddress", None)
    lmsPort = p.getIntValue("","LMSPort", 9000)
    lmsUser = p.getValue("","LMSUser", None)
    lmsPassword = p.getValue("","LMSPassword", None)
    lmsPlayer = p.getValue("","LMSPlayer", terminalId )

    s = p.getValue( "", "LMSMode", 'mute' ).lower()
    if s=='mute':
        lmsMode = LMS_MODE_MUTE
    elif s=='pause':
        lmsMode = LMS_MODE_PAUSE
    else:
        __error( f'Неверный режим интеграции LMS. Допустимые значения "Volume" и "Pause"','LMSMode', "" )



    # Microphone settings
    (audioInputDevice, audioInputName) = __getAudioDevice( audio, p.getValue( "", 'AudioInputDevice', None ), True )

    channels = p.getIntValue( '', 'Channels', 1 )
    if channels<1 or channels>16: 
        __error("Неверное количество каналов [1..16]","Channels")

    try:
        allMicrophones = ','.join([str(m) for m in range(0, channels)])
        microphones = set(map(int, p.getValue( '', 'Microphones', allMicrophones).split(",") ))
    except:
        microphones = set(range(0, channels) )

    for mic in microphones:
        if (mic<0) or (mic>=channels):
            __error("Неверно указаны индексы микрофонных каналов","Microphones")

    micSelection = p.getValue( '', "MicSelection",'avg' ).strip().lower()
    if micSelection not in ['avg', 'rms'] : 
        __error( f"Неверный метод группировки микрофонных каналов [AVG, RMS]","MicSelection" )

    noiseThreshold = p.getIntValue( '', "NoiseThreshold", 200 )
    if noiseThreshold<50 or noiseThreshold>1000: 
        __error("Неверное пороговое значение уровня шума [50..1000]","NoiseThreshold")

    vadSelectivity = p.getIntValue( '', "VADSelectivity", 3 )
    if vadSelectivity<0 or vadSelectivity>3: 
        __error("Неверное значение избирательности детектора голоса [0..3]","VADSelectivity")

    vadConfidence = p.getIntValue( '', "VADConfidence", 80 )
    if vadConfidence<10 or vadConfidence>100: 
        __error("Неверное значение коэффициента надежности детектора голоса [10..100]","VADConfidence")


           
    animator = p.getValue( '', "Animator",'text' ).strip().lower()
    if animator not in ['apa102','text'] : 
        __error( "Недопустимый тип аниматора [text, apa102]","Animator" )
    if animator=='apa102' :
        n = p.getIntValue('','APA102LEDCount',3)
        apa102LedCount = 1 if n<1 else 127 if n>127 else n
        apa102MuteLeds = set()
        leds = p.getValue( '', "APA102MuteLEDs",'0' ).strip().split(',')
        for s in leds :
            try: n = int(s)
            except: n=-1
            if (n>=0) and (n<apa102LedCount) : 
                apa102MuteLeds.add(n)

    loggerInit( sys.modules[__name__] )

def __getAudioDevice( audio: pyaudio.PyAudio, deviceIndex, isInput:bool ):
    parameter = f'Audio{("input" if isInput else "Output")}Device'
    # Use default device if not specified
    if deviceIndex == None :
        try:
            if isInput :
                a = audio.get_default_input_device_info()
                deviceIndex = audio.get_default_input_device_info().get( 'index' )
            else:
                deviceIndex = audio.get_default_output_device_info().get( 'index' )
        except:
            deviceIndex = 0

    if deviceIndex == None : 
        __error( 'Неверное имя или индекс аудиоустройтсва', parameter )
        return(None, None)

    # Extract device index if possible
    try: deviceIndex = int( deviceIndex )
    except: deviceIndex = str( deviceIndex )

    # Resolve audio input & output devices over the list of devices
    # available
    deviceName = None
    device = 0
    for i in range( audio.get_device_count() ):
        #print(audio.get_device_info_by_index( i ))
        device = audio.get_device_info_by_index( i )
        name = str(device.get( "name" ))
        # Resolve index by device name
        if isinstance( deviceIndex, str ) and name.lower().startswith( deviceIndex.lower() ) : deviceIndex = i
        # Assign original device name
        if isinstance( deviceIndex,int ) and ( deviceIndex == i ) :
            deviceName = name
            break

    # check if device was resolved
    if deviceIndex == None or deviceName == None : 
        __error( 'Неверное имя или индекс аудиоустройтсва', parameter )

    channels = device.get('maxInputChannels') if isInput else device.get('maxOutputChannels')
    if channels <=0 : 
        __error( f'Устройство не имеет {"аудиовходов" if isInput else "аудиовыходов"}', parameter )

    return (deviceIndex, deviceName)

def __error( message:str, parameter:str = '' ):
    global fileName
    p = "=>"+parameter if parameter!='' else ''
    print(f'{os.path.basename(fileName)}{p}: {message}')
    logError( message )
    quit(1)

