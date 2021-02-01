import sys
import time
import datetime
from lvt.const import *
from lvt.protocol import *
from lvt.server.grammar import *
from lvt.server.skill import Skill

TOPIC_WAIT_COMMAND = "WaitCommand"
WAIT_COMMAND_TIMEOUT = 5 # время в режиме ожидания команды, секунд

#Define base skill class
class AppealDetectorSkill(Skill):
    """Скил определяет наличие в фразе обращения к ассистенту и реализует режим ожидания команды.
    Скилл поддерживает следующие переменные
    * terminal.isAppealed -> bool  : в фразе содержится обращение к ассистенту
    * terminal.appeal -> str : имя, по которому обратились к ассистенту
    * terminal.appealPos -> int : индекс слова, в котором содержится обращение

    Кроме того, если фраза содержит только имя ассистента, скилл переходит к топику "WaitCommand" 
    Если в течение 5 секунд распознается очередная фраза

    """
    def onLoad( this ):
        #print('loading AppealDetector')
        this.priority = 10000
        this.subscribe( TOPIC_ALL )
        this.savedTopic = TOPIC_DEFAULT
        this.waitUntil = 0
        this.aNames = wordsToList( this.terminal.config.femaleAssistantNames + ' ' + this.terminal.config.maleAssistantNames )


    def onText( this ):
        # Если в режиме ожидания 
        if this.topic == TOPIC_WAIT_COMMAND:
            # Добавить в начало команды обращение, если нужно
            if not this.detectAppeals(): this.insertWords( 0,'слушай ' + this.appeal )
            # И перезапустить распознавание без топика
            this.changeTopic( TOPIC_DEFAULT )
            this.restartParsing()
            return

        # Не в режиме ожидания:
        # Проверяем, есть ли в фразе обращение:
        if this.detectAppeals():
            if this.topic == TOPIC_DEFAULT :
                this.terminal.animate( ANIMATION_AWAKE )
                # В случае если фраза содержит только обращение - переходим в ожидание команды
                if len( this.words ) == 1 :
                    this.savedTopic = this.topic
                    this.changeTopic( TOPIC_WAIT_COMMAND )
                    this.stopParsing()
                elif  this.findWordChainB( 'ты здесь' ) or \
                    this.findWordChainB( 'ты * живой' ) :
                    this.stopParsing( ANIMATION_ACCEPT )
                    this.say( ['да, конечно', 'куда же я денусь', 'пока всё еще да','живее всех живых'] )
                elif this.findWordChainB( 'меня слышишь' ) :
                    this.stopParsing( ANIMATION_ACCEPT )
                    this.say( ['ну конечно слышу', 'да, не ' + this.conformToAppeal( 'глухая' ), 'слышу-слышу', 'само-собой'] )

    def onPartialText( this ):
        # В процессе распознавания текста:
        # В режиме ожидания команды - увеличиваем таймаут
        if this.topic == TOPIC_WAIT_COMMAND:
            this.waitUntil = time.time() + WAIT_COMMAND_TIMEOUT
        else: # Распознаем наличие обращения
            if this.detectAppeals():
                if this.topic == TOPIC_DEFAULT:
                    this.terminal.animate( ANIMATION_AWAKE )


    def detectAppeals( this ):
        if this.isAppealed :
            return True
        aPos = None
        # Получить список имен ассистента
        for aName in this.aNames: # Встречается ли в фразе имя ассистента?
            aPos = this.findWord( aName, {'NOUN','nomn','sing'} )
            if aPos >= 0 : 
                # Сохраняем на будущее как и когда обратились к ассистенту
                this.terminal.appeal = this.getNormalForm( aPos, {'NOUN','nomn','sing'} )
                if this.terminal.appeal == 'алиша' : this.terminal.appeal = 'алиса'
                this.terminal.lastAppealed = datetime.datetime.now()
                break

        if aPos == None or aPos < 0 : return False

        # Обращение вида "Эй, ассистент" 
        if aPos > 0 : 
            if this.isWord( aPos - 1,'эй' ) or this.isWord( aPos - 1,'хэй' ) or this.isWord( aPos - 1,'алло' ) or this.isWord( aPos - 1,'и' ) or this.isWord( aPos - 1,'слушай' ) :
                # Удаляем незначащее слово
                aPos -= 1
                this.deleteWord( aPos )

        # Обращение вида "Ассистент, слушай"
        if aPos + 1 < len( this.words ) :
            if this.isWord( aPos + 1,'слушай' ) or this.isWord( aPos - 1,'алло' ) :
                # Удаляем незначащее слово
                this.deleteWord( aPos + 1 )

        this.terminal.appealPos = aPos
        this.terminal.isAppealed = True
        return True

    def onTopicChange( this, newTopic: str, params={} ):
        if newTopic == TOPIC_WAIT_COMMAND :
            # Задаем время ожидания команды
            this.waitUntil = time.time() + WAIT_COMMAND_TIMEOUT
            this.play( 'appeal_on.wav' )
        elif this.topic == TOPIC_WAIT_COMMAND :
            # Играем отбой
            this.waitUntil = 0
       
    def onTimer( this ):
        if( this.topic == TOPIC_WAIT_COMMAND ):
            if time.time() > this.waitUntil:
                this.animate( ANIMATION_CANCEL )
                this.play( 'appeal_off.wav' )
                this.changeTopic( this.savedTopic )


