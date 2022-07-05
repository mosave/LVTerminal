import time
from lvt.const import *
from lvt.logger import logDebug
from lvt.protocol import MSG_API_FIRE_INTENT
from lvt.server.grammar import *
from lvt.server.utterances import Utterances
from lvt.server.skill import Skill
import lvt.server.api as api

TIMEOUT_REPEAT = 15

"""
Запуск режима распознавания речи без использования словаря HomeAssistantListenerSkill:

await terminal.changeTopicAsync( HA_LISTENER_SKILL,
    say: str, # Фраза (список) для проговаривания в начале диалога
    prompt: str, # Фраза (список) - напоминание в процессе ожидания ответа
    intent: str, # Intent ID, вызываемый при каждом распознаваниии фразы
    model: str, "full" или "dict", предпочитаемая модель для распознавания

    defaultIntent: str, # Intent ID вызываеыый при истечении времени ожидания
    defaultTimeout: int = 30, # Время ожидания ответа (в секундах)
    defaultSay: str = None # Фраза для проговаривания при истечении времени ожидания
)
"""


#Define base skill class
class HomeAssistantListenerSkill(Skill):
    """ Режим "несловарного" распознавания речи.
    """
    def onLoad( self ):
        self.priority = 400
        self.__intents = []
        self.subscribe( HA_LISTENER_SKILL )
        self.say = "Активирован режим прослушивания"
        self.prompt = "Активен режим прослушивания"
        self.intent = "ListenerStarted"
        self.defaultSay = None
        self.defaultIntent = None
        self.defaultTimeout = 30

    async def onTopicChangeAsync( self, newTopic: str, params={} ):
        if newTopic == HA_LISTENER_SKILL:
            self.terminal.useVocabulary = False

            if "Say" not in params or params['Say'] is None:
                await self.sayAsync("Распознавание без словаря: стартовая фраза не задана")
                await self.changeTopicAsync(TOPIC_DEFAULT)
                return
            if "Intent" not in params or params['Intent'] is None:
                await self.sayAsync("Распознавание без словаря: Intent не задан")
                await self.changeTopicAsync(TOPIC_DEFAULT)
                return

            await self.sayAsync( params["Say"] )

            self.intent = params["Intent"]
            self.prompt = params["Prompt"] if "Prompt" in params else "Режим прослушивания все еще активен" # Фраза (список) - напоминание в процессе ожидания ответа

            model = params["Model"] if "Model" in params else None # Intent ID вызываеыый при истечении времени ожидания
            self.terminal.preferFullModel = (model!="d")
            self.defaultIntent = params["DefaultIntent"] if "DefaultIntent" in params else None # Intent ID вызываеыый при истечении времени ожидания
            self.defaultTimeout = int(params["DefaultTimeout"]) if "DefaultTimeout" in params else 30 # Время ожидания ответа (в секундах)
            self.defaultSay = params["DefaultSay"] if "DefaultSay" in params else None # Фраза для проговаривания при истечении времени ожидания
            self.importance = params["Importance"] if "Importance" in params else 1 # Уровень важность. Передается обратно для поддержки диалогов со стороны HA

            self.dtRepeat = time.time() + TIMEOUT_REPEAT
            self.dtCancel = time.time() + self.defaultTimeout


    async def onTextAsync( self ):
        if self.topic == HA_LISTENER_SKILL :
            await self.fireIntentAsync( self.intent, None )
            self.dtRepeat = time.time() + TIMEOUT_REPEAT
            self.dtCancel = time.time() + self.defaultTimeout

    async def onTimerAsync( self ):
        if self.topic == HA_LISTENER_SKILL :
            if (self.dtCancel>0) and (time.time() > self.dtCancel) :
                if( self.defaultIntent is not None):
                    await self.fireIntentAsync( self.defaultIntent, self.defaultSay )
                self.dtRepeat = 0
                self.dtCancel = 0
                await self.changeTopicAsync(TOPIC_DEFAULT)
                return

            if (self.dtRepeat>0) and (time.time() > self.dtRepeat) :
                self.dtRepeat = time.time() + TIMEOUT_REPEAT
                if bool(self.prompt):
                    await self.sayAsync(self.prompt)
                return

    async def fireIntentAsync( self, intent, say ):
        if bool(say):
            await self.sayAsync( say )

        if bool(intent):
            data = {}
            data['importance'] = self.importance
            api.fireIntent( intent, self.terminal.id, self.terminal.originalText, data)

        self.stopParsing()
