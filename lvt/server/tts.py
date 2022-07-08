from asyncio import Lock
import asyncio
import hashlib
import wave
import re
from numpy import random
from lvt.const import *
from lvt.logger import *
import lvt.server.config as config
from lvt.server.grammar import *


ttsLock = Lock()
ttsLocked = set()
rhvoiceWrapper = None


class TTS():
    """TTS Engine
    """

    def __init__( self ):
        global rhvoiceWrapper
        self.ttsRHVoice = None
        
        if config.ttsEngine == TTS_RHVOICE :
            if rhvoiceWrapper is None :
                try:
                    import rhvoice_wrapper as rhvoiceWrapper # https://pypi.org/project/rhvoice-wrapper/
                except Exception as e:
                    logError( f'{type(e).__name__} importing RHVoice wrapper: {e}' )
            pass
        elif config.ttsEngine is not None:
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

        speech = None
        wfn = hashlib.sha256((config.ttsEngine+'-'+config.voice+'-'+text).encode()).hexdigest()
        waveFileName = os.path.join( ROOT_DIR,'cache', wfn+'.wav' )

        text = self.prepareText(text)
        logDebug( f'{config.ttsEngine}: "{text}"' )

        #print(f'wave file name= {waveFileName}')
        #self.sendMessage( MSG_TEXT, text )

        #todo: rewrite to optimize 
        isLocked = True
        while isLocked:
            await ttsLock.acquire()
            if not (wfn in ttsLocked):
                ttsLocked.add(wfn)
                isLocked = False
            ttsLock.release()
            if isLocked:
                await asyncio.sleep(0.1)
        
        try:
            # Загрузить файл из кэша, если есть.
            if os.path.isfile(waveFileName):
                #dt = datetime.datetime.now().ns
                os.utime(waveFileName,)
                # Максимальный размер файла 5MB
                with open( waveFileName, 'rb' ) as f:
                    speech = f.read( 5000 * 1024 )
        except Exception as e:
            logError(f'Ошибка при загрузке аудиофрагмента из кэша: {type(e).__name__}: {e}' )
            speech = None

        # check if file was not loaded from cache
        if speech is None or len(speech) < 500:
            try:
                logDebug(f'{config.ttsEngine}: Cache not found, generating')
                if (config.ttsEngine == TTS_RHVOICE):
                    rhvoice = rhvoiceWrapper.TTS( 
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

                    # https://pypi.org/project/rhvoice-wrapper/

                    frames = rhvoice.get( text, 
                        voice= config.rhvParams['voice'],
                        format_='pcm', 
                        sets=config.rhvParams
                    )
                    rhvoice.join()

                    # fn = os.path.join( ROOT_DIR, 'logs', datetime.datetime.today().strftime(f'%Y%m%d_%H%M%S_say') )
                    # f = open( fn+'.pcm','wb')
                    # f.write(frames)
                    # f.close()
                    with wave.open( waveFileName, 'wb' ) as wav:
                        wav.setsampwidth(2)
                        wav.setnchannels(1)
                        wav.setframerate(24000)
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
                    sapiVoices = sapi.GetVoices()
                    v = config.voice.lower().strip()
                    for sapiVoice in sapiVoices:
                        if sapiVoice.GetAttribute("Name").lower().strip().startswith(v):
                            sapi.Voice = sapiVoice
                    sapi.Rate = config.sapiRate
                    sapiStream.Open( waveFileName, 3 )
                    sapi.AudioOutputStream = sapiStream
                    sapi.Speak(text)
                    sapi.WaitUntilDone(-1)
                    sapiStream.Close()

                if os.path.isfile(waveFileName):
                    #dt = datetime.datetime.now().ns
                    os.utime(waveFileName,)
                    # Максимальный размер файла 5MB
                    with open( waveFileName, 'rb' ) as f:
                        speech = f.read( 5000 * 1024 )

            except Exception as e:
                logError( f'TTS Engine exception: {e}' )

        await ttsLock.acquire()
        ttsLocked.remove(wfn)
        ttsLock.release()

        if speech is not None and len(speech)<500:
            speech = None
        return speech

    def cacheRotate(self):
        pass
    def cacheClean(self):
        pass

    def prepareText(self, text:str )->str:
        result = str(text)

        if (config.ttsEngine == TTS_RHVOICE):
            # Заменить признак ударения "+" на символ ударения (#0301) 
            while True:
                p = result.find("+")
                if (p>0) and (p+1<len(result)):
                    result = result[:p]+result[p+1:p+2]+f'\u0301'+result[p+2:]
                else:
                    break
        else:
            pass

        while True:
            m = re.search('\[[^\[\]\:]*\:[^\[\]\:]*\]', result)
            if bool(m): 
                (text,tgs) = m.group()[1:-1].strip().split(":")
                while True: 
                    _ = tgs
                    tgs = tgs.replace(',',' ').replace( '  ',' ' ).strip()
                    if tgs == _ :break

                tInteger = None
                tags = ''
                f = True
                for t in tgs.split(' '):
                    if len(str(t.strip()))>0:
                        try:
                            number = float(t)
                            if f :
                                text = conformToNumber( number, text)
                                f = False
                            else:
                                tags += ' ' + t + ' '
                        except ValueError:
                            tags += ' ' + t + ' '

                tags = extractTags( tags )
                if bool(tags):
                    text = inflectText( transcribeText(text),tags )
                    
                result = result[:m.start()].strip() + ' ' + text.strip() + ' ' + result[m.end():].strip()
            else:
                break

        return transcribeText(result)

#endregion

