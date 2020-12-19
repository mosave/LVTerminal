import sys
import time
from lvt.const import *
from lvt.server.grammar import *
from lvt.server.skill import Skill

TOPIC_WAIT_COMMAND = "WaitCommand"
WAIT_COMMAND_TIMEOUT = 5 # время в режиме ожидания команды, секунд

#Define base skill class
class AppealDetectorSkill(Skill):
    def onLoad( this ):
        #print('loading AppealDetector')
        this.priority = 10000
        this.subscribe( TOPIC_ALL )
        this.savedTopic = TOPIC_DEFAULT
        this.waitUntil = 0

    def onText( this ):
        # Если в режиме ожидания 
        if this.topic == TOPIC_WAIT_COMMAND:
            # Добавить в начало команды обращение, если нужно
            if not this.detectAppeals(): this.insertWords(0,'слушай '+this.appeal)
            # И перезапустить распознавание без топика
            this.changeTopic(TOPIC_DEFAULT)
            this.restartParsing()
            return

        # Не в режиме ожидания:
        # Проверяем, есть ли в фразе обращение:
        if this.detectAppeals():
            this.terminal.animate(ANIMATION_AWAKE)
            # В случае если фраза содержит только обращение - переходим в ожидание команды
            if len(this.words)==1 :
                this.savedTopic = this.topic
                this.changeTopic(TOPIC_WAIT_COMMAND)
                this.stopParsing()

    def onPartialText( this ):
        # В процессе распознавания текста:
        # В режиме ожидания команды - увеличиваем таймаут
        if this.topic == TOPIC_WAIT_COMMAND:
            this.waitUntil = time.time() + WAIT_COMMAND_TIMEOUT
        else: # Распознаем наличие обращения
            if this.detectAppeals():
                this.terminal.animate(ANIMATION_AWAKE)


    def detectAppeals( this ):
        aPos = None
        # Получить список имен ассистента
        aNames = wordsToList(this.config.assistantName)
        for aName in aNames: # Встречается ли в фразе имя ассистента?
            aPos = this.findWord( aName, {'NOUN','nomn','sing'} )
            if aPos != None : 
                # Сохраняем на будущее как обратились к ассистенту
                this.terminal.appeal = this.getNormalForm( aPos, {'NOUN','nomn','sing'})
                break

        this.terminal.appealPos = aPos

        if aPos == None : return False

        # Обращение вида "Эй, ассистент" 
        if aPos > 0 : 
            if this.isWord(aPos-1,'эй') \
                or this.isWord(aPos-1,'хэй') \
                or this.isWord(aPos-1,'алло') \
                or this.isWord(aPos-1,'и') \
                or this.isWord(aPos-1,'слушай') :
                # Удаляем незначащее слово
                aPos -= 1
                this.deleteWord(aPos)

        # Обращение вида "Ассистент, слушай"
        if aPos+1<len(this.words) :
            if this.isWord(aPos+1,'слушай') \
                or this.isWord(aPos-1,'алло') :
                # Удаляем незначащее слово
                this.deleteWord(aPos+1)

        this.terminal.appealPos = aPos
        return True

    def onTopicChange( this, topic:str, newTopic: str ):
        if newTopic == TOPIC_WAIT_COMMAND :
            # Задаем время ожидания команды
            this.waitUntil = time.time() + WAIT_COMMAND_TIMEOUT
            this.play('appeal_on.wav')
        elif topic == TOPIC_WAIT_COMMAND :
            # Играем отбой
            this.play('appeal_off.wav')
            this.waitUntil = 0
       
    def onTimer( this ):
        if( this.topic == TOPIC_WAIT_COMMAND ):
            if time.time() > this.waitUntil:
                this.changeTopic(this.savedTopic)
                this.animate( ANIMATION_NONE )


