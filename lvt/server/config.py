import sys
import time
import os
import psutil
from lvt.const import *
from lvt.server.grammar import *
from lvt.config_parser import ConfigParser

class Config:
    """LVT Server configuration.
      * terminals: list of terminal configuration sections to be used in Terminal
      * rhv* properties are defined if RHV voice engine specified only
    """

### __init__  ##########################################################################
#region
    def __init__( this, fileName ):
        p = ConfigParser( fileName )
        section = 'LVTServer'
        ### Network configuration
        this.serverAddress = p.getValue( section, 'ServerAddress','0.0.0.0' )
        this.serverPort = p.getIntValue( section, 'ServerPort',2700 )
        this.sslCertFile = p.getValue( section, 'SSLCertFile','' )
        this.sslKeyFile = p.getValue( section, 'SSLKeyFile','' )

        ### Voice recognition configuration 
        this.model = p.getValue( section, 'Model','' ).strip()
        this.fullModel = p.getValue( section, 'FullModel','' ).strip()
        if this.model=='' and this.fullModel== '':
            raise Exception( 'No models specified' )

        this.sampleRate = p.getIntValue( section, 'SampleRate',8000 )
        if this.sampleRate not in [8000,16000]: raise Exception("Invalid SampleRate specified")

        this.recognitionThreads = p.getIntValue( section, 'RecognitionThreads',os.cpu_count() )
        if( this.recognitionThreads < 1 ): this.recognitionThreads = 1

        this.vocabularyMode = bool(p.getIntValue( section, 'VocabularyMode', 1 ))
        if this.model=='' : this.vocabularyMode = False

        this.language = p.getValue( section, 'Language','ru' )
        if this.language not in {'ru','uk','en' } : this.language = 'ru'

        ### Speaker identification config
        this.spkModel = p.getValue( section, 'SpkModel','' ).strip()
        this.voiceSimilarity = p.getFloatValue( section, 'VoiceSimilarity', 0.6 )
        this.voiceSelectivity = p.getFloatValue( section, 'VoiceSelectivity', 0.2 )

        ### Assistant configuration
        this.maleAssistantNames = normalizeWords(p.getValue( section, 'MaleAssistantNames','' ))
        this.femaleAssistantNames = normalizeWords(p.getValue( section, 'FemaleAssistantNames','' ))

          
        if( len( wordsToList( this.maleAssistantNames + ' ' + this.femaleAssistantNames) ) == 0 ): 
            raise Exception( 'Either MaleAssistantNames or FemaleAssistantNames should be specified' )

        ### Logging
        this.logFileName = p.getValue( section, "Log", None )
        this.logLevel = p.getIntValue( section, "LogLevel",20 )
        this.printLevel = p.getIntValue( section, "PrintLevel",20 )

        ### TTS Engine
        this.ttsEngine = p.getValue( section, 'TTSEngine', '' )

        if str( this.ttsEngine ) == '':
            pass
        elif( this.ttsEngine.lower().strip() == TTS_RHVOICE.lower() ):
            this.ttsEngine = TTS_RHVOICE
            section = TTS_RHVOICE
            this.rhvMaleVoice = p.getValue( section, 'MaleVoice', 'Aleksandr+Alan' )
            this.rhvFemaleVoice = p.getValue( section, 'FemaleVoice', 'Anna+CLB' )
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

        ### MQTT client
        section = 'MQTT'
        this.mqttServer = p.getValue( section, 'Server','' )

        ### MajorDoMo
        section = 'MajorDoMo'
        this.mdUser = p.getValue( section, 'User','' )
        this.mdPassword = p.getValue( section, 'Password','' )
        this.mdServer = p.getValue( section, 'Server','' )
        #if this.mdServer!='' :
        #    this.mdServer = os.environ.get("BASE_URL", this.mdServer )
        this.mdIntegration = bool(p.getValue( section, 'Integration','0' )=='1')
        this.mdSendRawCommands = bool(p.getValue( section, 'SendRawCommands','0' )=='1')


        ### Terminals
        this.terminals = dict()
        for section in p.sections :
            if section.lower().startswith("terminal|") :
                id = p.getValue(section,'ID','')
                pwd = p.getValue(section,'Password','')
                if id=='' or pwd=='':
                    raise Exception( 'Terminal ID and Password are mandatory')
                this.terminals[id] = {
                    'password': pwd,
                    'name': p.getValue(section,'Name',id),
                    'location': p.getValue(section,'Location',''),
                    'autoupdate': bool(p.getValue(section,'AutoUpdate','0') != '0')
                }
        ### Skills
        this.skills = dict()
        for section in p.sections :
            if section.lower().find("skill|")>0 :
                cfg = p.getRawValues(section)
                cfg['enable'] = bool(p.getValue(section,'Enable','1')!='0')
                this.skills[section.split('|')[0].lower()] = cfg


#endregion

### getJson() ##########################################################################
#region
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
        s = normalizeWords(this.femaleAssistantNames + this.maleAssistantNames )
        js += f'"AssistantNames":"{s}",'
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
#endregion
       

