import time
from lvt.const import *
from lvt.server.grammar import *
from lvt.server.utterances import Utterances, isInteger
from lvt.server.skill import Skill
import lvt.server.api as api

TIMEOUT_REPEAT = 40

"""
Запуск диалога с HomeAssistantNegotiateSkill:

await terminal.changeTopicAsync( HA_NEGOTIATE_SKILL,
        say: str, # Фраза (список) для проговаривания в начале диалога
        prompt: str, # Фраза (список) - напоминание в процессе ожидания ответа
        options, # описание вариантов возможных ответов в диалоге (см комментарии)
        defaultIntent: str, # Intent ID вызываеыый при истечении времени ожидания
        defaultTimeout: int = 30, # Время ожидания ответа (в секундах)
        defaultSay: str = None # Фраза для проговаривания при истечении времени ожидания
)
Описание параметра options:
        options: # описание вариантов ответов, массив:
        [
            {
                'Intent': 'OptionOneIntent', # Intent ID вызываеыый при выборе этого варианта ответа.
                'Utterance': # список шаблонов фраз-триггеров для первого варианта
                [
                    'я выбираю первый вариант',
                    'первый',
                ],
                'Say': 'вы выбрали первый вариант' # Фраза (список фраз) для подтверждения сделанного выбора
            },
            {
                'Intent': 'OptionTwoIntent', # Intent ID вызываеыый при выборе второго варианта ответа.
                'Utterance': список шаблонов фраз-триггеров для второго варианта
                [
                    'я выбираю второй вариант',
                    'второй вариант'
                    'второй',
                ],
                'Say': 'вы выбрали второй вариант' # фраза (список фраз) для подтверждения сделанного выбора
            },
        ]

"""

class HaNegotiateOption:
    def __init__(self, intent, say ):
        self.intent = intent
        self.say = say

#Define base skill class
class HomeAssistantNegotiateSkill(Skill):
    """ Реализация "Negotiation" и "Confirmation" диалогов для Home Assistant'а
    - проговорить сообщение
    - ожидать фразу-триггер, подтверждающие выбор одного из предопределенных вариантов. При ее получении - вызвать нужный intent и вернуться в основной топик
    - во время ожидания периодически проговаривать фразу-напоминание (если сконфигурировано
    - по истечении заданного периода вызвать intent "по умолчанию" и вернуться в основной топик
    """
    def onLoad( self ):
        self.priority = 500
        self.subscribe( HA_NEGOTIATE_SKILL )
        self.dtRepeat = 0
        self.dtCancel = 0
        self.defaultIntent = None
        self.defaultTimeout = 30
        self.defaultSay = None
        self.options = []
        self.utterances : Utterances = Utterances(self.terminal)


    async def onTopicChangeAsync( self, newTopic: str, params={} ):
        if newTopic == HA_NEGOTIATE_SKILL:
            self.terminal.volumeOverride = params["Volume"] if "Volume" in params else None

            if "Say" not in params or params['Say'] is None:
                await self.terminal.sayAsync("Запуск диалога: стартовая фраза не задана")
                await self.terminal.changeTopicAsync(TOPIC_DEFAULT)
                return
            await self.terminal.sayAsync( params["Say"] )

            if "Options" not in params or not isinstance(params['Options'], list):
                await self.terminal.sayAsync("Ошибка. Не описаны варианты ответов")
                await self.terminal.changeTopicAsync(TOPIC_DEFAULT)
                return


            self.prompt = params["Prompt"] if "Prompt" in params else None # Фраза (список) - напоминание в процессе ожидания ответа

            self.utterances.clear()
            self.options.clear()
            i = 0
            for o in params['Options']:
                if not isinstance(o, dict):
                    await self.terminal.sayAsync(f"Ошибка. Неверное описание ответа {i+1}")
                    await self.terminal.changeTopicAsync(TOPIC_DEFAULT)
                    return
                elif 'Utterance' not in o:
                    await self.terminal.sayAsync(f"Ошибка. Не задан шаблон ключевой фразы (Utterance) для варианта {i+1}")
                    await self.terminal.changeTopicAsync(TOPIC_DEFAULT)
                    return
                utterances = o['Utterance'] if isinstance(o['Utterance'],list) else [str(o['Utterance'])]
                for u in utterances:
                    self.utterances.add( i, u )

                self.options.append(
                    HaNegotiateOption( 
                        o['Intent'] if 'Intent' in o else None, 
                        o['Say'] if 'Say' in o else None, 
                   )
                )
                i += 1

            self.defaultIntent = params["DefaultIntent"] if "DefaultIntent" in params else None # Intent ID вызываеыый при истечении времени ожидания
            self.defaultTimeout = int(params["DefaultTimeout"]) if "DefaultTimeout" in params else 30 # Время ожидания ответа (в секундах)
            self.defaultSay = params["DefaultSay"] if "DefaultSay" in params else None # Фраза для проговаривания при истечении времени ожидания
            self.importance = params["Importance"] if "Importance" in params else 1 # Уровень важности. Передается обратно для поддержки диалогов со стороны HA

            du = params["DefaultUtterance"] if "DefaultUtterance" in params else None
            if bool(du):
                self.utterances.add( 'default', du )

            self.setVocabulary( HA_NEGOTIATE_SKILL, self.utterances.vocabulary )
            
            self.dtRepeat = time.time() + TIMEOUT_REPEAT
            self.dtCancel = time.time() + self.defaultTimeout

    async def onTextAsync( self ):
        if self.terminal.topic == HA_NEGOTIATE_SKILL: 
            self.dtCancel = time.time() + self.defaultTimeout
            self.dtRepeat = time.time() + TIMEOUT_REPEAT
            matches = self.utterances.match(self.words)

            if len(matches)>0:
                m = matches[0]
                if isinstance(m.id, int):
                    option = self.options[m.id]
                    await self.fireIntentAsync( option.intent, option.say, m.values )
                elif str(m.id)=='default':
                    await self.fireIntentAsync( self.defaultIntent, self.defaultSay, m.values )
                else:
                    await self.terminal.changeTopicAsync( TOPIC_DEFAULT )
                    self.stopParsing()


    async def onTimerAsync( self ):
        if self.terminal.topic == HA_NEGOTIATE_SKILL :
            if (self.dtCancel>0) and (time.time() > self.dtCancel) :
                if( self.defaultIntent is not None):
                    await self.fireIntentAsync( self.defaultIntent, self.defaultSay, None)
                return

            if (self.dtRepeat>0) and (time.time() > self.dtRepeat) :
                self.dtRepeat = time.time() + TIMEOUT_REPEAT
                if bool(self.prompt):
                    await self.terminal.sayAsync(self.prompt)
                return

    async def fireIntentAsync( self, intent, say, data ):
        self.dtCancel = 0
        self.dtRepeat = 0
        if bool(say):
            await self.terminal.sayAsync( say )

        if bool(intent):
            data = data if isinstance( data,dict) else {}
            data['importance'] = self.importance
            api.fireIntent( intent, self.terminal.id, self.terminal.originalText, data)
            
        await self.terminal.changeTopicAsync( TOPIC_DEFAULT )
        self.stopParsing()

