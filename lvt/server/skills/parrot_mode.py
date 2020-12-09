import sys
import time
from lvt.const import *
from lvt.server.grammar import *
from lvt.server.skill import Skill

TOPIC_PARROT_MODE = 'ParrotMode'
REMINDER_TIMEOUT = 30
class ParrotModeSkill(Skill):
    """По ключевым фразам 'Включи режим попугая' или 'Повторяй за мной'
    переходит в режим попугая
    """
    def onLoad( this ):
        #print('loading repeat')
        this.subscribe( TOPIC_DEFAULT )
        this.subscribe( TOPIC_PARROT_MODE )
        this.priority = 1000
        this.remindOn = 0

    def onText( this ):
        if this.topic == TOPIC_PARROT_MODE:
            this.remindOn = time.time() + REMINDER_TIMEOUT
            iOff = this.findWord( 'выключи' )
            iStop = this.findWord( 'перестань' )
            iRepeat = this.findWord( 'повторять' )
            iParrot = this.findWord( 'попугай' )
            iBeParrot = this.findWord( 'попугайничать',{'INFN'} )
            if iOff != None and iParrot != None or \
                iStop != None and ( iRepeat != None or iBeParrot != None ) :
                this.changeTopic( TOPIC_DEFAULT )
                this.stopParsing()
            else:
                this.say( this.terminal.originalText )
        else:
            if this.isAppealed :
                if this.findWordChain( 'включи режим попугая' ) != None or \
                    this.findWordChain( 'перейди в режим попугая' ) != None or \
                    this.findWordChain( 'повторяй за мной' ) :
                    this.changeTopic( TOPIC_PARROT_MODE )
                    this.stopParsing()



    def onTopicChange( this, topic:str, newTopic: str ):
        if newTopic == TOPIC_PARROT_MODE :
            this.say( 'Окей, говорите и я буду повторять всё, что услышу!' )
            this.say( 'Для завершения скажите: "перестань за мной повторять"' )
            # Задаем время проговаривания напоминания
            this.remindOn = time.time() + REMINDER_TIMEOUT
        elif topic == TOPIC_PARROT_MODE :
            this.say( 'Режим попугая выключен' )
            this.remindOn = 0
       
    def onTimer( this ):
        if( this.topic == TOPIC_PARROT_MODE ):
            if time.time() > this.remindOn:
                this.say( 'Для возврата в нормальный режим скажите "выключить режим попугая" или "перестань за мной повторять"!' )
                this.remindOn = time.time() + REMINDER_TIMEOUT

