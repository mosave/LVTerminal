import sys
import time
import os
import getopt
from lvt.const import *
from lvt.logger import logError
from lvt.server.grammar import *
from lvt.config_parser import ConfigParser

class Config:
    """LVT Server configuration.
      * terminals: list of terminal configuration sections to be used in Terminal
      * rhv* properties are defined if RHV voice engine specified only
    """

### __init__  ##########################################################################
#region
    def __init__( self ):
        withConfig = False
        self.configName = "server.cfg"
        for arg in sys.argv[1:]:
            a = arg.strip().lower()
            if ( a.startswith('-c=') or a.startswith('--config=') ) :
                self.configName = a.split('=')[1]
                withConfig = True

        if not withConfig:
            ConfigParser.checkConfigFiles( [
                'server.cfg',
                'acronyms', 'locations', 'vocabulary', 'devices', 'persons'
                ])
        p = ConfigParser( self.configName )
        section = 'LVTServer'
        ### Network configuration
        self.serverAddress = p.getValue( section, 'ServerAddress','0.0.0.0' )
        self.serverPort = p.getIntValue( section, 'ServerPort',2700 )
        self.apiServerPort = p.getIntValue( section, 'APIServerPort', 7999 )
        self.sslCertFile = p.getValue( section, 'SSLCertFile','' )
        self.sslKeyFile = p.getValue( section, 'SSLKeyFile','' )

        ### Voice recognition configuration 
        self.model = p.getValue( section, 'Model','' ).strip()
        self.fullModel = p.getValue( section, 'FullModel','' ).strip()
        if self.model=='' and self.fullModel== '':
            self.error( 'No models specified' )

        self.storeAudio = bool(p.getValue(section,'StoreAudio','0') != '0')

        self.recognitionThreads = p.getIntValue( section, 'RecognitionThreads',os.cpu_count() )
        if( self.recognitionThreads < 1 ): self.recognitionThreads = 1

        self.vocabularyMode = bool(p.getIntValue( section, 'VocabularyMode', 1 ))
        if self.model=='' : self.vocabularyMode = False

        self.language = p.getValue( section, 'Language','ru' )
        if self.language not in {'ru','uk','en' } : self.language = 'ru'

        ### Speaker identification config
        self.spkModel = p.getValue( section, 'SpkModel','' ).strip()
        self.voiceSimilarity = p.getFloatValue( section, 'VoiceSimilarity', 0.6 )
        self.voiceSelectivity = p.getFloatValue( section, 'VoiceSelectivity', 0.2 )

        ### Assistant configuration
        self.maleAssistantNames = normalizeWords(p.getValue( section, 'MaleAssistantNames','' ))
        self.femaleAssistantNames = normalizeWords(p.getValue( section, 'FemaleAssistantNames','' ))

          
        if( len( wordsToList( self.maleAssistantNames + ' ' + self.femaleAssistantNames) ) == 0 ): 
            self.error( 'Either MaleAssistantNames or FemaleAssistantNames should be specified' )

        ### Logging
        self.logFileName = p.getValue( section, "Log", None )
        self.logLevel = p.getIntValue( section, "LogLevel",20 )
        self.printLevel = p.getIntValue( section, "PrintLevel",20 )

        ### TTS Engine
        self.ttsEngine = p.getValue( section, 'TTSEngine', '' )

        if str( self.ttsEngine ) == '':
            pass
        elif( self.ttsEngine.lower().strip() == TTS_RHVOICE.lower() ):
            self.ttsEngine = TTS_RHVOICE

            section = TTS_RHVOICE
            self.rhvDataPath = p.getValue( section, 'data_path', None )
            self.rhvConfigPath = p.getValue( section, 'config_path', None )

            self.rhvParamsMale = self.loadRHVoiceParams( "RHVoiceMale", p )
            self.rhvParamsFemale = self.loadRHVoiceParams( "RHVoiceFemale", p )

            if self.rhvParamsMale == None and self.rhvParamsFemale == None :
                self.error('В конфигурации обязательно должна быть определена хотя бы одна из секций [RHVoiceMale] или [RHVoiceFemale]') 
        elif( self.ttsEngine.lower().strip() == TTS_SAPI.lower() ):
            self.ttsEngine = TTS_SAPI
            section = TTS_SAPI
            self.sapiMaleVoice = p.getValue( section, 'MaleVoice', None )
            self.sapiFemaleVoice = p.getValue( section, 'FemaleVoice', None )
            if not self.sapiMaleVoice : self.sapiMaleVoice = self.sapiFemaleVoice
            if not self.sapiFemaleVoice : self.sapiFemaleVoice = self.sapiMaleVoice
            self.sapiMaleRate = p.getIntValue( section, "MaleRate", 0 )
            self.sapiFemaleRate = p.getIntValue( section, "FemaleRate", 0 )
            if (self.sapiMaleRate<-10) or (self.sapiMaleRate>10):
                self.sapiMaleRate = 0
            if (self.sapiFemaleRate<-10) or (self.sapiFemaleRate>10):
                self.sapiFemaleRate = 0
        else:
            self.error( 'Неверное значение','TTSEngine' )

        ### Terminals
        self.terminals = dict()
        for section in p.sections :
            if section.lower().startswith("terminal|") :
                id = p.getValue(section,'ID','').strip().lower()
                pwd = p.getValue(section,'Password','')
                if id=='' or pwd=='':
                    self.error( 'Необходимо задать значения параметров ID и Password')
                self.terminals[id] = {
                    'password': pwd,
                    'name': p.getValue(section,'Name',id),
                    'location': p.getValue(section,'Location',''),
                    'autoupdate': p.getIntValue(section,'AutoUpdate',1)
                }
                if self.terminals[id]['autoupdate'] not in [0,1,2] :
                    self.error( 'Неверное значение','AutoUpdate')
        ### Skills
        self.skills = dict()
        for section in p.sections :
            if section.lower().find("skill|")>0 :
                cfg = p.getRawValues(section)
                cfg['enable'] = bool(p.getValue(section,'Enable','1')!='0')
                self.skills[section.split('|')[0].lower()] = cfg

    def loadRHVoiceParams( self, section: str, p: ConfigParser ) :
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
                self.error(f'Не определено', 'Voice', section )
        return rhvParams

    def error(self, message:str, parameter:str = None, section:str = None):
        s = os.path.basename(self.configName)
        if str(section)!="" : s = s + "=>"+section
        if str(parameter)!="" : s = s + "=>"+parameter
        print(f'{s}: {message}')
        logError( message )
        quit(1);

#endregion

       

