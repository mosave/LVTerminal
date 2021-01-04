import sys
import time
import datetime
from lvt.const import *
from lvt.server.grammar import *
from lvt.server.skill import Skill

TOPIC_MD_REFRESH = "MDRefreshDevices"

#Define base skill class
class MajorDoMoSkill(Skill):
    """Скилл интеграции с MajorDoMo.
    Отправляет все распознанные но не обработанные фразы 
    на сервер MajorDoMo, если параметр
    config.mdSendRawCommands == True
    Кроме того при config.mdUseIntegrationScript == True
    В ответ на фразу "Обнови список устройств" вызывает
    * Какой сегодня день недели, какое число, какая дата
    """
    def onLoad( this ):
        this.priority = 1000
        this.subscribe( TOPIC_DEFAULT, TOPIC_MD_REFRESH )
        this.extendVocabulary('обновить список устройств')

    def onText( this ):
        if this.isAppealed :
            if this.findWordChainB('обновить список устройств'):
                this.changeTopic(TOPIC_MD_REFRESH)
                this.stopParsing(ANIMATION_THINK)
                thread = threading.Thread( target=this.httpGet, args=[this.url, this.user, this.password] )
                thread.daemon = False
                thread.start()

            else:
                this.stopParsing(ANIMATION_NONE)


    def onTopicChange( this, newTopic: str, params={} ):
        #if this.topic == TOPIC_MD_REFRESH:
        #    this.animate( ANIMATION_NONE )
        #    this.say( 'Устройства обновлены' )
        #elif newTopic==TOPIC:
        #    this.terminal.animate( this.lastAnimation )
        pass

    def onTimer( this ):
        if( this.topic == TOPIC_MD_REFRESH ):
            pass


    def httpGet( this, url, user, password ):
        try:
            if user and password :
                auth = requests.auth.HTTPBasicAuth( user, password )
            else :
                auth = None
            r = requests.get( url, auth=auth )
        except Exception as e:
            logError( f'HTTP GET("{url}","payload"): {e}' )
