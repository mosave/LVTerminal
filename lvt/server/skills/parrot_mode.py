import sys
import time
from lvt.const import *
from lvt.server.grammar import *
from lvt.server.skill import Skill

TOPIC_PARROT_MODE = 'ParrotMode'
REMINDER_TIMEOUT = 60
class ParrotModeSkill(Skill):
    """Скилл "Режим попугая" позволяет оценить качество распознавания речи.
    Ключевые фразы для активации режима: "Повторяй за мной" или "Включи режим попугая"
    """
    def onLoad( this ):
        #print('loading repeat')
        this.subscribe( TOPIC_DEFAULT )
        this.subscribe( TOPIC_PARROT_MODE )
        this.priority = 1000
        this.remindOn = 0
        this.extendVocabulary("повторяй за мной, включи, переключись в режим попугая");
        this.extendVocabulary("выключи режим попугая, перестань повторять, перестань попугайничать");

    def onText( this ):
        if this.topic == TOPIC_PARROT_MODE:
            this.remindOn = time.time() + REMINDER_TIMEOUT
            iOff = this.findWord( 'выключи' )
            iOn = this.findWord( 'включи' )
            if iOn<0 : iOn = this.findWord( 'переключись' )
            iDict = this.findWord( 'словарь' )
            iRecognize = this.findWord( 'распознавание' )
            iNoDict = this.findWordChain( 'без словаря' )
            iStop = this.findWord( 'перестань' )
            iRepeat = this.findWord( 'повторять' )
            iParrot = this.findWord( 'попугай' )
            iBeParrot = this.findWord( 'попугайничать',{'INFN'} )
            if iOff>=0 and iParrot>0 or \
                iStop>=0 and ( iRepeat>=0 or iBeParrot>=0 ) :
                this.stopParsing(ANIMATION_ACCEPT)
                this.changeTopic( TOPIC_DEFAULT )
            elif iNoDict<0 and iDict>=0 and iOn>=0 and iOn<iDict or \
                iNoDict>=0 and iOff>=0 and iOff<iNoDict :
                if this.terminal.usingVocabulary:
                    this.stopParsing(ANIMATION_CANCEL)
                    this.say("режим распознавания со словарем уже включен")
                else:
                    this.stopParsing(ANIMATION_ACCEPT)
                    this.terminal.usingVocabulary = True
                    this.say("Включаю режим распознавания со словарем")
            elif iNoDict<0 and iDict>=0 and iOff>=0 and  iOff<iDict or \
                iNoDict>=0 and iOn>=0 and iOn<iNoDict :
                if this.terminal.usingVocabulary:
                    this.stopParsing(ANIMATION_ACCEPT)
                    this.terminal.usingVocabulary = False
                    this.say("Выключаю режим распознавания со словарем")
                else:
                    this.stopParsing(ANIMATION_CANCEL)
                    this.say("режим распознавания со словарем уже выключен")
            else:
                this.say( this.terminal.originalText )


        else:
            if this.isAppealed :
                if this.findWordChain( 'включи режим попугая' )>=0 or \
                    this.findWordChain( 'переключись режим попугая' )>=0 or \
                    this.findWordChain( 'переключись в режим попугая' )>=0 or \
                    this.findWordChain( 'перейди в режим попугая' )>=0 or \
                    this.findWordChain( 'повторяй за мной' )>=0 :
                    this.terminal.animate(ANIMATION_ACCEPT)
                    this.changeTopic( TOPIC_PARROT_MODE )

        this.stopParsing()

    def onTopicChange( this, topic:str, newTopic: str ):
        if newTopic == TOPIC_PARROT_MODE :
            this.say( 'Окей, говорите и я буду повторять всё, что услышу!' )
            s = "со словарем" if this.terminal.usingVocabulary else "без словаря"
            this.say( f'Активен режим распознавания {s}.' )
            this.say( 'Для завершения скажите: "перестань за мной повторять"' )
            # Задаем время проговаривания напоминания
            this.remindOn = time.time() + REMINDER_TIMEOUT
        elif topic == TOPIC_PARROT_MODE :
            this.say( 'Режим попугая выключен' )
            this.remindOn = 0
            if this.terminal.usingVocabulary != this.terminal.vocabularyMode :
                s = "со словарем" if this.terminal.vocabularyMode  else "без словаря"
                this.say( f'Режим распознавания {s} активирован' )
       
    def onTimer( this ):
        if( this.topic == TOPIC_PARROT_MODE ):
            if time.time() > this.remindOn:
                this.say( 'Для возврата в нормальный режим скажите "выключить режим попугая" или "перестань за мной повторять"!' )
                this.remindOn = time.time() + REMINDER_TIMEOUT
                this.animate( ANIMATION_NONE )

