import datetime
from lvt.const import *
from lvt.protocol import *
from lvt.server.grammar import *
from lvt.server.utterances import Utterances
from lvt.server.skill import Skill

TIMEOUT_VOLUME = 7

class ServerConfigSkill(Skill):
    """Управление режимами сервера.
    Ключевые фразы скилла: "Включи (выключи) режим распознавания со словарем"
    """
    def onLoad( self ):
        self.priority = 5000
        self.subscribe( TOPIC_DEFAULT )
        self.utterances = Utterances( self.terminal )
        self.utterances.add("update", "обнови [терминал, колонку]")
        self.utterances.add("reboot", "[перезагрузить, перезапустить, пере загрузи, пере запусти] [терминал, колонку]")


        self.utterances.add("volume:Up", "Сделай [терминал, колонку, динамик, звук, ] [немного,чуть, ] [громче,погромче]")
        self.utterances.add("volume:Down", "Сделай [терминал, колонку, динамик, звук, ] [немного,чуть, ] [тише, потише]")
        self.utterances.add("volume:Up", "увеличить громкость [звука, колонки, терминала, динамика]")
        self.utterances.add("volume:Down", "уменьшить громкость [звука, колонки, терминала, динамика]")

        self.utterances.add("volume:Set", "[установить, сделать, ] [громкость, звук] [терминала, колонки, динамика, звука, ] [на, в, ] volume=<number> процентов")

        self.utterances.add("plusVolume:Up", "[сделай, сделай еще, еще, ] [громче, погромче]")
        self.utterances.add("plusVolume:Down", "[сделай, сделай еще, еще, ] [тише, потише]")
        self.utterances.add("plusVolume:Set", "[установи, сделай, ] volume=<number> процентов")

        self.setVocabulary( TOPIC_DEFAULT, self.utterances.vocabulary )

        self.nextVersionCheck = datetime.datetime.now()
        self.plusVolumeThreshold = datetime.datetime.now()


    async def onTextAsync( self ):
        if self.topic == TOPIC_DEFAULT and self.isAppealed :
            matches = self.utterances.match(self.words)
            if len(matches)>0:
                if matches[0].id=='update':
                    await self.terminal.updateClient()
                    self.stopParsing()
                elif matches[0].id=='reboot':
                    await self.terminal.reboot("Перезагружаю терминал", "Терминал перезагружен")
                    self.stopParsing()
                elif matches[0].id.startswith('volume'):
                    await self.onVolumeCmd( matches[0].id, matches[0].values )
                    self.stopParsing()

        elif self.topic == TOPIC_DEFAULT:
            if datetime.datetime.now() < self.plusVolumeThreshold:
                matches = self.utterances.match(self.words)
                if (len(matches)>0) and matches[0].id.startswith('plusVolume'):
                    await self.onVolumeCmd( matches[0].id, matches[0].values )
                    self.stopParsing()
                else:
                    self.plusVolumeThreshold = datetime.datetime.now()

    async def onVolumeCmd(self, cmd, params ):
        try:
            volume = int(params["volume"]) if 'volume' in params else self.terminal.volume
        except Exception:
            volume = self.terminal.volume
        cmd = cmd.split(':')[1].lower()
        if cmd=='up':
            if volume>=100:
                await self.terminal.playAsync("asr_error.wav")
            volume += 10
            self.terminal.volume = volume if volume <=100 else 100
        elif cmd=='down':
            if volume<=20:
                await self.terminal.playAsync("asr_error.wav")

            volume -= 10
            self.terminal.volume = volume if volume >= 20 else 20
        elif cmd=='set':
            if volume>100:
                self.terminal.volume = 100
                await self.terminal.playAsync("asr_error.wav")
            elif volume<20:
                self.terminal.volume = 20
                await self.terminal.playAsync("asr_error.wav")
            else:
                self.terminal.volume = volume

        await self.terminal.sayAsync( f'{self.terminal.volume} [процент:{self.terminal.volume}]' )
        self.plusVolumeThreshold = datetime.datetime.now() + datetime.timedelta( seconds=10 )

    async def onTimerAsync( self ):
        if self.topic == TOPIC_DEFAULT and self.lastAppealed :
            if datetime.datetime.now() > self.lastAppealed + datetime.timedelta( seconds=10 ) \
                and datetime.datetime.now() > self.nextVersionCheck \
                and 8 <= datetime.datetime.now().hour <= 22 :

                self.nextVersionCheck = datetime.datetime.today() + datetime.timedelta( hours=32 )
                if self.terminal.clientVersion != VERSION :
                    if self.terminal.autoUpdate == 2 :
                        await self.terminal.updateClient()
                    if self.terminal.autoUpdate == 1 :
                        await self.sayAsync( 'Версия терминала устарела. Вы можете обновить его командой "Обновить терминал"' )

