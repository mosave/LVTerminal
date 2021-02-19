import sys
import time
import os
import pyaudio
from lvt.const import *
from lvt.config_parser import ConfigParser
from lvt.alsa_supressor import AlsaSupressor

class Config:
    """LVT Client Configuration"""
    def __init__( this ):
        AlsaSupressor.disableWarnings()

        ConfigParser.checkConfigFiles( ['client.cfg'])

        p = ConfigParser( 'client.cfg' )

        this.serverAddress = p.getValue( '', "serverAddress","" )
        if len( this.serverAddress.strip() ) == 0:
            raise Exception( "Lite Voice Terminal Server address was not specified" )
        this.serverPort = p.getIntValue( '', "ServerPort", 2700 )
        this.terminalId = p.getValue( '', "TerminalId", '' ).replace( ' ','' ).lower()
        if len( this.terminalId ) <= 0 :
            raise Exception( "TerminalId should be specified" )

        this.password = p.getValue( '', "Password",'' ).replace( ' ','' )

        if len( this.password ) <= 0 :
            raise Exception( "TerminalId should be specified" )

        this.ssl = bool( p.getIntValue( '', "UseSSL",0 ) )
        this.sslAllowAny = bool( p.getIntValue( '', "AllowAnyCert",0 ) )
        # audioInput and

        this.logFileName = p.getValue( '', "Log", None )
        this.logLevel = p.getIntValue( '', "LogLevel",20 )
        this.printLevel = p.getIntValue( '', "PrintLevel",20 )

        (this.audioInputDevice, this.audioInputName) = this.getAudioDevice( p.getValue( "", 'AudioInputDevice', None ), True )
        (this.audioOutputDevice, this.audioOutputName) = this.getAudioDevice( p.getValue( "", 'AudioOutputDevice', None ), False )
        this.noiseThreshold = p.getIntValue( '', "NoiseThreshold", 200 )
        if this.noiseThreshold<50 or this.noiseThreshold>1000: raise Exception("Invalid NoiseThreshold specified")

        this.vadSelectivity = p.getIntValue( '', "VADSelectivity", 3 )
        if this.vadSelectivity<0 or this.vadSelectivity>3: raise Exception("Invalid VADSelectivity specified")

        this.vadConfidence = p.getIntValue( '', "VADConfidence", 80 )
        if this.vadConfidence<10 or this.vadConfidence>100: raise Exception("Invalid VADConfidence specified")

        this.sampleRate = p.getIntValue( '', 'SampleRate', 8000 )
        if this.sampleRate not in [8000,16000]: raise Exception("Invalid SampleRate specified")

        this.channelSelection = p.getValue( '', "ChannelSelection",'0' ).strip().lower()
        try: this.channelSelection = int(this.channelSelection)
        except:pass

        if isinstance(this.channelSelection, int) and (this.channelSelection<0 or this.channelSelection>15) or \
           isinstance(this.channelSelection, str) and this.channelSelection not in ['rms'] : 
            raise Exception( "Invalid ChannelSelection value specified" )
           
        this.animator = p.getValue( '', "Animator",'text' ).strip().lower()
        if this.animator not in ['apa102','text'] : raise Exception( "Invalid Animator specified" )
        if this.animator=='apa102' :
            n = p.getIntValue('','APA102LEDCount',3)
            this.apa102LedCount = 1 if n<1 else 127 if n>127 else n
            this.apa102MuteLeds = set()
            leds = p.getValue( '', "APA102MuteLEDs",'0' ).strip().split(',')
            for s in leds :
                try: n = int(s)
                except: n=-1
                if (n>=0) and (n<this.apa102LedCount) : 
                    this.apa102MuteLeds.add(n)



    def getAudioDevice( this, deviceIndex, isInput:bool ):
        audio = pyaudio.PyAudio()
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
            name = audio.get_device_info_by_index( i ).get( "name" )
            # Resolve index by device name
            if ( type( deviceIndex ) is str ) and name.lower().startswith( deviceIndex.lower() ) : deviceIndex = i
            # Assign original device name
            if ( type( deviceIndex ) is int ) and ( deviceIndex == i ) : 
                deviceName = name
                break

        audio.terminate()
        # check if device was resolved
        if deviceIndex != None and deviceName == None : 
            raise Exception( f'Invalid Audio{("input" if isInput else "Output")}Device specified' )
        return (deviceIndex, deviceName)



