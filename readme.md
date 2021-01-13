# Lite Voice Terminal

### Disclaimer: "очень предварительная" версия в процессе разработки

Lite Voice Terminal is free open source client-server platform for powering up DIY offline "lite" smart speaker for Russian language.
“Lite” means lite speaker is built on hardware with limited computational power like RaspberryPi Zero / Zero W
"Offline" means voice recognition services are provided by on-premise ASR server.

Lite Voice Terminal это клиент-серверная платформа с открытым кодом для создания "легких" смарт колонок, 
не требующих использования онлайн-сервисов для распознавания голоса.

Под словом "легкий" понимаются минимальные требования к железу "умной" колонки, 
которая может быть реализована на Raspberry ZeroW или подобном одноплатном компьютере с достаточно 
чувствительным микрофоном и возможностью вывода звука

Распознавание голоса при этом выполняет установленный локально сервер. Предполагается, что сервер
на базе Intel Core i3 / 16Gb достаточен для поддержки до 10-20 терминалов.

### Возможности (реализованные и планируемые к реализации)

- [x] Клиент LVT может работать как под unix (RaspberryPi с микрофоном) так и на windows платформе
- [ ] Реализация LVT клиента на HTML/JScript 
- [x] Не требует использования внешних онлайн сервисов
- [x] Обмен между клиентской и серверной частью реализовано по протоколу websock с поддержкой SSL
- [x] Не требует специальной настройки голосовой активации (как snowboy), имя (несколько имен) ассистента 
просто указывюется в файле настройки. К имени же привязывается и голос ассистента (мужской/женский)
- [ ] Идентификация говорящего по голосу (работает только на достаточно длинных фразах, на текущий момент отключено)
- [x] Возможность расширения функций ассистента за счет написания своих модулей 
- [x] Распознавание с использованием либо БЕЗ использования словаря с возможностью переключаться между режимами на ходу. Я пока не решил окончательно, какой из режимов работает лучше...
- [x] Взаимодействие с устройствами по протоколу **MQTT**: на текущий момент работает только отправка сообщений
- [x] Интеграция в систему **MajorDoMo**: реализовано получение списка устройств через интеграционный php скрипт, после чего устройствами можно управлять непосредственно в LVT либо просто отправлять распознанные фразы для обработки в консоль МД)
- [ ] Ограниченная поддержка функций **MdmTerminal2**
- [x] Запуск сервера LVT на Unix
- [ ] Запуск сервера LVT на Windows
- [x] RHVoice TTS
- [ ] Windows TTS


### При реализации LVT использованы сторонние компоненты и модули:

* [kaldi](https://github.com/alphacep/kaldi): офлайн-распознавание речи
* [vosk API](https://github.com/alphacep/vosk-ap): программный интерфейс для kaldi
* [pymorphy2](https://github.com/kmike/pymorphy2): морфологический анализатор для русского и украинского языков
* [RHVoice](https://github.com/Olga-Yakovleva/RHVoice):  синтез голоса для русского языка
* [APA102](https://pypi.org/project/apa102): управление светодиодной лентой
* [WebRTC VAD](https://github.com/wiseman/py-webrtcvad): Определение наличия голоса во входном потоке
* [ReSpeaker components](https://github.com/respeaker): Взаимодействие с микрофоном и методы обработки звуков
* [mdmTerminal2](https://github.com/Aculeasis/mdmTerminal2): Много идей и кода позаимствовано из реализации голосового терминала MajorDoMo

### Документация
 * [Установка и настройка сервера LVT](https://github.com/mosave/LVTerminal/blob/master/docs/Configuration%20-%20Server.md)
 * [Установка и настройка терминала LVT](https://github.com/mosave/LVTerminal/blob/master/docs/Configuration%20-%20Terminal.md)
 * Примеры реализации терминалов
    * [Raspberry Pi3 A+ и Respeaker 4 MIC](https://github.com/mosave/LVTerminal/tree/master/hardware/RPi%203A%2B%20with%20Respeaker4/readme.md)
    * [Raspberry Pi ZeroW и Respeaker 4 MIC Linear Array](https://github.com/mosave/LVTerminal/tree/master/hardware/RPi%20Zero%20with%20Respeaker4%20Linear%20Array/readme.md)
    * [Raspberry Pi ZeroW и Respeaker 2 MIC](https://github.com/mosave/LVTerminal/tree/master/hardware/RPi%20Zero%20with%20Respeaker2/readme.md)
 * [Описание протокола LVT](https://github.com/mosave/LVTerminal/blob/master/docs/LVT%20-%20Protocol.md)
 * [Разработка скиллов (skill, навык)](https://github.com/mosave/LVTerminal/blob/master/docs/Skill%20-%20Development.md)
 * []()

## License

LVT is distributed under [LGPL v2.1](https://www.gnu.org/licenses/lgpl-2.1.html) or later.
Components and API used may be a subject of other licenses.

