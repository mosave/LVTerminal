import sys
import importlib
from lvt.const import *
from lvt.logger import *
from lvt.server.grammar import *

class Skill:
    """Базовый класс скиллов.
    Описания класса используются для автодокументирования возможностей ассистента.
    """
    def __init__( this, terminal, moduleFileName: str, name: str ):
        this.terminal = terminal
        this.moduleFileName = moduleFileName
        this.name = name
        this.enable = True
        this.subscriptions = set()
        this.vocabulary = set()
        # Чем выше значение приоритета, тем ближе к началу в цепочке
        # распознавания ставится скил
        this.priority = 0
        # Переход в новое состояние
        this.onLoad()

    def onLoad( this ):
        """Вызывается при инициализации скилла. 
        Обазательная конфигурация:
          * Состояния, к которым необходимо прибиндить скил
          * Ключевые слова, которые необходимо добавить в словарь фильтрации распознавалки в режиме "со словарем"
        """

        # Состояния, в которых скилл должен вызываться в при распозновании
        # фразы
        # this.subscribe( TOPIC_ALL )
        # this.subscribe( TOPIC_DEFAULT )
        # this.unsubscribe( TOPIC_DEFAULT )

        # this.extendVocabulary("список слов словаря", {'теги'})
        #
        #
        pass

    def onText( this ):
        """Вызывается после завершения распознавания фразы в случае если скилл привязан к текущему состоянию
          * appeal - в фразе присутствует обращение к ассистенту
        Возвращаемое значение, tuple:
        (<новое состояние>, <прервать дальнейшую обработку фразы> )
        """
        pass

    def onPartialText( this ):
        """Вызывается в процессе распознавания фразы если скилл привязан к текущему состоянию
          * text
          * appeal - в фразе присутствует обращение к ассистенту
        Возвращаемое значение, tuple:
        (<новое состояние>, <прервать дальнейшую обработку фразы> )
        """
        pass

    def onTopicChange( this, topic:str, newTopic: str ):
        """Вызывается при переходе синтаксического анализатора в состояние, на которое подписан скилл
        """
        pass
        
    def onTimer( this ):
        """Вызывается примерно 1 раз в секунду, в зависимости от """
        pass

    def getSkillFileName( this, ext: str ) -> str:
        """Generate skill-related file name by adding extension"""
        if not isinstance( ext,str ) :
            ext = ''
        elif not ext.startswith( '.' ):
            ext = '.' + ext
        # :)
        if ext == '.py': ext = '.py.dat'
        return os.path.splitext( moduleFileName )[0] + ext

### Terminal wrappers ##################################################################
#region
    @property
    def config( this ): return this.terminal.config
    @property
    def assistantNames( this ): return this.terminal.assistantNames
    @property
    def isAppealed( this ): return this.terminal.isAppealed
    @property
    def appealPos( this ): return this.terminal.appealPos
    @property
    def appeal( this ): return this.terminal.appeal
    @property
    def location( this ): return this.terminal.location

    @property
    def words( this ): return this.terminal.words
    @property
    def text( this ): return this.terminal.text
    @property
    def topic( this ): return this.terminal.topic

    def animate( this, animation:str, force:bool=False ): this.terminal.animate(animation, force)
    def say( this, text ): this.terminal.say( text )
    def play( this, waveFileName ): this.terminal.play( waveFileName )
    def log( this, msg:str ): log(f'[{this.terminal.name}:{this.name}]: {msg}')
    def logError( this, msg:str ): logError(f'[{this.terminal.name}:{this.name}]: {msg}')
    def logDebug( this, msg:str ): logDebug(f'[{this.terminal.name}:{this.name}]: {msg}')
#endregion

