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
        this.subscribe( TOPIC_DEFAULT,TOPIC_PARROT_MODE )
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
            iRecognize = this.findWord( 'распознавание' )
            (iNoDict,_) = this.findWordChain( 'без словаря' )
            iDict = this.findWord( 'словарь' ) if iNoDict<0 else -1

            iStop = this.findWord( 'перестань' )
            iRepeat = this.findWord( 'повторять' )
            iParrot = this.findWord( 'попугай' )
            iBeParrot = this.findWord( 'попугайничать',{'INFN'} )
            if iOff>=0 and iParrot>0  or  iStop>=0 and ( iRepeat>=0 or iBeParrot>=0 ) :
                this.stopParsing(ANIMATION_ACCEPT)
                this.changeTopic( TOPIC_DEFAULT )
            elif iOn>=0 and iOn<iDict  or  iOff>=0 and iOff<iNoDict :
                if this.terminal.usingVocabulary:
                    this.stopParsing(ANIMATION_CANCEL)
                    s = "Режим распознавания со словарём уже включен"
                else:
                    this.stopParsing(ANIMATION_ACCEPT)
                    this.terminal.usingVocabulary = True
                    s = "Включаю режим распознавания со словарём"
                this.animate(ANIMATION_AWAKE)
                this.say(s)
            elif iOff>=0 and  iOff<iDict  or  iOn>=0 and iOn<iNoDict :
                if this.terminal.usingVocabulary:
                    this.stopParsing(ANIMATION_ACCEPT)
                    this.terminal.usingVocabulary = False
                    s = "Выключаю режим распознавания со словарём"
                else:
                    this.stopParsing(ANIMATION_CANCEL)
                    s = "Режим распознавания со словарём уже выключен"
                this.animate(ANIMATION_AWAKE)
                this.say(s)
            else:
                this.say( this.terminal.originalText )

        else:
            if this.isAppealed :
                if this.findWordChainB( 'включи режим попугая' ) or \
                    this.findWordChainB( 'переключись * режим попугая' ) or \
                    this.findWordChainB( 'перейди в режим попугая' ) or \
                    this.findWordChainB( 'повторяй за мной' ) :
                    this.changeTopic( TOPIC_PARROT_MODE )
                    this.stopParsing(ANIMATION_ACCEPT)

    def onTopicChange( this, newTopic: str, params = {} ):
        if newTopic == TOPIC_PARROT_MODE :
            this.terminal.sendMessage( MSG_MUTE_WHILE_SPEAK_ON )
            this.animate(ANIMATION_AWAKE)
            this.say( 'Окей, говорите и я буду повторять всё, что услышу!' )
            this.say( 'Для завершения скажите: "перестань за мной повторять"' )
            s = "со словарём" if this.terminal.usingVocabulary else "без словаря"
            this.say( f'Активен режим распознавания {s}.' )
            # Задаем время проговаривания напоминания
            this.remindOn = time.time() + REMINDER_TIMEOUT
        elif this.topic == TOPIC_PARROT_MODE :
            this.say( 'Режим попугая выключен' )
            this.remindOn = 0
            if this.terminal.usingVocabulary != this.terminal.vocabularyMode :
                s = "со словарем" if this.terminal.vocabularyMode  else "без словаря"
                this.say( f'Режим распознавания {s} активирован' )
            this.terminal.sendMessage( MSG_MUTE_WHILE_SPEAK_OFF )
       
    def onTimer( this ):
        if( this.topic == TOPIC_PARROT_MODE ):
            if time.time() > this.remindOn:
                this.say( 'Для возврата в нормальный режим скажите "выключить режим попугая" или "перестань за мной повторять"!' )
                this.remindOn = time.time() + REMINDER_TIMEOUT

