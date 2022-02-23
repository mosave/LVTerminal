import time
from lvt.const import *
from lvt.server.grammar import *
from lvt.server.skill import Skill
from lvt.server.api import *

TIMEOUT_REPEAT = 15
TIMEOUT_CANCEL = 30

"""
Запуск диалога с HomeAssistantNegotiateSkill:

await terminal.changeTopicAsync( TOPIC_HA_NEGOTIATE,
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

#Define base skill class
class HomeAssistantNegotiateSkill(Skill):
    """ Реализация "Negotiation" и "Confirmation" диалогов для Home Assistant'а
    - проговорить сообщение
    - ожидать фразу-триггер, подтверждающие выбор одного из предопределенных вариантов. При ее получении - вызвать нужный intent и вернуться в основной топик
    - во время ожидания периодически проговаривать фразу-напоминание (если сконфигурировано
    - по истечении заданного периода вызвать intent "по умолчанию" и вернуться в основной топик
    """
    def onLoad( self ):
        self.priority = 0
        self.subscribe( TOPIC_HA_NEGOTIATE )
        self.dtRepeat = time.time()
        self.dtCancel = time.time()
        self.defaultIntent = None
        self.defaultTimeout = 30
        self.defaultSay = None
        self.defaultData = {}
        self.options = []


    async def onTopicChange( self, newTopic: str, params={} ):
        if newTopic == TOPIC_HA_NEGOTIATE:
            if "Say" not in params or params['Say'] is None:
                await self.sayAsync("Запуск диалога: не задана стартовая фраза")
                await self.changeTopicAsync(TOPIC_DEFAULT)
                return
            await self.sayAsync( params["Say"] )

            if "Options" not in params or not isinstance(params['Options'], list):
                await self.sayAsync("Ошибка. Не описаны варианты ответа")
                await self.changeTopicAsync(TOPIC_DEFAULT)
                return
            if "DefaultIntent" not in params or params['DefaultIntent'] is None:
                await self.sayAsync("Ошибка. Не задан параметр Default Intent")
                await self.changeTopicAsync(TOPIC_DEFAULT)
                return

            self.prompt = params["Prompt"] if "Prompt" in params else None # Фраза (список) - напоминание в процессе ожидания ответа

            self.options = []
            i = 0
            for option in params['Options']:
                i += 1
                if not isinstance(option, dict):
                    await self.sayAsync(f"Ошибка. Неверное описание ответа {i}")
                    await self.changeTopicAsync(TOPIC_DEFAULT)
                    return
                elif 'Utterance' not in option:
                    await self.sayAsync(f"Ошибка. Не задан Utterance для варианта {i}")
                    await self.changeTopicAsync(TOPIC_DEFAULT)
                    return
                self.options.append( {
                    'Intent' : option['Intent'] if 'Intent' in option else None,
                    'Utterance' : option['Utterance'] if isinstance(option['Utterance'],list) else [str(option['Utterance'])],
                    'Say' : option['Say'] if 'Say' in option else None,
                    'Data' : option['Data'] if 'Data' in option else {}
                })

            self.defaultIntent = params["DefaultIntent"] if "DefaultIntent" in params else None # Intent ID вызываеыый при истечении времени ожидания
            self.defaultTimeout = int(params["DefaultTimeout"]) if "DefaultTimeout" in params else 30 # Время ожидания ответа (в секундах)
            self.defaultSay = params["DefaultSay"] if "DefaultSay" in params else None # Фраза для проговаривания при истечении времени ожидания
            self.defaultData = params["DefaultData"] if "DefaultData" in params else {} # Дополнительные данные для DefaultEvent
            self.importance = params["Importance"] if "Importance" in params else 1 # Уровень важность. Передается обратно для поддержки диалогов со стороны HA
            self.dtRepeat = time.time() + TIMEOUT_REPEAT
            self.dtCancel = time.time() + self.defaultTimeout

    async def onText( self ):
        if self.topic == TOPIC_HA_NEGOTIATE: 
            for option in self.options:
                for u in option['Utterance']:
                    if self.findWordChainB( str(u) ):
                        await self.sayAsync( u['Say'] )
                        self.fireIntent( u['Intent'], u['Data'])
            self.stopParsing()

    async def onTimer( self ):
        if self.topic == TOPIC_HA_NEGOTIATE :
            if time.time() > self.dtCancel :
                if bool(self.defaultSay):
                    await self.sayAsync(self.defaultSay)
                await self.fireEventAsync( self.defaultIntent, self.defaultData)
                return

            if time.time() > self.dtRepeat :
                self.dtRepeat = time.time() + TIMEOUT_REPEAT
                if bool(self.prompt):
                    await self.sayAsync(self.prompt)
                return

    async def fireEventAsync( self, intent_type, intent_data ):
        if bool(intent_type):
            data = intent_data if isinstance( intent_data,dict) else {}
            fireIntent( intent_type, self.terminal.id, self.terminal.originalText, data)
        await self.changeTopicAsync( TOPIC_DEFAULT )
        self.stopParsing()