### Манипуляции словами и цепочками слов - поиск, удаление, подмена ####################
#region
    def getNormalFormOf( this, word: str, tags=None ) -> str:
        """Возвращает нормальную форму слова с учетом морфологических признаков"""
        parses = parseWord( word )
        for p in parses:
            if ( tags == None ) or tags in p.tag: 
                return p.normal_form
        return ''

    def getNormalForm( this, index: int, tags=None ) -> str:
        """Возвращает нормальную форму слова в фразе с учетом морфологических признаков"""
        for p in this.words[index]:
            if ( tags == None ) or tags in p.tag: 
               return p.normal_form
        return ''

    def isWord( this, index, word: str, tags=None ) -> bool:
        """Сравнение слова со словом в фразе с учетом морфологических признаков"""
        nf = this.getNormalFormOf( word, tags ) if word != None else None
        for p in this.terminal.words[index]:
            if ( tags == None or tags in p.tag ) and (nf==None or p.normal_form == nf): 
                return True
        return False

    def isInTag( this, index, tags ) -> bool:
        """Проверка соответствия слова в фразе морфологическим признакам"""
        for p in this.terminal.words[i]:
            if tags in p.tag: 
                return True
        return False

    def findWord( this, word: str, tags=None ) -> int:
        """Поиск в фразе слова с заданными морфологическими признаками"""
        nf = this.getNormalFormOf( word,tags )
        for index in range( len( this.terminal.words ) ):
            for p in this.terminal.words[index]:
                if ( tags == None or tags in p.tag ) and p.normal_form == nf: 
                    return index
        return -1

    def findWordChain( this, chain: str, startIndex: int=0 ) -> int:
        """Поиск в фразе цепочки слов"""

        cWords = wordsToList( chain )
        # Количество возможных положений цепочки в фразе (длина фразы-длина
        # цепочки)
        n = len( this.terminal.words ) - len( cWords ) - startIndex + 1
        # Проверить, достаточно ли слов в фразе
        if n < 1 : return -1

        for index in range( startIndex, n ):
            found = True
            for i in range( len( cWords ) ) :
                if not this.isWord( index + i, cWords[i] ) : 
                    found = False
                    break
            if found : return index

        return -1

    def deleteWord( this, index: int, wordsToDelete:int=1 ):
        """ Удаление одного или нескольких слов из фразы"""
        while wordsToDelete > 0 and index < len( this.terminal.words ):
           this.terminal.words.pop( index )
           wordsToDelete -= 1

    def insertWords( this, index:int, words: str ):
        """Вставить слово или цепочку слов в фразу"""
        words = wordsToList( words )

        for i in range( len( words ) ):
            p = parseWord( words[-i - 1] )
            # ?  do something with tags
            this.terminal.words.insert( index, p )

    def replaceWordChain( this, chain: str, replaceWithChain: str ) -> bool:
        """Найти в фразе цепочку слов chain и заменить ее на replaceWithChain """
        found = False
        while True:
            n = this.findWordChain( chain )
            if n >= 0:
                this.deleteWord( n, len( wordsToList( chain ) ) )
                this.insertWords( n, replaceWithChain )
                found = True
            else:
                break

        return found

#endregion

### Методы конфигурации скила и управление ходом разбора фразы #########################
#region
    def subscribe( this, topic:str ):
        """Привязать вызов process к состоянию"""
        this.subscriptions.add( str( topic ) )

    def unsubscribe( this, topic:str ):
        """Привязать вызов process к состоянию"""
        this.subscriptions.remove( str( topic ) )

    def isSubscribed( this, topic ):
        """Возвращает True если скилл подписан на Topic с учетом маски *, """
        topic = str( topic ).strip()
        for s in this.subscriptions:
            if s == "*" :return True
            ab = s.split( '*' )
            if len( ab ) == 1 and ab[0] == topic : return True
            if len( ab ) > 1 and topic.startswith( ab[0] ) and topic.endswith( ab[-1] ): return True

    def extendVocabulary( this, words, tags = None ):
        """Расширить словарь словоформами, удовлетворяющим тегам
        По умолчанию (tags = None) слова добавляется в том виде как они были переданы
        Принимает списки слов как в виде строк так и в виде массивов (рекурсивно)
        """
        this.vocabulary.update( wordsToVocabulary(words, tags) )

    def changeTopic( this, newTopic ):
        """Изменить текущий топик. Выполняется ПОСЛЕ выхода из обработчика onText/onPartialText"""
        this.terminal.newTopic = str( newTopic )

    def stopParsing( this ):
        """Прервать исполнение цепочки скиллов после выхода из обработчика onText/onPartialText"""
        this.terminal.parsingStopped = True

    def restartParsing( this ):
        """Прервать исполнение цепочки скиллов и перезапустить процесс анализа после выхода из обработчика onText/onPartialText"""
        this.terminal.parsingStopped = True
        this.terminal.parsingRestart = True
#endregion


