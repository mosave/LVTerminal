import time
import datetime
import asyncio
from lvt.const import *
from lvt.protocol import *
import lvt.server.config as config
from lvt.server.grammar import *
from lvt.server.utterances import Utterances
from lvt.server.skill import Skill

# Время ожидания команды в режиме Appealed, секунд
APPEAL_TIMEOUT = 10

#Define base skill class
class AppealDetectorSkill(Skill):
    """Скил определяет наличие в фразе обращения к ассистенту и удаляет вычищает его из анализируемого текста.
    Скилл поддерживает следующие переменные
    * terminal.isAppealed -> bool  : в фразе содержится обращение к ассистенту
    * terminal.appeal -> str : имя, по которому обратились к ассистенту
    """
    def onLoad( self ):
        #print('loading AppealDetector')
        self.priority = 10000
        self.subscribe( TOPIC_DEFAULT )
        self.waitUntil = 0
        self.aNames = wordsToList( config.assistantNames )
        self.utterances = Utterances( self.terminal )
        self.utterances.add("voice", "[Голос, подай голос, скажи что-нибудь]")
        # "ты" в фразе распознается ненадежно. В шаблоне просто исключим его из распознавания
        self.utterances.add("alive", "[здесь, живой, еще живой, там живой, там еще живой]")
        self.utterances.add("hearing", "[меня слышишь, слышишь, там меня слышишь]")
        self.setVocabulary( TOPIC_DEFAULT, self.utterances.vocabulary )
        self.appealTimeout = 0
        self.isPlaying = False

    async def onTextAsync( self ):
        # Проверяем, есть ли в фразе обращение:
        if self.detectAppeals():
            # Если мы не находимся в режиме ожидания команды
            if self.appealTimeout == 0:
                # В случае если фраза содержит только обращение - 
                # переходим в режим ожидания команды и запускаем таймер
                if len( self.words ) == 0:
                    self.isPlaying = self.terminal.isPlaying
                    self.terminal.playerMute()
                    if not self.isPlaying:
                        await asyncio.sleep(0.1)
                        await self.terminal.sayAsync( [ 'Да?', 'Слушаю?', 'Что?', 'Я' ] )
                    self.stopParsing()
                    self.terminal.sendMessage( MSG_WAKEUP )
                    self.appealTimeout = time.time() + APPEAL_TIMEOUT
                else:
                    matches = self.utterances.match(self.words)
                    if len(matches)>0 :
                        self.stopParsing()
                        if matches[0].id=='voice':
                            await self.terminal.sayAsync( ['Гав. Гав-гав.', 'мяаау блин', 'отстаньте от меня','не мешайте, я за домом присматриваю','не мешайте. я думаю', 'шутить изволите?'] )
                        elif matches[0].id=='alive':
                            await self.terminal.sayAsync( ['да. конечно', 'куда же я денусь', 'пока всё еще да','живее всех живых','не мешайте. я думаю', 'шутить изволите?'] )
                        elif matches[0].id=='hearing':
                            await self.terminal.sayAsync( ['ну конечно слышу', 'да. '+self.terminal.appeal+' не ' + self.terminal.conformToAppeal( 'глухая' ), 'слышу-слышу', 'само собой'] )

            else:
                self.appealTimeout =  time.time() + 3


    async def onTimerAsync( self ):
        if (self.appealTimeout != 0) and ( time.time() > self.appealTimeout) :
            self.terminal.sendMessage( MSG_IDLE )
            self.terminal.isAppealed = False
            self.terminal.playerUnmute()
            self.appealTimeout = 0
            return

    def detectAppeals( self ):
        # LVT уже находится в режиме ожидания команды.
        if self.appealTimeout != 0:
            self.terminal.isAppealed = True

        aPos = -1
        # Определим, содержится ли в обрабатываемой фразе обращение к ассистенту:

        for aName in self.aNames: # Встречается ли в фразе имя ассистента?
            aPos = self.findWord( aName, {'NOUN','nomn','sing'} )
            if aPos >= 0 : 
                # Сохраняем на будущее как и когда обратились к ассистенту
                self.terminal.appeal = self.getNormalForm( aPos, {'NOUN','nomn','sing'} )
                self.terminal.lastAppealed = datetime.datetime.now()
                break

        # Обращение к ассистенту найдено. Очистим текст от него, оставив только текст команды
        if aPos >=0:
            self.terminal.isAppealed = True

            # Обращение вида "Эй, ассистент" 
            if aPos > 0 : 
                if self.isWord( aPos - 1,'эй' ) or self.isWord( aPos - 1,'хэй' ) or self.isWord( aPos - 1,'алло' ) or self.isWord( aPos - 1,'и' ) or self.isWord( aPos - 1,'слушай' ) :
                    # Удаляем незначащее слово
                    aPos -= 1
                    self.deleteWord( aPos )

            # Обращение вида "Ассистент, слушай"
            if aPos + 1 < len( self.words ) :
                if self.isWord( aPos + 1,'слушай' ) or self.isWord( aPos - 1,'алло' ) :
                    # Удаляем незначащее слово
                    self.deleteWord( aPos + 1 )

            if aPos<len(self.words):
                self.deleteWord(aPos)

        return self.terminal.isAppealed
