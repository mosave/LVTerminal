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
from lvt.server.terminal import *

# Timeout for LVT status updates to MajorDoMo
MD_STATUS_TIMEOUT = 60

#Define base skill class
class MajorDoMoSkill(Skill):
    """Скилл интеграции с MajorDoMo.
    Отправляет распознанные но не обработанные фразы на сервер MajorDoMo, если параметр
    config.mdSendRawCommands == True
    Кроме того в ответ на фразу "Обнови список устройств" заново загружает список устройств
    с сервера MajorDoMo (config.mdIntegration должен быть True)
    """
    def onLoad( this ):
        this.priority = 200
        this.subscribe( TOPIC_DEFAULT, TOPIC_MD_ASK, TOPIC_MD_YES, TOPIC_MD_NO, TOPIC_MD_CANCEL )
        this.waitUntil = 0
        this.usingVocabulary = this.terminal.usingVocabulary
        this.terminal.answerPrefix = ''
        this.lastStatusUpdate = 0
        this.lastStatusCheck = 0
        this.lastStatus=''

    def onText( this ):
        if (this.topic == TOPIC_MD_ASK) or \
           (this.isAppealed) and this.config.mdSendRawCommands:
                thread = threading.Thread( target=this.sendCommandToMD( this.originalText ) )
                thread.daemon = False
                thread.start()
                this.stopParsing(ANIMATION_ACCEPT)

    def onPartialText( this ):
        if this.topic == TOPIC_MD_ASK : 
            this.waitUntil = time.time() + WAIT_COMMAND_TIMEOUT

    def onTopicChange( this, newTopic: str, params={} ):
        if newTopic == TOPIC_MD_ASK :
            this.play( 'appeal_on.wav' )
            this.animate( ANIMATION_AWAKE )
            this.terminal.playAppealOffIfNotStopped = False
            this.usingVocabulary = this.terminal.usingVocabulary
            this.terminal.usingVocabulary = False
            this.waitUntil = time.time() + WAIT_COMMAND_TIMEOUT+10
        elif newTopic == TOPIC_MD_YES :
            thread = threading.Thread( target=this.sendCommandToMD( 'да' ) )
            thread.daemon = False
            thread.start()
            this.stopParsing(ANIMATION_ACCEPT)
            this.changeTopic( TOPIC_DEFAULT )
            pass
        elif newTopic == TOPIC_MD_NO :
            thread = threading.Thread( target=this.sendCommandToMD( 'нет' ) )
            thread.daemon = False
            thread.start()
            this.stopParsing(ANIMATION_ACCEPT)
            this.changeTopic( TOPIC_DEFAULT )
            pass
        elif newTopic == TOPIC_MD_CANCEL :
            thread = threading.Thread( target=this.sendCommandToMD( '' ) )
            thread.daemon = False
            thread.start()
            this.stopParsing(ANIMATION_CANCEL)
            this.changeTopic( TOPIC_DEFAULT )
            pass
        elif this.topic == TOPIC_MD_ASK :
            this.terminal.usingVocabulary = this.usingVocabulary
            this.waitUntil = 0

    def onTimer( this ):
        global terminals
        t = time.time()
        if (this.config.mdIntegration) and (t > this.lastStatusCheck + 10) :
            this.lastStatusCheck = t
            ts = dict()
            for terminal in terminals: ts[terminal.id] = terminal.isConnected
            ts = json.dumps(ts)

            if (ts != this.lastStatus) or (t > this.lastStatusUpdate + MD_STATUS_TIMEOUT) :
                this.lastStatusUpdate = t
                this.lastStatus = ts
                thread = threading.Thread( target=this.sendStatusToMD() )
                thread.daemon = False
                thread.start()


        if( this.topic == TOPIC_MD_ASK ):
            if t > this.waitUntil:
                this.terminal.playAppealOffIfNotStopped = False
                this.play( 'appeal_off.wav' )
                this.changeTopic( TOPIC_MD_CANCEL )


    def updateDevices( this ):
        try:
            Devices.loadMajorDoMoDevices()
            Devices.updateDefaultDevices()
            this.mdUpdateResult = 1
        except Exception as e:
            this.mdUpdateResult = 2

    def sendCommandToMD( this, commandText ):
        commandText = commandText.strip()
        if not commandText and not this.terminal.answerPrefix :
            return
        if this.terminal.answerPrefix:
            commandText = (this.terminal.answerPrefix+' '+commandText).strip()
        this.terminal.answerPrefix = ''

        try:
            if this.config.mdUser and this.config.mdPassword :
                auth = requests.auth.HTTPBasicAuth( this.config.mdUser, this.config.mdPassword )
            else :
                auth = None

            #log(f'Отправка команды в MajorDoMo: "{commandText}"')

            if False and this.config.mdIntegration :
                params = {"qry":commandText,'terminal':this.terminal.id }
                if this.terminal.speaker != None :
                    params['username'] = this.terminal.speaker.id
                url = urljoin( os.environ.get("BASE_URL", config.mdServer ), f'/lvt.php' )
                r = requests.post( url, data=params, auth=auth )
            else:
                params = {"qry":commandText,'terminal':this.terminal.id }
                if this.terminal.speaker != None :
                    params['username'] = this.terminal.speaker.id

                qry = urlencode(params)
                url = urljoin( os.environ.get("BASE_URL", config.mdServer ), f'/command.php?{qry}' )
                r = requests.get( url, auth=auth )

        except Exception as e:
            logError( f'HTTP GET("{url}","payload"): {e}' )


    def sendStatusToMD( this ):
        global terminals
        try:
            if this.config.mdUser and this.config.mdPassword :
                auth = requests.auth.HTTPBasicAuth( this.config.mdUser, this.config.mdPassword )
            else :
                auth = None

            status = json.dumps(Terminal.getLVTStatus())
            params = { 'cmd':'LVTStatus', 'status':status }

            url = urljoin( os.environ.get("BASE_URL", config.mdServer ), f'/lvt.php' )
            r = requests.post( url, data=params, auth=auth )

        except Exception as e:
            logError( f'HTTP GET("{url}","payload"): {e}' )

