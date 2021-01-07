import sys
import time
import datetime
from lvt.const import *
from lvt.server.grammar import *
from lvt.server.skill import Skill
from lvt.server.devices import Devices

#Define base skill class
class OnOffSkill(Skill):
    """Обработка фраз "включи что-нибудь" и "выключи что-нибудь".
    Действие производятся для каждой из названных локаций либо для локации терминала по умолчанию
    Подбор устройств для включения-выключения.
    1. Определяется действие: включить либо выключить
    2. Отфильтровываются устройства имеющие метод "on" или "off" соответственно
    3. Обрабатывается шаблон "[включи|выключи] все [тип или название устройства]"
    4. Иначе выполняются поиск устройства по названию
    5. Иначе при команде "включить" отбираются устройтва озвученного типа с признаком isDefault (такой будет хотя бы один)
    6. Иначе при команде "выключить" отбираются ВСЕ устройтва озвученного типа или названия
    """
    def onLoad( this ):
        this.priority = 3000
        this.subscribe( TOPIC_DEFAULT )
        this.extendVocabulary('включи выключи подключи отключи вруби выруби зажги погаси весь все полностью')

    def onText( this ):
        if not this.isAppealed : return
        turnOn = False
        ap = this.findWord('выключи')
        if ap<0 : ap = this.findWord('выключать')
        if ap<0 : ap = this.findWord('отключи')
        if ap<0 : ap = this.findWord('выруби')
        if ap<0 : ap = this.findWord('погаси')
        if ap<0 : 
            turnOn = True
            ap = this.findWord('включи')
        if ap<0 : ap = this.findWord('включать')
        if ap<0 : ap = this.findWord('подключи')
        if ap<0 : ap = this.findWord('вруби')
        if ap<0 : ap = this.findWord('зажги') >=0
        if ap<0 : return

        _text = this.text

        this.deleteWord(ap)
        this.replaceWordChain(this.appeal,'')
        this.replaceWordChain('эй','')
        this.replaceWordChain('слушай','')
        
        all = False
        if this.replaceWordChain('все','' ) : all = True
        if this.replaceWordChain('весь','' ) : all = True
        if this.replaceWordChain('полностью','' ) : all = True

        result = False
        for l in this.locations:
            location = this.entities.findLocation(l)
            if this.turnOnOff( location, turnOn, all ) : result = True

        if result :
            this.stopParsing(ANIMATION_ACCEPT)
        else :
            # restore original text if not processed:
            this.terminal.text = _text



    def turnOnOff( this, location: list, turnOn, all) -> bool:
        devices = Devices()
        devs = list()
        # Отфильтровать устройства по локации и наличию метода on/off
        for d in devices.devices.values() :
           if d.location not in location : continue
           if ('on' if turnOn else 'off') not in d.methods : continue
           devs.append(d)
        devsE = list()
        if all :
            #3. Обрабатывается шаблон "[включи|выключи] все [тип или название устройства]"
            for d in devs :
                names = d.type.names + d.names
                for s in names :
                    if this.findWordChainB(s) :
                        devsE.append(d)
                        break
        else:
            #4. Иначе выполняются поиск устройства по названию
            for d in devs :
                for s in d.names :
                    if this.findWordChainB(s) : 
                        devsE.append(d)
                        break
            if len(devsE)==0 and turnOn:
                #5. Иначе при команде "включить" отбираются устройтва озвученного типа с признаком isDefault (такой будет хотя бы один)
                for d in devs :
                    if d.isDefault :
                        for s in d.type.names :
                            if this.findWordChainB(s) :
                                devsE.append(d)
                                break
            if len(devsE)==0 and not turnOn:
                #6. Иначе при команде "выключить" отбираются ВСЕ устройтва озвученного типа или названия
                for d in devs :
                    names = d.type.names + d.names
                    for s in names :
                        if this.findWordChainB(s) :
                            devsE.append(d)
                            break
        if( len(devsE)<=0 ) :
            return False


        for d in devsE :
            d.methods['on' if turnOn else 'off'].execute()

        #s = [d.id for d in devsE]
        #print( f'{location}:  {("включаю" if turnOn else "выключаю ")} {s}')
        return True

