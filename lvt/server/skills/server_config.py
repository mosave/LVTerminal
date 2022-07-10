import datetime
from lvt.const import *
from lvt.protocol import *
from lvt.server.grammar import *
from lvt.server.utterances import Utterances
from lvt.server.skill import Skill

# Как часто проверять версию терминала (раз в день?)
CHECK_VERSION_TIMEOUT = 60 * 60 * 24
# Время после последнего обращения, через которое будет выполнена проверка версии клиента
APPEAL_TIMEOUT = 5

#Define base skill class
class ServerConfigSkill(Skill):
    """Управление режимами сервера.
    Ключевые фразы скилла: "Включи (выключи) режим распознавания со словарем"
    """
    def onLoad( self ):
        self.priority = 5000
        self.subscribe( TOPIC_DEFAULT )
        self.utterances = Utterances( self.terminal )
        self.utterances.add("update", "обнови терминал")
        self.utterances.add("reboot", "[перезагрузить, перезапустить, пере загрузи, пере запусти] терминал")
        self.setVocabulary( TOPIC_DEFAULT, self.utterances.vocabulary )
        self.nextVersionCheckOn = datetime.datetime.now()

    async def onTextAsync( self ):
        if self.isAppealed :
            matches = self.utterances.match(self.words)
            if len(matches)>0:
                self.stopParsing()
                if matches[0].id == 'update':
                    await self.terminal.updateClient()
                else:
                    await self.terminal.reboot("Перезагружаю терминал", "Терминал перезагружен")

    async def onTimerAsync( self ):
        if self.topic == TOPIC_DEFAULT and self.lastAppealed :
            if datetime.datetime.now() > self.lastAppealed + datetime.timedelta( seconds=10 ) \
                and datetime.datetime.now() > self.nextVersionCheckOn \
                and 8 <= datetime.datetime.now().hour <= 22 :

                self.nextVersionCheckOn = datetime.datetime.today() + datetime.timedelta( hours=32 )
                if self.terminal.clientVersion != VERSION :
                    if self.terminal.autoUpdate == 2 :
                        await self.terminal.updateClient()
                    if self.terminal.autoUpdate == 1 :
                        await self.sayAsync( 'Версия терминала устарела. Вы можете обновить его командой "Обновить терминал"' )

