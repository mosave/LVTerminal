import sys
import time
from lvt.const import *
from lvt.server.grammar import *
from lvt.server.skill import Skill

def YesNoParams( message: str, 
    topicYes: str, 
    topicNo: str, 
    topicCancel: str=None ) -> str:
    return  ( {
        'message':message,
        'topicYes':topicYes,
        'topicNo': topicNo,
        'topicCancel' : topicCancel
        } )

TOPIC_YES_NO = "YesNo"
TIMEOUT_REPEAT = 15
TIMEOUT_CANCEL = 30


#Define base skill class
class YesNoSkill(Skill):
    """ Проговорить сообщение, дождаться утрвердительного либо отрицательного ответа 
    и по результатам переключиться на один из предопредлеленных топиков.
    
    При вызове скилл должен получить dict со следующими параметрами:
        * message  : Вопрос, сформулированный таким образом, чтобы на него 
                     требовался положительный либо отрицательный ответ.
        * topicYes : топик, который будет выбран в случае положительного ответа
        * topicNo  : Топик для выбора в случае отрицательного ответа
        * topicCancel : Топик для выбора в случае если пользователь не ответил на вопрос

    Для формирования параметров можно использовать враппер YesNoParams
    
    """
    def onLoad( this ):
        this.priority = 100
        this.subscribe( TOPIC_YES_NO )
        this.extendVocabulary( "нет, не согласен, отказ, стой, отмена, отменить, не хочу, прекрати, не надо, не нужно" )
        this.extendVocabulary( "да, согласен, конечно, продолжить, уверен, поехали" )
        this.message = "вы уверены? Скажите да или нет"
        this.topicYes = ''
        this.topicNo = ''
        this.topicCancel = ''
        this.dtRepeat = time.time()
        this.dtCancel = time.time()

    def onText( this ):
        if this.topic != TOPIC_YES_NO : 
            return

        if this.topicCancel != '' and ( \
            this.findWordChainB( 'отменить' ) or \
            this.findWordChainB( 'отмена' ) ) :
            this.changeTopic( this.topicCancel,this.text )
            this.stopParsing( ANIMATION_CANCEL )
            return
        if this.findWordChainB( 'нет' ) or \
            this.findWordChainB( 'отмена' ) or \
            this.findWordChainB( 'не согласен' ) or \
            this.findWordChainB( 'отказ' ) or \
            this.findWordChainB( 'стой' ) or \
            this.findWordChainB( 'не уверен' ) or \
            this.findWordChainB( 'не нужно' ) :
            this.changeTopic( this.topicNo,this.text )
            this.stopParsing( ANIMATION_CANCEL )
            return
        if this.findWordChainB( 'да' ) or \
            this.findWordChainB( 'согласен' ) or \
            this.findWordChainB( 'продолжай' ) or \
            this.findWordChainB( 'конечно' ) or \
            this.findWordChainB( 'поехали' ) or \
            this.findWordChainB( 'уверен' ) :
            this.changeTopic( this.topicYes,this.text )
            this.stopParsing( ANIMATION_ACCEPT )
            return
        this.say('Извините, я не '+this.conformToAppeal('понял')+' что вы сказали. Скажите пожалуйста да или нет')
        this.stopParsing()

    def onPartialText( this ):
        if this.topic == TOPIC_YES_NO : 
            this.dtRepeat = time.time() + TIMEOUT_REPEAT
            this.dtCancel = time.time() + TIMEOUT_CANCEL

    def onTopicChange( this, newTopic: str, params={} ):
        if newTopic == TOPIC_YES_NO:
            this.dtRepeat = time.time() + TIMEOUT_REPEAT
            this.dtCancel = time.time() + TIMEOUT_CANCEL

            this.message = str( params['message'] ).strip() if 'message' in params else ''
            this.topicYes = str( params['topicYes'] ).strip() if 'topicYes' in params else ''
            this.topicNo = str( params['topicNo'] ).strip() if 'topicNo' in params else ''
            if 'topicCancel' in params and params['topicCancel']!=None :
                this.topicCancel = str( params['topicCancel'] ).strip() 
            else:
                this.topicCancel = ''
            this.defaultAnimation = this.terminal.lastAnimation

            if this.message == '' or this.topicYes == '' or this.topicNo == '' :
                this.say( "В скилл Yes Or No переданы неправильные значения параметров" )
                this.changeTopic( TOPIC_DEFAULT )
                this.stopParsing( ANIMATION_CANCEL )
                return

            this.animate( ANIMATION_AWAKE )
            this.say( this.message )
        else:
            this.terminal.animate( this.defaultAnimation )

    def onTimer( this ):
        if( this.topic == TOPIC_YES_NO ):
            if this.topicCancel!='' and time.time() > this.dtCancel :
                this.say('Извините, я так ничего и не услышала...')
                this.changeTopic( this.topicCancel, 'Ответ не получен' )
                return

            if time.time() > this.dtRepeat :
                this.dtRepeat = time.time() + TIMEOUT_REPEAT
                this.say(this.message)
                return
            
