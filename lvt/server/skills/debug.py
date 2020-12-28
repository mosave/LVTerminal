import sys
import time
from lvt.const import *
from lvt.server.grammar import *
from lvt.server.skill import Skill
from lvt.server.skills.yes_no import YesNoParams

TOPIC_DEBUG_YES_NO = "DebugYesNo"
TOPIC_DEBUG1 = "Debug1"
TOPIC_DEBUG2 = "Debug2"
TOPIC_DEBUG3 = "Debug3"
TOPIC_DEBUG4 = "Debug4"
TOPIC_DEBUG_YES = "DebugYes"
TOPIC_DEBUG_NO = "DebugNo"
TOPIC_DEBUG_CANCEL = "DebugCancel"
#Define base skill class
class DebugSkill(Skill):
    def onLoad( this ):
        this.priority = 9000
        this.extendVocabulary("проверка да или нет")
        this.extendVocabulary("проверка поиска по шаблону")
        this.subscribe( TOPIC_DEFAULT,  TOPIC_DEBUG_YES,TOPIC_DEBUG_NO, TOPIC_DEBUG_CANCEL,
                       TOPIC_DEBUG1,TOPIC_DEBUG2, TOPIC_DEBUG3, TOPIC_DEBUG4 )

    def onText( this ):
        if this.isAppealed :
            if this.findWordChainB("проверка поиска по шаблону") :
                def failed( pattern, pos, len ) :
                    (p,l) = this.findWordChain( pattern )
                    if p != pos  or l != len :
                        this.say(f'Ошибка при поиске {pattern}: ({p},{l})')
                        this.stopParsing(ANIMATION_CANCEL)
                        return True
                    else:
                        return False

                this.stopParsing(ANIMATION_ACCEPT)
                this.terminal.text = normalizeWords('ноль один два три четыре пять шесть семь восемь девять ноль один два')
                if failed('два три четыре',2,3) : return
                if failed('девять ноль один два три', -1, 0) : return
                if failed('два три ? четыре', -1, 0) : return
                if failed('два три ? пять', 2,4) : return
                if failed('два три * четыре', 2,3) : return
                if failed('два три * шесть', 2,5) : return
                if failed('два * один',2,10) : return
                if failed('два * пять * шесть * один',2,10) : return
                if failed('два * пять ? шесть * один',-1,0) : return
                if failed('два * пять ? семь * один',2,10) : return
                if failed('три * три',-1,0) : return

                this.stopParsing(ANIMATION_ACCEPT)
                this.say('Поиск по шаблону работает')

            elif this.findWordChainB("проверка да или нет") :
                this.stopParsing(ANIMATION_ACCEPT)
                this.changeTopic( "YesNo", \
                    message='Да или нет?',
                    topicYes = TOPIC_DEBUG_YES,
                    topicNo = TOPIC_DEBUG_NO,
                    topicCancel = TOPIC_DEBUG_CANCEL
                )
    def onTopicChange( this, newTopic: str, params = {} ):
        if newTopic == TOPIC_DEBUG_YES :
            this.say( 'Подтверждено' )
            this.changeTopic(TOPIC_DEFAULT)
        elif newTopic == TOPIC_DEBUG_NO :
            this.say( 'отказано' )
            this.changeTopic(TOPIC_DEFAULT)
        elif newTopic == TOPIC_DEBUG_CANCEL :
            this.say( 'отмена' )
            this.changeTopic(TOPIC_DEFAULT)
