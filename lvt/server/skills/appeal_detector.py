import sys
import time
import datetime
from lvt.const import *
from lvt.protocol import *
import lvt.server.config as config
from lvt.server.grammar import *
from lvt.server.utterances import Utterances
from lvt.server.skill import Skill

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
        self.utterances.add("alive", "[ты здесь, ты живой, ты еще живой, ты там живой, ты там еще живой]")
        self.utterances.add("hearing", "[ты меня слышишь, ты там меня слышишь]")
        self.vocabulary = self.utterances.vocabulary

    async def onTextAsync( self ):
        # Проверяем, есть ли в фразе обращение:
        if self.detectAppeals():
            self.lastSound = time.time()
            if self.topic == TOPIC_DEFAULT :
                self.terminal.animate( ANIMATION_AWAKE )
                # В случае если фраза содержит только обращение - завершаем обработку фразы
                if len( self.words ) == 0:
                    self.stopParsing()
                else:
                    matches = self.utterances.match(self.words)
                    if len(matches)>0 :
                        self.stopParsing( ANIMATION_ACCEPT )
                        if matches[0].id=='voice':
                            await self.sayAsync( ['Гав. Гав-гав.', 'мяаау блин.', 'отстаньте от меня','не мешайте, я за домом присматриваю','не мешайте, я думаю', 'шутить изволите?'] )
                        elif matches[0].id=='alive':
                            await self.sayAsync( ['да, конечно', 'куда же я денусь', 'пока всё еще да','живее всех живых','не мешайте, я думаю', 'шутить изволите?'] )
                        elif matches[0].id=='hearing':
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

