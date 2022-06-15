import sys
import time
import datetime
from lvt.const import *
from lvt.protocol import *
import lvt.server.config as config
from lvt.server.grammar import *
from lvt.server.skill import Skill

#Define base skill class
class AppealDetectorSkill(Skill):
    """Скил определяет наличие в фразе обращения к ассистенту и реализует режим ожидания команды.
    Скилл поддерживает следующие переменные
    * terminal.isAppealed -> bool  : в фразе содержится обращение к ассистенту
    * terminal.appeal -> str : имя, по которому обратились к ассистенту

    Кроме того, если фраза содержит только имя ассистента, скилл переходит к топику "WaitCommand" 
    Если в течение 5 секунд распознается очередная фраза - она

    """
    def onLoad( self ):
        #print('loading AppealDetector')
        self.priority = 10000
        self.subscribe( TOPIC_ALL )
        self.savedTopic = TOPIC_DEFAULT
        self.waitUntil = 0
        self.aNames = wordsToList( config.assistantNames )
        self.extendVocabulary('подай голос, скажи что-нибудь,голос,ты здесь,живой, живая, меня слышишь' )

    async def onText( self ):
        # Если в режиме ожидания 
        if self.topic == TOPIC_WAIT_COMMAND:
            # Добавить в начало команды обращение, если нужно
            if not self.detectAppeals(): self.insertWords( 0,'слушай ' + self.appeal )
            # Ставим галочку в терминале что в случае необнаружения команды озвучить appeal_off
            self.terminal.playAppealOffIfNotStopped = True
            # И перезапустить распознавание без топика
            await self.changeTopicAsync( TOPIC_DEFAULT )
            self.restartParsing()
            return

        # Не в режиме ожидания:
        # Проверяем, есть ли в фразе обращение:
        if self.detectAppeals():
            self.lastSound = time.time()
            if self.topic == TOPIC_DEFAULT :
                self.terminal.animate( ANIMATION_AWAKE )
                # В случае если фраза содержит только обращение - переходим в ожидание команды
                if len( self.words ) == 0:
                    self.savedTopic = self.topic
                    await self.changeTopicAsync( TOPIC_WAIT_COMMAND )
                    self.stopParsing()
                elif self.findWordChainB( 'подай голос' ) or \
                    self.findWordChainB( 'скажи что-нибудь' ) or \
                    self.findWordChainB( 'голос' ) :
                    self.stopParsing( ANIMATION_ACCEPT )
                    await self.sayAsync( ['Гав. Гав-гав.', 'мяаау блин.', 'отстаньте от меня','не мешайте, я за домом присматриваю','не мешайте, я думаю', 'шутить изволите?'] )
                elif self.findWordChainB( 'ты здесь' ) or \
                    self.findWordChainB( 'ты * живой' ) :
                    self.stopParsing( ANIMATION_ACCEPT )
                    await self.sayAsync( ['да, конечно', 'куда же я денусь', 'пока всё еще да','живее всех живых','не мешайте, я думаю', 'шутить изволите?'] )
                elif self.findWordChainB( 'меня слышишь' ) :
                    self.stopParsing( ANIMATION_ACCEPT )
                    await self.sayAsync( ['ну конечно слышу', 'да, '+self.appeal+' не ' + self.conformToAppeal( 'глухая' ), 'слышу-слышу', 'само собой'] )

    def detectAppeals( self ):
        if self.isAppealed :
            return True
        aPos = None
        # Получить список имен ассистента
        for aName in self.aNames: # Встречается ли в фразе имя ассистента?
            aPos = self.findWord( aName, {'NOUN','nomn','sing'} )
            if aPos >= 0 : 
                # Сохраняем на будущее как и когда обратились к ассистенту
                self.terminal.appeal = self.getNormalForm( aPos, {'NOUN','nomn','sing'} )
                #if self.terminal.appeal == 'алиша' : self.terminal.appeal = 'алиса'
                self.terminal.lastAppealed = datetime.datetime.now()
                break

        if aPos == None or aPos < 0 : return False

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

        self.terminal.isAppealed = True
        return True

    async def onTopicChange( self, newTopic: str, params={} ):
        if newTopic == TOPIC_WAIT_COMMAND :
            # Задаем время ожидания команды
            self.waitUntil = time.time() + WAIT_COMMAND_TIMEOUT
            await self.playAsync( 'appeal_on.wav' )
        elif self.topic == TOPIC_WAIT_COMMAND :
            # Играем отбой
            self.waitUntil = 0
       
    async def onTimer( self ):
        if( self.topic == TOPIC_WAIT_COMMAND ):
            if time.time() > self.waitUntil:
                self.animate( ANIMATION_CANCEL )
                await self.playAsync( 'appeal_off.wav' )
                await self.changeTopicAsync( self.savedTopic )
                self.terminal.playAppealOffIfNotStopped = False


