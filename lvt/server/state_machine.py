import sys
from lvt.const import *
from lvt.grammar import *
from lvt.server.skill_factory import SkillFactory

class StateMachine:
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

    def processText( this, text: str, final: bool ):
        pass


