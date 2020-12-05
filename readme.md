# Lite Voice Terminal

Lite Voice Terminal is free open source client-server platform for powering up DIY offline "light" smart speaker for Russian language.
“Lite” means lite speaker is built on hardware with limited computational power like RaspberryPi Zero / Zero W
"Offline" means voice recognition services are provided by on-premise ASR server.

**Lite Voice Terminal** это клиент-серверная платформа с открытым кодом для создания "легких" смарт колонок, 
не требующих использования онлайн-сервисов для распознавания голоса.

Под термином "легкий" в данном случае понимаются минимальные требования к железу самой колонки, 
которая может быть реализована на Raspberry Zero/ZeroW или подобном одноплатном компьютере.

Распознавание голоса при этом выполняет установленный локально сервер. Предполагается, что сервера на базе Intel Core i3 / 16Gb 
достаточен для поддержки до 10-20 терминалов.

### Возможности
* Не требует использования онлайн сервисов
* Обмен между клиентом и реализована через простой протокол поверх websock с поддержкой SSL
* Идентификация говорящего по голосу
* 
* Возможность расширения за счет написания своих модулей 
* Взаимодействие с устройствами по MQTT протоколу (?)
* Интеграция в MajorDoMo (?)

### LVT при работе использует следующие библиотеки:

* [kaldi](https://github.com/alphacep/kaldi): офлайн-распознавание речи
* [vosk API](https://github.com/alphacep/vosk-ap): программный интерфейс для kaldi
* [pymorphy2](https://github.com/kmike/pymorphy2): морфологический анализатор для русского и украинского языков
* [RHVoice](https://github.com/Olga-Yakovleva/RHVoice):  синтез голоса для русского языка



## License

LVT is distributed under [LGPL v2.1](https://www.gnu.org/licenses/lgpl-2.1.html) or later.
Components and API used may be a subject of other licenses.

