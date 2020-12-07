import sys
import time
import os
import psutil
from lvt.const import *
from lvt.config_parser import ConfigParser

class Config:
    """LVT Server configuration.
      * terminals: list of terminal configuration sections to be used in Terminal
      * rhv* properties are defined if RHV voice engine specified only
    """
    def __init__( this, fileName ):
        p = ConfigParser( fileName )
        section = 'LVTServer'
        this.serverAddress = p.getValue( section, 'ServerAddress','0.0.0.0' )
        this.serverPort = p.getIntValue( section, 'ServerPort',2700 )
        this.sslCertFile = p.getValue( section, 'SSLCertFile','' )
        this.sslKeyFile = p.getValue( section, 'SSLKeyFile','' )
        this.model = p.getValue( section, 'Model','' ).strip()
        this.fullModel = p.getValue( section, 'FullModel','' ).strip()
        if this.model=='' and this.fullModel== '':
            raise Exception( 'No models specified' )

        this.spkModel = p.getValue( section, 'SpkModel','' ).strip()
        this.sampleRate = p.getIntValue( section, 'SampleRate',8000 )
        this.recognitionThreads = p.getIntValue( section, 'RecognitionThreads',os.cpu_count() )
        if( this.recognitionThreads < 1 ): this.recognitionThreads = 1

        this.voiceSimilarity = p.getFloatValue( section, 'VoiceSimilarity', 0.6 )
        this.voiceSelectivity = p.getFloatValue( section, 'VoiceSelectivity', 0.2 )

        this.assistantName = p.getValue( section, 'AssistantName','' ) \
            .replace( ',',' ' ).replace( '  ',' ' ).strip().lower()
        if( len( this.assistantName.strip() ) == 0 ): 
            raise Exception( 'AssistantName should be specified' )

        this.language = p.getValue( section, 'Language','ru' )
        if this.language not in {'ru','uk','en' } : this.language = 'ru'

        this.confirmationPhrases = p.getValue( section, 'ConfirmationPhrases','да, хорошо, согласен, да будет так' ) \
            .lower().replace( '  ',' ' ).replace( ', ',',' )

        this.cancellationPhrases = p.getValue( section, 'CancellationPhrases','нет, отмена, стоп, стой' ) \
            .lower().replace( '  ',' ' ).replace( ', ',',' )

        # TTS Engine
        this.ttsEngine = p.getValue( section, 'TTSEngine', '' )

        if str( this.ttsEngine ) == '':
            pass
        elif( this.ttsEngine.lower().strip() == TTS_RHVOICE.lower() ):
            this.ttsEngine = TTS_RHVOICE
            section = TTS_RHVOICE
            this.rhvVoice = p.getValue( section, 'Voice', 'Anna+CLB' )
            this.rhvDataPath = p.getValue( section, 'data_path', None )
            this.rhvConfigPath = p.getValue( section, 'config_path', None )
            this.rhvParams = p.getValues( section )
            if( this.rhvParams != None ):
                for key in this.rhvParams: 
                    try: 
                        this.rhvParams[key] = int( this.rhvParams[key] )
                    except:
                        try:
                            this.rhvParams[key] = float( this.rhvParams[key] )
                        except:
                            pass
        else:
            raise Exception( 'Invalid voice engine specified' )


    def getJson( this, terminals=None ):
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

        js = '{'
        js += f'"Model":"{this.model}",'
        js += f'"FullModel":"{this.fullModel}",'
        js += f'"SpkModel":"{this.spkModel}",'
        js += f'"SampleRate":"{this.sampleRate}",'
        js += f'"RecognitionThreads":"{this.recognitionThreads}",'
        js += f'"AssistantName":"{this.assistantName}",'
        js += f'"VoiceEngine":"{this.ttsEngine}",'
        if terminals != None :
            activeTerminals = 0
            for t in terminals: activeTerminals+= 1 if t.isActive else 0
            js += f'"TotalTerminals":"{len(this.terminals)}",'
            js += f'"ActiveTerminals":"{activeTerminals}",'
        js += f'"CpuCores":"{os.cpu_count()}",'
        js += f'"CpuFreq":"{cpufreq.current:.2f}Mhz",'
        js += f'"CpuLoad":"{psutil.cpu_percent()}%",'
        js += f'"MemTotal":"{formatSize(svmem.total)}",'
        js += f'"MemAvail":"{formatSize(svmem.available)}",'
        js += f'"MemUsed":"{formatSize(svmem.used)}",'
        js += f'"MemLoad":"{svmem.percent}%"' + '}'
        return js
       

