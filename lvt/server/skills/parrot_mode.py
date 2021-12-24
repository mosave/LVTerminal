import sys
import time
from lvt.const import *
from lvt.protocol import *
from lvt.server.grammar import *
from lvt.server.skill import Skill

TOPIC_PARROT_MODE = 'ParrotMode'
REMINDER_TIMEOUT = 60
class ParrotModeSkill(Skill):
    """Скилл "Режим попугая" позволяет оценить качество распознавания речи.
    Ключевые фразы для активации режима: "Повторяй за мной" или "Включи режим попугая"
    """
    def onLoad( this ):
        this.subscribe( TOPIC_DEFAULT,TOPIC_PARROT_MODE )
        this.priority = 1000
        this.remindOn = 0
        this.extendVocabulary( "повторяй за мной, включи режим попугая" )
        this.extendVocabulary( "выключи режим попугая, перестань повторять" )

    def onText( this ):
        if this.topic == TOPIC_PARROT_MODE:
            this.remindOn = time.time() + REMINDER_TIMEOUT

            iOff = this.findWord( 'выключи' )
            iOn = this.findWord( 'включи' )

            iStop = this.findWord( 'перестань' )
            iRepeat = this.findWord( 'повторять' )
            iParrot = this.findWord( 'попугай' )
            if iOff >= 0 and iParrot > 0 or iStop >= 0 and iRepeat >= 0 :
                this.stopParsing( ANIMATION_ACCEPT )
                this.changeTopic( TOPIC_DEFAULT )
            else:
                this.say( this.terminal.originalTextUnfiltered )

        else:
            if this.isAppealed :
                if this.findWordChainB( 'включи режим попугая' ) or \
                    this.findWordChainB( 'переключись * режим попугая' ) or \
                    this.findWordChainB( 'перейди в режим попугая' ) or \
                    this.findWordChainB( 'повторяй за мной' ) :
                    this.changeTopic( TOPIC_PARROT_MODE )
                    this.stopParsing( ANIMATION_ACCEPT )

    def onTopicChange( this, newTopic: str, params={} ):
        if this.topic == TOPIC_DEFAULT and newTopic == TOPIC_PARROT_MODE :
            this.animate( ANIMATION_AWAKE )
            this.say( 'Окей, говорите и я буду повторять всё, что услышу!. ' + 'Для завершения скажите: "перестань за мной повторять"' )
            # Задаем время проговаривания напоминания
            this.remindOn = time.time() + REMINDER_TIMEOUT
        elif this.topic == TOPIC_PARROT_MODE :
            this.say( 'Режим попугая выключен' )
            this.remindOn = 0
       
    def onTimer( this ):
        if( this.topic == TOPIC_PARROT_MODE ):
            if time.time() > this.remindOn:
                this.say( 'Для завершения скажите "выключить режим попугая" или "перестань за мной повторять"!' )
                this.remindOn = time.time() + REMINDER_TIMEOUT

