# Lite Voice Terminal

Lite Voice Terminal is free open source client-server platform for powering up DIY offline "lite" smart speaker for Russian language.
“Lite” means lite speaker is built on hardware with limited computational power like RaspberryPi Zero / Zero W
"Offline" means voice recognition services are provided by on-premise ASR server.

Lite Voice Terminal это клиент-серверная платформа с открытым кодом для создания "легких" смарт колонок, 
не требующих использования онлайн-сервисов для распознавания голоса.

Под словом "легкий" понимаются минимальные требования к железу самой колонки, 
которая может быть реализована на Raspberry Zero/ZeroW или подобном одноплатном компьютере с подключенным достаточно 
чувствительным микрофоном и возможностью вывода звука

Распознавание голоса при этом выполняет установленный локально сервер. Предполагается, что сервер
на базе Intel Core i3 / 16Gb достаточен для поддержки до 10-20 терминалов.

### Возможности (реализованные и планируемые к реализации)
* Не требует использования внешних онлайн сервисов
* Обмен между клиентской и серверной частью реализовано по протоколу websock с поддержкой SSL
* Идентификация говорящего по голосу
* Возможность расширения функций ассистента за счет написания своих модулей 
* Взаимодействие с устройствами по MQTT протоколу (?)
* Интеграция в MajorDoMo (?)

### При реализации LVT использованы сторонние компоненты и модули:

* [kaldi](https://github.com/alphacep/kaldi): офлайн-распознавание речи
* [vosk API](https://github.com/alphacep/vosk-ap): программный интерфейс для kaldi
* [pymorphy2](https://github.com/kmike/pymorphy2): морфологический анализатор для русского и украинского языков
* [RHVoice](https://github.com/Olga-Yakovleva/RHVoice):  синтез голоса для русского языка
* [APA102](https://pypi.org/project/apa102): управление светодиодной лентой
* [WebRTC VAD](https://github.com/wiseman/py-webrtcvad): Определение наличия голоса во входном потоке
* [ReSpeaker components](https://github.com/respeaker): Взаимодействие с микрофоном и методы обработки звуков
* [mdmTerminale](https://github.com/Aculeasis/mdmTerminal2): Много идей и кода позаимствовано из реализации голосового терминала MajorDoMo

## License

LVT is distributed under [LGPL v2.1](https://www.gnu.org/licenses/lgpl-2.1.html) or later.
Components and API used may be a subject of other licenses.

