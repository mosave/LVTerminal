import sys
from lvt.const import *
from lvt.grammar import *
from lvt.config_parser import ConfigParser
from lvt.server.skill_factory import SkillFactory

config = None

class StateMachine:
    def setConfig( gConfig ):
        """Initialize module' config variable for easier access """
        global config
        config = gConfig

    def __init__( this, terminal ):
        # Именованные сущности (низкоуровневые алгоритмы):
        # https://yandex.ru/dev/dialogs/alice/doc/naming-entities.html
        # * Имя пользователя
        # * Расположение (справочник)
        # * Дата и время
        this.terminal = terminal
        this.currentState = 'idle'
        this.states = dict()
        this.states['idle'] = []
        this.skills = SkillFactory(terminal).loadAllSkills()
        this.traceLog = list()

    def onText( this, text: str, words: list(), final: bool, appeal: bool ):
        """Обработка распознанного текста
          * text - строка с распознанный текстом
          * words - список вариантов морфологического разбора для каждого слова из text
                    https://pymorphy2.readthedocs.io/en/stable/user/guide.html#id3
                    https://pymorphy2.readthedocs.io/en/stable/misc/api_reference.html#pymorphy2.analyzer.Parse
          * final: Окончательный вариант фразы (распознавание завершено)
          * appeal: во фразе обнаружено обращение к ассистенту
        """
        pass

    def onTimer( this ):
        pass

