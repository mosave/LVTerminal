# Lite Voice Terminal
Free, open source, offline, DIY smart speaker platform oriented to **Russian language**.

### Disclaimer: "Второй подход к инструменту", версия в процессе разработки. Состояние "вроде что-то заработало"

Lite Voice Terminal это клиент-серверная платформа с открытым исходным кодом для создания "легких" смарт колонок,
не требующих использования онлайн-сервисов для распознавания голоса.

"Легкий" означает что смарт колонка (LVT клиент) может быть собрана на Raspberry Pi Zero или подобном маломощном одноплатном компьютере с достаточно 
чувствительным микрофоном и возможностью вывода звука.

Распознавание голоса и обработка команд выполняется на установленном в локальной сети [kaldi](https://github.com/alphacep/kaldi)/[vosk API](https://github.com/alphacep/vosk-api) сервере. В целом можно сказать что Intel Core i3 / 16Gb достаточно для обеспечения работы 10-20 терминалов, 
5-7 из которых могут одновременно поддерживать диалог с пользователем "в реальном времени".

Архитектура сервера LVT в целом предполагает расширение функциональности ассистента за счет отдельных модулей-скилов, однако реализация ориентирована в первую очередь на совместную работу с платформами автоматизации умного дома, таких как [Home Assistant](https://www.home-assistant.io/), для которого предусмотрен свой [модуль интеграции](https://github.com/mosave/LVT_HA)



Запланированные изменения:
 - Отказ от избыточной универсальности, поддержка только русского языка.
 - Упрощение и оптимизация серверной части
 - Интеграция с [Logitech Media Server (Squeezebox)](https://mysqueezebox.com/index/Home)) на уровне сервера.
 - Расширение протоколов управления LVT и разработка модуля интеграции с Home Assistant.
 - Оптимизация клиента LVT


### Возможности (реализованные и планируемые к реализации)

- [x] Клиент LVT может работать как под unix (RaspberryPi с микрофоном) так и на windows платформе
- [x] Не требует использования внешних онлайн сервисов
- [x] Обмен между клиентской и серверной частью реализовано по протоколу websock с поддержкой SSL
- [x] Не требует специальной настройки голосовой активации, имя (несколько имен) ассистента 
задается в файле настройки.
- [ ] Идентификация говорящего по голосу (работает только на достаточно длинных фразах, на текущий момент отключено)
- [x] Возможность расширения функций ассистента за счет написания своих модулей 
- [x] Совместная работа LVT клиента и squeezebox lite (плеер-клиент [Logitech Media Server](https://mysqueezebox.com/index/Home))
- [x] Интеграция в **Home Assistant**
- [x] Запуск сервера LVT на Unix
- [x] Запуск сервера LVT на Windows
- [x] RHVoice TTS
- [x] Windows TTS
- [ ] Docker-образ LVT сервера 


### При реализации LVT использованы сторонние компоненты и модули:

* [kaldi](https://github.com/alphacep/kaldi): офлайн-распознавание речи
* [vosk API](https://github.com/alphacep/vosk-api): программный интерфейс для kaldi
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
 * [Описание протокола LVT](https://github.com/mosave/LVTerminal/blob/master/docs/LVT%20Protocol.md)
 * [Разработка скиллов (skill, навык)](https://github.com/mosave/LVTerminal/blob/master/docs/Skill%20Development.md)
 * [Первая итерация проекта (ветка заморожена)](https://github.com/mosave/LVTerminal/tree/iteration0).

## License

LVT is distributed under [LGPL v2.1](https://www.gnu.org/licenses/lgpl-2.1.html) or later.
Components and API used may be a subject of other licenses.
