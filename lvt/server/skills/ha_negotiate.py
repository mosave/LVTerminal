import time
from lvt.const import *
from lvt.server.grammar import *
from lvt.server.utterances import Utterances, isInteger
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

class HaNegotiateOption:
    def __init__(self, intent, say, data ):
        self.intent = intent
        self.say = say
        self.data = data

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
        self.dtRepeat = 0
        self.dtCancel = 0
        self.defaultIntent = None
        self.defaultTimeout = 30
        self.defaultSay = None
        self.defaultData = {}
        self.options = []
        self.utterances : Utterances = Utterances(self.terminal)


    async def onTopicChange( self, newTopic: str, params={} ):
        if newTopic == TOPIC_HA_NEGOTIATE:
            if "Say" not in params or params['Say'] is None:
                await self.sayAsync("Запуск диалога: стартовая фраза не задана")
                await self.changeTopicAsync(TOPIC_DEFAULT)
                return
            await self.sayAsync( params["Say"] )

            if "Options" not in params or not isinstance(params['Options'], list):
                await self.sayAsync("Ошибка. Не описаны варианты ответов")
                await self.changeTopicAsync(TOPIC_DEFAULT)
                return
            if "DefaultIntent" not in params or params['DefaultIntent'] is None:
                await self.sayAsync("Ошибка. Не задан параметр Default Intent")
                await self.changeTopicAsync(TOPIC_DEFAULT)
                return

            self.prompt = params["Prompt"] if "Prompt" in params else None # Фраза (список) - напоминание в процессе ожидания ответа

            self.utterances.clear()
            self.options.clear()
            i = 0
            for o in params['Options']:
                if not isinstance(o, dict):
                    await self.sayAsync(f"Ошибка. Неверное описание ответа {i+1}")
                    await self.changeTopicAsync(TOPIC_DEFAULT)
                    return
                elif 'Utterance' not in o:
                    await self.sayAsync(f"Ошибка. Не задан шаблон ключевой фразы (Utterance) для варианта {i+1}")
                    await self.changeTopicAsync(TOPIC_DEFAULT)
                    return
                utterances = o['Utterance'] if isinstance(o['Utterance'],list) else [str(o['Utterance'])]
                for u in utterances:
                    self.utterances.add( i, u )

                self.options.append(
                    HaNegotiateOption( 
                        o['Intent'] if 'Intent' in o else None, 
                        o['Say'] if 'Say' in o else None, 
                        o['Data'] if 'Data' in o else {} 
                   )
                )
                i += 1

            self.defaultIntent = params["DefaultIntent"] if "DefaultIntent" in params else None # Intent ID вызываеыый при истечении времени ожидания
            self.defaultTimeout = int(params["DefaultTimeout"]) if "DefaultTimeout" in params else 30 # Время ожидания ответа (в секундах)
            self.defaultSay = params["DefaultSay"] if "DefaultSay" in params else None # Фраза для проговаривания при истечении времени ожидания
            self.defaultData = params["DefaultData"] if "DefaultData" in params else {} # Дополнительные данные для DefaultEvent
            self.importance = params["Importance"] if "Importance" in params else 1 # Уровень важность. Передается обратно для поддержки диалогов со стороны HA

            du = params["DefaultUtterance"] if "DefaultUtterance" in params else None
            if bool(du):
                self.utterances.add( 'default', du )
            
            self.dtRepeat = time.time() + TIMEOUT_REPEAT
            self.dtCancel = time.time() + self.defaultTimeout

    async def onText( self ):
        if self.topic == TOPIC_HA_NEGOTIATE: 
            self.dtCancel = time.time() + self.defaultTimeout
            self.dtRepeat = time.time() + TIMEOUT_REPEAT
            matches = self.utterances.match(self.words)

            if len(matches)>0:
                m = matches[0]
                if isinstance(m.id, int):
                    option = self.options[m.id]
                    values = m.values
                    for name, value in option.data.items():
                        if (name not in values) or (values[name] is None):
                            values[name] = value
                    await self.fireIntentAsync( option.intent, option.say, values )
                elif str(m.id)=='default':
                    values = m.values
                    for name, value in self.defaultData.items():
                        if (name not in values) or (values[name] is None):
                            values[name] = value
                    await self.fireIntentAsync( self.defaultIntent, self.defaultSay, values )
                else:
                    await self.changeTopicAsync( TOPIC_DEFAULT )
                    self.stopParsing()


    async def onTimer( self ):
        if self.topic == TOPIC_HA_NEGOTIATE :
            if (self.dtCancel>0) and (time.time() > self.dtCancel) :
                await self.fireIntentAsync( self.defaultIntent, self.defaultSay, self.defaultData)
                return

            if (self.dtRepeat>0) and (time.time() > self.dtRepeat) :
                self.dtRepeat = time.time() + TIMEOUT_REPEAT
                if bool(self.prompt):
                    await self.sayAsync(self.prompt)
                return

    async def fireIntentAsync( self, intent, say, data ):
        self.dtCancel = 0
        self.dtRepeat = 0
        if bool(say):
            await self.sayAsync( say )

        if bool(intent):
            data = data if isinstance( data,dict) else {}
            fireIntent( intent, self.terminal.id, self.terminal.originalText, data)
        await self.changeTopicAsync( TOPIC_DEFAULT )
        self.stopParsing()

