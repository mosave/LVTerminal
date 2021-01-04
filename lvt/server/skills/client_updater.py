import sys
import time
from lvt.const import *
from lvt.server.grammar import *
from lvt.server.skill import Skill

#Define base skill class
class ClientUpdaterSkill(Skill):
    """Раз в день проверяет версию терминального клиента
    Если версия уже устарела, то предлагает обновить терминал
    
    """
    def onLoad( this ):
        this.priority = 500
        this.subscribe( TOPIC_DEFAULT )

    def onText( this ):
        pass
