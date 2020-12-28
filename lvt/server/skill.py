import sys
import importlib
from lvt.const import *
from lvt.logger import *
from lvt.server.grammar import *

class Skill:
    """Базовый класс скиллов
    Описания класса используются для автодокументирования возможностей ассистента.
    """
    def __init__( this, terminal, moduleFileName: str, name: str, cfg: dict ):
        this.terminal = terminal
        this.moduleFileName = moduleFileName
        this.name = name
        this.config = cfg
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

    def onTopicChange( this, newTopic:str, params={} ):
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
    def isAppealed( this ): return this.terminal.isAppealed
    @property
    def appealPos( this ): return this.terminal.appealPos
    @property
    def appeal( this ): return this.terminal.appeal
    @property
    def location( this ): return this.terminal.location
    @property
    def entities( this ): return this.terminal.entities

    @property
    def words( this ): return this.terminal.words
    @property
    def text( this ): return this.terminal.text
    @property
    def topic( this ): return this.terminal.topic

    def animate( this, animation:str ): this.terminal.animate( animation )
    def say( this, text ): this.terminal.say( text )
    def play( this, waveFileName ): this.terminal.play( waveFileName )
    def log( this, msg:str ): log( f'[{this.terminal.name}:{this.name}]: {msg}' )
    def logError( this, msg:str ): logError( f'[{this.terminal.name}:{this.name}]: {msg}' )
    def logDebug( this, msg:str ): logDebug( f'[{this.terminal.name}:{this.name}]: {msg}' )
#endregion

### Манипуляции словами и цепочками слов - поиск, удаление, подмена ####################
#region
    def getNormalFormOf( this, word: str, tags=None ) -> str:
        """Возвращает нормальную форму слова с учетом морфологических признаков"""
        parses = parseWord( word )
        for p in parses:
            if ( tags == None ) or tags in p.tag: 
                return p.normal_form.replace( 'ё', 'e' )
        return ''

    def getNormalForm( this, index: int, tags=None ) -> str:
        """Возвращает нормальную форму слова в фразе с учетом морфологических признаков"""
        for p in this.words[index]:
            if ( tags == None ) or tags in p.tag: 
               return p.normal_form.replace( 'ё', 'e' )
        return ''

    def conformToAppeal( this, word: str ) -> str:
        """Согласовать слово с обращением (мужской-женский-средний род)"""
        parse = parseWord( word )[0]
        gender = parseWord( this.terminal.appeal )[0].tag.gender
        return parse.inflect( {gender} ).word

    def isWord( this, index, word: str, tags=None ) -> bool:
        """Сравнение слова со словом в фразе с учетом морфологических признаков"""
        if word == None or not isinstance( word, str ) : return False

        nf = this.getNormalFormOf( word, tags )
        for p in this.terminal.words[index]:
            if ( tags == None or tags in p.tag ) and ( p.normal_form.replace( 'ё', 'e' ) == nf ): 
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
                if ( tags == None or tags in p.tag ) and p.normal_form.replace( 'ё', 'e' ) == nf: 
                    return index
        return -1

    def findWordChain( this, chain: str, startIndex: int=0 ) :
        """Поиск в фразе цепочки слов по шаблону
       Возвращает индекс первого слова в цепочке и длину
       Поддерживаемые шаблоны: 
       ? - одно любое слово
       * - ноль или больше любых слов
       """

        cWords = wordsToList( chain )
        txt = wordsToList(this.terminal.text)
        lenW = len( this.terminal.words )
        lenCW = len( cWords )
        if lenW<=0 : return(-1,0)
        if lenCW<=0 : return(startIndex,0)

        for index in range( startIndex, lenW ):
            found = True
            iW = index
            iCW = 0
            while iCW < lenCW :
                if iW >= lenW :
                    return(-1, 0)
                elif cWords[iCW] == '*' :
                    iCW += 1
                    (p,l) = this.findWordChain( ' '.join( cWords[iCW:] ), iW )
                    if p<0 : found = False
                    iW = p+l
                    iCW = lenCW
                    break
                elif cWords[iCW] == '?' :
                    iW += 1
                    iCW += 1
                elif this.isWord( iW, cWords[iCW] ) : 
                    iW += 1
                    iCW += 1
                else :
                    found = False
                    break
            if found and iCW == lenCW : 
                return (index,iW - index)

        return (-1, 0)

    def findWordChainB( this, chain: str, startIndex: int=0 ) -> bool:
        """Поиск в фразе цепочки слов по шаблону
        Возвращает True если цепочка найдена в 
        Поддерживаемые шаблоны: 
        ? - одно любое слово
        * - ноль или больше любых слов
        """
        (start, len) = this.findWordChain( chain, startIndex )
        return ( start >= 0 )

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
            (p,l) = this.findWordChain( chain )
            if p >= 0:
                this.deleteWord( p, l )
                this.insertWords( p, replaceWithChain )
                found = True
            else:
                break

        return found

#endregion

### Методы конфигурации скила и управление ходом разбора фразы #########################
#region
    def subscribe( this, *topics ):
        """Привязать вызов process к состоянию"""
        for t in topics : this.subscriptions.add( str( t ) )

    def unsubscribe( this, *topics ):
        """Привязать вызов process к состоянию"""
        for t in topics : this.remove( str( t ) )

    def isSubscribed( this, topic ):
        """Возвращает True если скилл подписан на Topic с учетом маски *, """
        topic = str( topic ).strip()
        for s in this.subscriptions:
            if s == "*" :return True
            ab = s.split( '*' )
            if len( ab ) == 1 and ab[0] == topic : return True
            if len( ab ) > 1 and topic.startswith( ab[0] ) and topic.endswith( ab[-1] ): return True

    def extendVocabulary( this, words, tags=None ):
        """Расширить словарь словоформами, удовлетворяющим тегам
        По умолчанию (tags = None) слова добавляется в том виде как они были переданы
        Принимает списки слов как в виде строк так и в виде массивов (рекурсивно)
        """
        this.vocabulary.update( wordsToVocabulary( words, tags ) )

    def changeTopic( this, newTopic, *params, **kwparams ):
        """Изменить текущий топик. Выполняется ПОСЛЕ выхода из обработчика onText/onPartialText"""
        this.terminal.newTopic = str( newTopic )

        p = kwparams
        if len( params ) == 1 and isinstance( params[0],dict ) : 
            p.update( params[0] )
        elif len( params ) > 0 : 
            p.update( {'params':params} )
        this.terminal.newTopicParams = p
        this.terminal.logDebug( f'{this.name}.changeTopic("{newTopic}", {p}) ]' )

    def stopParsing( this, animation: str=None ):
        """Прервать исполнение цепочки скиллов после выхода из обработчика onText/onPartialText"""
        if animation != None : 
            this.terminal.animate( ANIMATION_NONE )
            this.terminal.animate( animation )
        this.terminal.parsingStopped = True

    def restartParsing( this ):
        """Прервать исполнение цепочки скиллов и перезапустить процесс анализа после выхода из обработчика onText/onPartialText"""
        this.terminal.parsingStopped = True
        this.terminal.parsingRestart = True
#endregion


