import sys
import time
from lvt.const import *
from lvt.server.grammar import *
from lvt.server.skill import Skill

TOPIC_DEBUG1 = "Debug1"
TOPIC_DEBUG2 = "Debug2"
TOPIC_DEBUG3 = "Debug3"
TOPIC_DEBUG4 = "Debug4"
TOPIC_DEBUG_CANCEL = "DebugCancel"
#Define base skill class
class DebugSkill(Skill):
    """Скилл для отладки"""
    def onLoad( self ):
        self.priority = 9000
        self.extendVocabulary("проверка да или нет")
        self.extendVocabulary("проверка поиска по шаблону")
        self.subscribe( TOPIC_DEFAULT,  TOPIC_DEBUG_CANCEL,
                       TOPIC_DEBUG1,TOPIC_DEBUG2, TOPIC_DEBUG3, TOPIC_DEBUG4 )

    async def onText( self ):
        if self.isAppealed :
            if self.findWordChainB("проверка поиска по шаблону") :
                async def failed( pattern, pos, len ) :
                    (p,l) = self.findWordChain( pattern )
                    if p != pos  or l != len :
                        await self.sayAsync(f'Ошибка при поиске {pattern}: ({p},{l})')
                        self.stopParsing(ANIMATION_CANCEL)
                        return True
                    else:
                        return False

                self.stopParsing(ANIMATION_ACCEPT)
                self.terminal.text = normalizeWords('ноль один два три четыре пять шесть семь восемь девять ноль один два')
                if await failed('два три четыре',2,3) : return
                if await failed('девять ноль один два три', -1, 0) : return
                if await failed('два три ? четыре', -1, 0) : return
                if await failed('два три ? пять', 2,4) : return
                if await failed('два три * четыре', 2,3) : return
                if await failed('два три * шесть', 2,5) : return
                if await failed('два * один',2,10) : return
                if await failed('два * пять * шесть * один',2,10) : return
                if await failed('два * пять ? шесть * один',-1,0) : return
                if await failed('два * пять ? семь * один',2,10) : return
                if await failed('три * три',-1,0) : return

                self.stopParsing(ANIMATION_ACCEPT)
                await self.sayAsync('Поиск по шаблону работает')

    async def onTopicChange( self, newTopic: str, params = {} ):
        # if newTopic == TOPIC_DEBUG_YES :
        #     await self.sayAsync( 'Подтверждено' )
        #     await self.changeTopicAsync(TOPIC_DEFAULT)
        # elif newTopic == TOPIC_DEBUG_NO :
        #     await self.sayAsync( 'отказано' )
        #     await self.changeTopicAsync(TOPIC_DEFAULT)
        # elif newTopic == TOPIC_DEBUG_CANCEL :
        #     await self.sayAsync( 'отмена' )
        #     await self.changeTopicAsync(TOPIC_DEFAULT)
        pass
