import sys
import time
import os
import getopt
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
    def __init__( this ):
        configName = "server.cfg"
        for arg in sys.argv[1:]:
            a = arg.strip().lower()
            if ( a.startswith('--config=') ) :
                configName = a.split('=')[1]


        ConfigParser.checkConfigFiles( [
            'server.cfg',
            'acronyms', 'locations', 'vocabulary', 'devices', 'persons'
            ])
        p = ConfigParser( configName )
        section = 'LVTServer'
        ### Network configuration
        this.serverAddress = p.getValue( section, 'ServerAddress','0.0.0.0' )
        this.serverPort = p.getIntValue( section, 'ServerPort',2700 )
        this.apiServerPort = p.getIntValue( section, 'APIServerPort', 7999 )
        this.sslCertFile = p.getValue( section, 'SSLCertFile','' )
        this.sslKeyFile = p.getValue( section, 'SSLKeyFile','' )

        ### Voice recognition configuration 
        this.model = p.getValue( section, 'Model','' ).strip()
        this.fullModel = p.getValue( section, 'FullModel','' ).strip()
        if this.model=='' and this.fullModel== '':
            raise Exception( 'No models specified' )

        this.sampleRate = p.getIntValue( section, 'SampleRate',8000 )
        if this.sampleRate not in [8000,16000]: raise Exception("Invalid SampleRate specified")

        this.storeAudio = bool(p.getValue(section,'StoreAudio','0') != '0')

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
            this.rhvDataPath = p.getValue( section, 'data_path', None )
            this.rhvConfigPath = p.getValue( section, 'config_path', None )

            this.rhvParamsMale = this.loadRHVoiceParams( "RHVoiceMale", p )
            this.rhvParamsFemale = this.loadRHVoiceParams( "RHVoiceFemale", p )

            if this.rhvParamsMale == None and this.rhvParamsFemale == None :
                raise Exception('В конфигурации обязательно должна быть определена хотя бы одна из секций [RHVoiceMale] или [RHVoiceFemale]') 
        elif( this.ttsEngine.lower().strip() == TTS_SAPI.lower() ):
            this.ttsEngine = TTS_SAPI
            section = TTS_SAPI
            this.sapiMaleVoice = p.getValue( section, 'MaleVoice', None )
            this.sapiFemaleVoice = p.getValue( section, 'FemaleVoice', None )
            if not this.sapiMaleVoice : this.sapiMaleVoice = this.sapiFemaleVoice
            if not this.sapiFemaleVoice : this.sapiFemaleVoice = this.sapiMaleVoice
            this.sapiMaleRate = p.getIntValue( section, "MaleRate", 0 )
            this.sapiFemaleRate = p.getIntValue( section, "FemaleRate", 0 )
            if (this.sapiMaleRate<-10) or (this.sapiMaleRate>10):
                this.sapiMaleRate = 0
            if (this.sapiFemaleRate<-10) or (this.sapiFemaleRate>10):
                this.sapiFemaleRate = 0
        else:
            raise Exception( 'Неверное значение параметра TTSEngine' )

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
                id = p.getValue(section,'ID','').strip().lower()
                pwd = p.getValue(section,'Password','')
                if id=='' or pwd=='':
                    raise Exception( 'Необходимо задать значения параметров ID и Password')
                this.terminals[id] = {
                    'password': pwd,
                    'name': p.getValue(section,'Name',id),
                    'location': p.getValue(section,'Location',''),
                    'autoupdate': p.getIntValue(section,'AutoUpdate',1)
                }
                if this.terminals[id]['autoupdate'] not in [0,1,2] :
                    raise Exception( 'Неверное значение параметра "AutoUpdate"')
        ### Skills
        this.skills = dict()
        for section in p.sections :
            if section.lower().find("skill|")>0 :
                cfg = p.getRawValues(section)
                cfg['enable'] = bool(p.getValue(section,'Enable','1')!='0')
                this.skills[section.split('|')[0].lower()] = cfg

    def loadRHVoiceParams( this, section: str, p: ConfigParser ) :
        rhvParams = p.getValues( section )
        if( rhvParams != None ):
            for key in rhvParams: 
                try: 
                    rhvParams[key] = int( rhvParams[key] )
                except:
                    try:
                        rhvParams[key] = float( rhvParams[key] )
                    except:
                        pass
            if 'voice' not in rhvParams or str(rhvParams['voice']).strip()=='':
                raise Exception(f'Не определен параметр Voice="" в секции {section}')
        return rhvParams

#endregion

       

