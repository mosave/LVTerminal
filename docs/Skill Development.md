# Lite Voice Terminal
## Разработка скиллов

### Общая структура
 * Модуль класса подгружается автоматически при инициализации загружке сервера
 * Экземпляр класса создается для каждого терминала-клиента в момент инициализации. При отключении клиента из памяти не выгружается.
 * Класс скилла должен наследоваться от базового класса Skill, имя класса так же дожно обязательно заканчиваться на Skill
 * Класс может иметь свою конфигурацию, которая хранится в общем файле конфигурации в разделе, совпадающем с названием класса.
   Каждый скилл имеет доступ к своей конфигурации через this.config (тип dict()).
 * После распознавания фразы полученный текст прогоняется через семантический анализатор, реализованный как
   последовательность "скиллов": небольших классов, выполняющих отдельные функции: обнаружение обращения к ассистенту,
   разворачивание акронимов, извлечение названий локаций или устройств, ответ на определенный вопрос и тд
 * Для фильтрации применяемой цепочки скиллов используется "топик" - контекст семантического анализатора. 
   Каждый скилл может подписаться на определенный набор топиков.


### События:

 * onLoad(): вызывается после создания экземпляра класса. Здесь выполняются все необходимые настройки и инициализация скилла
 * onText(): вызывается после завершения распознавания очередной фразы. Основной метод, реализующий логику скилла
 * onPartialText() - Вызывается в процессе распознавания фразы. Следует учитывать, что частично распознанный текст
   изменяется в процессе и может сильно отличаться от финальной версии.
   Перекрывать onPartialText() рекомендуется только в случае необходимости, поскольку это приводит к излишней загрузке системы.
 * onTimer() - вызывается по мере возможности, примерно раз в секунду. Использовать с аккуратностью, избегать блокировок.
 * onTopicChange( newTopic, params ): вызывается при изменении топика (контекст семантического анализатора)
   Вызывается только если скилл подписан на новый (newTopic) либо текущий (this.terminal.topic) топики
 

### Свойства базового класса Skill:
 * terminal
 * moduleFileName
 * name
 * config
 * cfg
 * subscriptions = set()
 * vocabulary = set()
 * priority - Чем выше значение приоритета, тем ближе к началу в цепочке
    распознавания ставится скил
 * isAppealed
 * appeal
 * appealPos
 * location
 * parsedLocations
 * entities
 * words
 * text
 * originalText
 * topic

### Методы базового класса Skill:
 * animate( this, animation:str )
 * say( this, text )
 * play( this, waveFileName )
 * log( this, msg:str )
 * logError( this, msg:str )
 * logDebug( this, msg:str )

 * getNormalFormOf( this, word: str, tags=None ) -> str:
 * getNormalForm( this, index: int, tags=None ) -> str:
 * conformToAppeal( this, word: str ) -> str:
 * isWord( this, index, word: str, tags=None ) -> bool:
 * isInTag( this, index, tags ) -> bool:
 * findWord( this, word: str, tags=None ) -> int:
 * findWordChain( this, chain: str, startIndex: int=0 ) :
 * findWordChainB( this, chain: str, startIndex: int=0 ) -> bool:
 * deleteWord( this, index: int, wordsToDelete:int=1 ):
 * insertWords( this, index:int, words: str ):
 * replaceWordChain( this, chain: str, replaceWithChain: str ) -> bool:
 * subscribe( this, *topics ):
 * unsubscribe( this, *topics ):
 * isSubscribed( this, topic ):
 * extendVocabulary( this, words, tags=None ):
 * changeTopic( this, newTopic, *params, **kwparams ):
 * stopParsing( this, animation: str=None ):
 * restartParsing( this ):

### Свойства терминала (this.terminal)
### Методы терминала (this.terminal)

