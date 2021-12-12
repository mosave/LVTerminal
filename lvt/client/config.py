import sys
import time
import os
import pyaudio
from lvt.const import *
from lvt.logger import logError
from lvt.config_parser import ConfigParser

global audio

class Config:
    def initialize( gAudio: pyaudio.PyAudio ):
        global audio
        audio = gAudio

    """LVT Client Configuration"""
    def __init__( self ):
        withConfig = False
        self.configName = 'client.cfg'
        for arg in sys.argv[1:]:
            a = arg.strip().lower()
            if ( a.startswith('-c=') or a.startswith('--config=') ) :
                self.configName = arg.strip().split('=')[1]
                withConfig = True

        if not withConfig:
            ConfigParser.checkConfigFiles( ['client.cfg'])

        p = ConfigParser( self.configName )

        self.serverAddress = p.getValue( '', "serverAddress","" )
        if len( self.serverAddress.strip() ) == 0:
            self.configError( "Не задан адрес сервера","serverAddress" )
        self.serverPort = p.getIntValue( '', "ServerPort", 2700 )
        self.terminalId = p.getValue( '', "TerminalId", '' ).replace( ' ','' ).lower()
        if len( self.terminalId ) <= 0 :
            self.configError( "Не задан ID терминала","TerminalId" )

        self.password = p.getValue( '', "Password",'' ).replace( ' ','' )

        if len( self.password ) <= 0 :
            self.configError( "Не задан пароль","Password" )

        self.ssl = bool( p.getIntValue( '', "UseSSL",0 ) )
        self.sslAllowAny = bool( p.getIntValue( '', "AllowAnyCert",0 ) )
        # audioInput and

        self.logFileName = p.getValue( '', "Log", None )
        self.logLevel = p.getIntValue( '', "LogLevel",20 )
        self.printLevel = p.getIntValue( '', "PrintLevel",20 )

        #Audio output settings
        (self.audioOutputDevice, self.audioOutputName ) = self.getAudioDevice( p.getValue( "", 'AudioOutputDevice', None ), False )

        self.volumeControl = p.getValue("","LVTVolumeControl",None)
        self.volumeControlPlayer = p.getValue("","PlayerVolumeControl",None)
        self.volumeCardIndex = p.getIntValue("", "VolumeCardIndex", 0 )

        # Microphone settings
        (self.audioInputDevice, self.audioInputName) = self.getAudioDevice( p.getValue( "", 'AudioInputDevice', None ), True )

        self.channels = p.getIntValue( '', 'Channels', 1 )
        if self.channels<1 or self.channels>16: 
            self.configError("Неверное количество каналов [1..16]","Channels")

        try:
            allMicrophones = ','.join([str(m) for m in range(0, self.channels)])
            self.microphones = set(map(int, p.getValue( '', 'Microphones', allMicrophones).split(",") ))
        except:
            self.microphones = set(range(0, self.channels) )

        for mic in self.microphones:
            if (mic<0) or (mic>=self.channels):
                self.configError("Неверно указаны индексы микрофонных каналов","Microphones")

        self.micSelection = p.getValue( '', "MicSelection",'avg' ).strip().lower()
        if self.micSelection not in ['avg', 'rms'] : 
            self.configError( f"Неверный метод группировки микрофонных каналов [AVG, RMS]","MicSelection" )

        self.noiseThreshold = p.getIntValue( '', "NoiseThreshold", 200 )
        if self.noiseThreshold<50 or self.noiseThreshold>1000: 
            self.configError("Invalid value [50..1000]","NoiseThreshold")

        self.vadSelectivity = p.getIntValue( '', "VADSelectivity", 3 )
        if self.vadSelectivity<0 or self.vadSelectivity>3: 
            self.configError("Invalid value [0..3]","VADSelectivity")

        self.vadConfidence = p.getIntValue( '', "VADConfidence", 80 )
        if self.vadConfidence<10 or self.vadConfidence>100: 
            self.configError("Invalid value [10..100]","VADConfidence")


           
        self.animator = p.getValue( '', "Animator",'text' ).strip().lower()
        if self.animator not in ['apa102','text'] : 
            self.configError( "Invalid value [text, apa102]","Animator" )
        if self.animator=='apa102' :
            n = p.getIntValue('','APA102LEDCount',3)
            self.apa102LedCount = 1 if n<1 else 127 if n>127 else n
            self.apa102MuteLeds = set()
            leds = p.getValue( '', "APA102MuteLEDs",'0' ).strip().split(',')
            for s in leds :
                try: n = int(s)
                except: n=-1
                if (n>=0) and (n<self.apa102LedCount) : 
                    self.apa102MuteLeds.add(n)


    def getAudioDevice( self, deviceIndex, isInput:bool ):
        global audio 
        # Use default device if not specified
        if deviceIndex == None :
            try:
                if isInput :
                    deviceIndex = audio.get_default_input_device_info().get( 'index' )
                else:
                    deviceIndex = audio.get_default_output_device_info().get( 'index' )
            except:
                deviceIndex = None

        if deviceIndex == None : return(None, None)

        # Extract device index if possible
        try: deviceIndex = int( deviceIndex )
        except: deviceIndex = str( deviceIndex )

        # Resolve audio input & output devices over the list of devices
        # available
        deviceName = None
        for i in range( audio.get_device_count() ):
            #print(audio.get_device_info_by_index( i ))
            name = audio.get_device_info_by_index( i ).get( "name" )
            # Resolve index by device name
            if ( type( deviceIndex ) is str ) and name.lower().startswith( deviceIndex.lower() ) : deviceIndex = i
            # Assign original device name
            if ( type( deviceIndex ) is int ) and ( deviceIndex == i ) : 
                deviceName = name
                break

        # check if device was resolved
        if deviceIndex != None and deviceName == None : 
            self.configError( 'Invalid Device Name', f'Audio{("input" if isInput else "Output")}Device' )
        return (deviceIndex, deviceName)

    def configError(self, message:str, parameter:str = None):
        print(f'{os.path.basename(self.configName)}{("=>"+parameter if str(parameter)!="" else "")}: {message}')
        logError( message )
        quit(1);

