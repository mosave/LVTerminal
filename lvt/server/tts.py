from asyncio import Lock
import time
import hashlib
import wave
from numpy import random
from lvt.const import *
from lvt.logger import *
import lvt.server.config as config

ttsLock = Lock()
ttsLocked = set()

rhvoiceWrapper = None

class TTS():
    """TTS Engine
    """

    def __init__( self ):
        global rhvoiceWrapper
        logDebug( f'{config.ttsEngine}: Initializing' )
        self.ttsRHVoice = None
        
        if config.ttsEngine == TTS_RHVOICE :
            try:
                if rhvoiceWrapper is None:
                    import rhvoice_wrapper as rhvoiceWrapper # https://pypi.org/project/rhvoice-wrapper/
                self.ttsRHVoice = rhvoiceWrapper.TTS( 
                    threads = 1,
                    lib_path = self.__rhvp('lib_path'),
                    data_path = self.__rhvp('data_path'),
                    resources = self.__rhvp('resources'),
                    lame_path = self.__rhvp('lame_path'),
                    opus_path = self.__rhvp('opus_path'),
                    flac_path = self.__rhvp('flac_path'),
                    quiet = True,
                    config_path = ""#config.rhvParams['config_path'] if 'config_path' in config.rhvParams else None
                    )
                
            except Exception as e:
                logError( f'Exception initializing RHVoice engine: {e}' )
        elif config.ttsEngine != None:
            logError( f'{config.ttsEngine}: Not yet implemented' )

    def __rhvp(self, parameter: str)->str:
        return config.rhvParams[parameter] if parameter in config.rhvParams else None

    async def textToSpeechAsync( self, text )->bytes:
        """Cached conversion of text to audio
        """
        global ttsLock
        global ttsLocked

        if not config.ttsEngine:
            return

        if isinstance(text, list):
            text = text[random.randint(len(text))]

        logDebug( f'{config.ttsEngine}: "{text}"' )

        voice = None
        wfn = hashlib.sha256((config.ttsEngine+'-'+config.voice+'-'+text).encode()).hexdigest()
        waveFileName = os.path.join( ROOT_DIR,'cache', wfn+'.wav' )

        #todo: rewrite to optimize 
        isLocked = True
        while isLocked:
            await ttsLock.acquire()
            if not (wfn in ttsLocked):
                ttsLocked.add(wfn)
                isLocked = False
            ttsLock.release()
            if isLocked:
                time.sleep(0.1)
        try:
            #print(f'wave file name= {waveFileName}')
            #self.sendMessage( MSG_TEXT, text )
            if not os.path.isfile(waveFileName): 
                logDebug(f'{config.ttsEngine}: Cache not found, generating')
                if (config.ttsEngine == TTS_RHVOICE) and (self.ttsRHVoice != None):
                    rhvParams = config.rhvParams
                    # https://pypi.org/project/rhvoice-wrapper/

                    frames = self.ttsRHVoice.get( text, 
                        voice= rhvParams['voice'],
                        format_='pcm', 
                        sets=rhvParams
                    )
                    # fn = os.path.join( ROOT_DIR, 'logs', datetime.datetime.today().strftime(f'%Y%m%d_%H%M%S_say') )
                    # f = open( fn+'.pcm','wb')
                    # f.write(frames)
                    # f.close()
                    with wave.open( waveFileName, 'wb' ) as wav:
                        sampwidth = wav.setsampwidth(2)
                        nchannels = wav.setnchannels(1)
                        framerate = wav.setframerate(24000)
                        wav.writeframes( frames )

                elif (config.ttsEngine == TTS_SAPI):
                    #https://docs.microsoft.com/en-us/previous-versions/windows/desktop/ms723602(v=vs.85)
                    #pip3 install pywin32
                    # win32 should be imported globally. No other options but tru/except found
                    try:
                        if 'win32com.client' not in sys.modules:
                            import win32com.client
                        if 'pythoncom' not in sys.modules:
                            import pythoncom
                    except:
                        pass
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
                #dt = datetime.datetime.now().ns
                os.utime(waveFileName,)

                with open( waveFileName, 'rb' ) as f:
                    voice = f.read( 5000 * 1024 )
            else:
                logError(f'File {waveFileName} not found')
        except Exception as e:
            logError( f'TTS Engine exception: {e}' )

        await ttsLock.acquire()
        ttsLocked.remove(wfn)
        ttsLock.release()
        return voice

    def cacheRotate(self):
        pass
    def cacheClean(self):
        pass

#endregion

