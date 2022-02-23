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
    def onLoad( self ):
        self.priority = 0
        self.subscribe( TOPIC_YES_NO )
        self.extendVocabulary( "нет, не согласен, отказ, стой, отмена, отменить, не хочу, прекрати, не надо, не нужно" )
        self.extendVocabulary( "да, согласен, конечно, продолжить, уверен, поехали" )
        self.message = "вы уверены? Скажите да или нет"
        self.topicYes = ''
        self.topicNo = ''
        self.topicCancel = ''
        self.dtRepeat = time.time()
        self.dtCancel = time.time()

    async def onText( self ):
        if self.topic != TOPIC_YES_NO : 
            return

        if self.topicCancel != '' and ( \
            self.findWordChainB( 'отменить' ) or \
            self.findWordChainB( 'отмена' ) ) :
            await self.changeTopicAsync( self.topicCancel,self.terminal.text )
            self.stopParsing( ANIMATION_CANCEL )
            return
        if self.findWordChainB( 'нет' ) or \
            self.findWordChainB( 'отмена' ) or \
            self.findWordChainB( 'не согласен' ) or \
            self.findWordChainB( 'отказ' ) or \
            self.findWordChainB( 'стой' ) or \
            self.findWordChainB( 'не уверен' ) or \
            self.findWordChainB( 'не нужно' ) :
            await self.changeTopicAsync( self.topicNo,self.terminal.text )
            self.stopParsing( ANIMATION_CANCEL )
            return
        if self.findWordChainB( 'да' ) or \
            self.findWordChainB( 'согласен' ) or \
            self.findWordChainB( 'продолжай' ) or \
            self.findWordChainB( 'конечно' ) or \
            self.findWordChainB( 'поехали' ) or \
            self.findWordChainB( 'уверен' ) :
            await self.changeTopicAsync( self.topicYes,self.terminal.text )
            self.stopParsing( ANIMATION_ACCEPT )
            return
        await self.sayAsync('Извините, я не '+self.conformToAppeal('понял')+' что вы сказали. Скажите пожалуйста да или нет')
        self.stopParsing()

    async def onTopicChange( self, newTopic: str, params={} ):
        if newTopic == TOPIC_YES_NO:
            self.dtRepeat = time.time() + TIMEOUT_REPEAT
            self.dtCancel = time.time() + TIMEOUT_CANCEL

            self.message = str( params['message'] ).strip() if 'message' in params else ''
            self.topicYes = str( params['topicYes'] ).strip() if 'topicYes' in params else ''
            self.topicNo = str( params['topicNo'] ).strip() if 'topicNo' in params else ''
            if 'topicCancel' in params and params['topicCancel']!=None :
                self.topicCancel = str( params['topicCancel'] ).strip() 
            else:
                self.topicCancel = ''
            self.defaultAnimation = self.terminal.lastAnimation

            if self.message == '' or self.topicYes == '' or self.topicNo == '' :
                await self.sayAsync( "В скилл Yes Or No переданы неправильные значения параметров" )
                await self.changeTopicAsync( TOPIC_DEFAULT )
                self.stopParsing( ANIMATION_CANCEL )
                return

            self.animate( ANIMATION_AWAKE )
            await self.sayAsync( self.message )
        else:
            self.terminal.animate( self.defaultAnimation )

    async def onTimer( self ):
        if( self.topic == TOPIC_YES_NO ):
            if self.topicCancel!='' and time.time() > self.dtCancel :
                await self.sayAsync('Извините, я так ничего и не услышала...')
                await self.changeTopicAsync( self.topicCancel, 'Ответ не получен' )
                return

            if time.time() > self.dtRepeat :
                self.dtRepeat = time.time() + TIMEOUT_REPEAT
                await self.sayAsync(self.message)
                return
            
