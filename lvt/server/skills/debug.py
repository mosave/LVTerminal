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
        this.priority = 5000
        this.extendVocabulary("проверка да или нет")
        this.subscribe( TOPIC_DEFAULT,  TOPIC_DEBUG_YES,TOPIC_DEBUG_NO, TOPIC_DEBUG_CANCEL,
                       TOPIC_DEBUG1,TOPIC_DEBUG2, TOPIC_DEBUG3, TOPIC_DEBUG4 )

    def onText( this ):
        if this.isAppealed :
            if this.findWordChain("проверка да или нет")>=0 :
                this.stopParsing(ANIMATION_ACCEPT)
                this.changeTopic( "YesNo", \
                    message='Да или нет?',
                    topicYes = TOPIC_DEBUG_YES,
                    topicNo = TOPIC_DEBUG_NO,
                    topicCancel = TOPIC_DEBUG_CANCEL
                )
        pass
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
