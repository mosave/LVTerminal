import sys
import time
import os
import pyaudio
from lvt.const import *
from lvt.config_parser import ConfigParser

class Config:
    """LVT Client Configuration"""
    def __init__( this, fileName ):
        p = ConfigParser( os.path.join( ROOT_DIR, fileName ) )

        this.serverAddress = p.getValue( '', "serverAddress","" )
        if len( this.serverAddress.strip() ) == 0:
            raise Exception( "Light Voice Terminal Server address was not specified" )
        this.serverPort = p.getIntValue( '', "ServerPort", 2700 )
        this.terminalId = p.getValue( '', "TerminalId", '' ).replace( ' ','' )
        if len( this.terminalId ) <= 0 :
            raise Exception( "TerminalId should be specified" )

        this.password = p.getValue( '', "Password",'' ).replace( ' ','' )

        if len( this.password ) <= 0 :
            raise Exception( "TerminalId should be specified" )

        this.ssl = bool( p.getIntValue( '', "UseSSL",0 ) )
        this.sslAllowAny = bool( p.getIntValue( '', "AllowAnyCert",0 ) )
        # audioInput and
        (this.audioInputDevice, this.audioInputName) = this.getAudioDevice( p.getValue( "", 'AudioInputDevice', None ) )
        (this.audioOutputDevice, this.audioOutputName) = this.getAudioDevice( p.getValue( "", 'AudioOutputDevice', None ) )
        this.noiseThreshold = p.getIntValue( '', "NoiseThreshold", 200 )
        this.sampleRate = p.getIntValue( '', 'SampleRate', 8000 )

    def getAudioDevice( this, deviceIndex ):
        # Use default device if not specified
        if deviceIndex == None : return (None, None)
        # Extract device index if possible
        try: 
            deviceIndex = int( deviceIndex )
        except: pass

        # Resolve audio input & output devices over the list of devices
        # available
        deviceName = None
        audio = pyaudio.PyAudio()
        for i in range( audio.get_device_count() ):
            name = audio.get_device_info_by_index( i ).get( "name" )
            # Resolve index by device name
            if ( type( deviceIndex ) is str ) and name.lower().startswith( deviceIndex.lower() ) : deviceIndex = i
            # Assign original device name
            if ( type( deviceIndex ) is int ) and ( deviceIndex == i ) : deviceName = name
        audio.terminate()

        # check if device was resolved
        if deviceName == None : raise Exception( f'Invalid {keyName} specified' )
        return (deviceIndex, deviceName)



