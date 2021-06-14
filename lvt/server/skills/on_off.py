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
    4. Иначе при команде "включить" :
        4.1 Выполняются поиск устройства по названию
        4.2 Иначе отбираются устройтва озвученного типа с признаком isDefault (такой будет хотя бы один)
    5. Иначе при команде "выключить"
        5.1 Иначе отбираются ВСЕ устройтва озвученного типа либо названия
        //5.1 Выполняются поиск устройства по названию
        //5.2 Иначе отбираются ВСЕ устройтва озвученного типа
    """
    def onLoad( this ):
        this.priority = 3000
        this.subscribe( TOPIC_DEFAULT )
        this.extendVocabulary('включи выключи подключи отключи зажги погаси весь все полностью')

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
            this.terminal.text = ''
            this.stopParsing(ANIMATION_ACCEPT)
            this.say('Включаю!' if turnOn else 'Выключаю!')
        else :
            # restore original text if not processed:
            this.terminal.text = _text



    def turnOnOff( this, location: str, turnOn, all) -> bool:
        devices = Devices()
        devs = list()
        this.logDebug(f'{location}')
        # Отфильтровать устройства по локации и наличию метода on/off
        for d in devices.devices.values() :
           if d.location!=None and location not in d.location : continue
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
            #print(f'#3: {len(devsE)}')
        #4. Иначе при команде "включить":
        if len(devsE)==0 and turnOn:
            # 4.1 Выполняются поиск устройства по названию
            for d in devs :
                for s in d.names :
                    if this.findWordChainB(s) : 
                        devsE.append(d)
                        break # in d.names
            #print(f'#4.1: {len(devsE)}')

            # 4.2 Иначе отбираются устройтва озвученного типа с признаком isDefault 
            # Такой будет хотя бы один для каждого типа
            if len(devsE)==0:
                for d in devs :
                    if d.isDefault :
                        for s in d.type.names :
                            if this.findWordChainB(s) :
                                devsE.append(d)
                                break # in d.type.names
            #print(f'#4.2: {len(devsE)}')

        #

        # 5.1 Иначе при команде "выключить" отбираются устройтва по названию
        if len(devsE)==0 and not turnOn:
            #for d in devs :
            #    for s in d.names :
            #        if this.findWordChainB(s) : 
            #            devsE.append(d)
            #            break # in d.names
            ##print(f'#5.1: {len(devsE)}')

            # 5.1 Иначе при команде "выключить" отбираются ВСЕ устройтва озвученного типа лбо названия
            if len(devsE)==0:
                for d in devs :
                    names = d.type.names + d.names
                    for s in names : #d.type.names :
                        if this.findWordChainB(s) :
                            devsE.append(d)
                            break # in names
                #print(f'#5.2: {len(devsE)}')

        # Ни одного устройства не подобрано - возвращаем false
        if( len(devsE)<=0 ) :
            return False

        # Найдено одно или больше устройств - выполнфем действие:
        for d in devsE :
            d.methods['on' if turnOn else 'off'].execute()

        #s = [d.id for d in devsE]
        #print( f'{location}:  {("включаю" if turnOn else "выключаю ")} {s}')
        return True

