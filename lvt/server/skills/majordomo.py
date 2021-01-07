import sys
import time
import datetime
import threading
import requests
from urllib.parse import urljoin, urlencode
from lvt.const import *
from lvt.logger import *
from lvt.server.grammar import *
from lvt.server.skill import Skill
from lvt.server.devices import Devices

#Define base skill class
class MajorDoMoSkill(Skill):
    """Скилл интеграции с MajorDoMo.
    Отправляет распознанные но не обработанные фразы на сервер MajorDoMo, если параметр
    config.mdSendRawCommands == True
    Кроме того в ответ на фразу "Обнови список устройств" заново загружает список устройств
    с сервера MajorDoMo (config.mdIntegration должен быть True)
    """
    def onLoad( this ):
        this.priority = 100
        this.subscribe( TOPIC_DEFAULT )
        this.extendVocabulary('обновить список устройств')

    def onText( this ):
        if this.isAppealed :
            if this.config.mdSendRawCommands:
                thread = threading.Thread( target=this.sendRawCommand() )
                thread.daemon = False
                thread.start()
                this.stopParsing(ANIMATION_ACCEPT)



    def updateDevices( this ):
        try:
            Devices.loadMajorDoMoDevices()
            Devices.updateDefaultDevices()
            this.mdUpdateResult = 1
        except Exception as e:
            this.mdUpdateResult = 2

    def sendRawCommand( this ):
        try:
            if this.config.mdUser and this.config.mdPassword :
                auth = requests.auth.HTTPBasicAuth( this.config.mdUser, this.config.mdPassword )
            else :
                auth = None

            qry = urlencode({"qry":this.originalText })
            log(f'Отправка команды в MajorDoMo: "{this.terminal.originalText}"')

            url = urljoin( os.environ.get("BASE_URL", config.mdServer ), f'/command.php?{qry}' )
            r = requests.get( url, auth=auth )
        except Exception as e:
            logError( f'HTTP GET("{url}","payload"): {e}' )
