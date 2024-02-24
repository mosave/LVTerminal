from lvt.const import *
from lvt.logger import *
from lvt.server.grammar import *
import lvt.server.config as config
from lvt.server.entities import *
import lvt.server.terminal as terminals

class Skill:
    """Базовый класс скиллов
    Описания класса используются для автодокументирования возможностей ассистента.
    """
    def __init__( self, terminal, moduleFileName: str, name: str, cfg: dict ):
        self.terminal: terminals.Terminal = terminal
        self.moduleFileName = moduleFileName
        self.name = name
        self.cfg = cfg
        self.subscriptions = set()
        self.__vocabulary : dict( str, set() ) = {}
        # Чем выше значение приоритета, тем ближе к началу в цепочке
        # распознавания ставится скил
        self.priority = 0
        # Переход в новое состояние
        self.onLoad()

    def onLoad( self ):
        """Вызывается при инициализации скилла. 
        Обазательная конфигурация:
          * Топики, к которым необходимо подписать скил
          * Словарь, используемый при распознавании в режиме "со словарем" для каждого топика
        """

        # Состояния, в которых скилл должен вызываться в при распозновании
        # фразы
        # self.subscribe( TOPIC_ALL )
        # self.subscribe( TOPIC_DEFAULT )
        # self.unsubscribe( TOPIC_DEFAULT )

        # self.setVocabulary(TOPIC_DEFAULT, "список слов словаря")
        pass

    async def onTextAsync( self ):
        """Вызывается после завершения распознавания фразы в случае если скилл привязан к текущему состоянию
          * appeal - в фразе присутствует обращение к ассистенту
        """
        pass

    async def onTopicChangeAsync( self, newTopic:str, params={} ):
        """Вызывается при переходе синтаксического анализатора в состояние, на которое подписан скилл
        """
        pass
        
    async def onTimerAsync( self ):
        """Вызывается примерно 1 раз в секунду, в зависимости от """
        pass

#region Terminal wrappers #############################################################
    @property
    def words( self ): return self.terminal.words
    @property
    def text( self ) -> str: return self.terminal.text
    @property
    def originalText( self ) -> str: return self.terminal.originalText

    def log( self, msg:str ): log( f'[{self.terminal.id}.{self.name}]: {msg}' )
    def logError( self, msg:str ): logError( f'[{self.terminal.id}.{self.name}]: {msg}' )
    def logDebug( self, msg:str ): logDebug( f'[{self.terminal.id}.{self.name}]: {msg}' )
#endregion

#region Манипуляции словами и цепочками слов - поиск, удаление, подмена ###############
    def getNormalForm( self, index: int, tags=None ) -> str:
        """Возвращает нормальную форму слова в фразе с учетом морфологических признаков"""
        for p in self.words[index]:
            if ( tags is None ) or tags in p.tag: 
               return p.normal_form#.replace( 'ё', 'e' )
        return ''

    def isWord( self, index, word: str, tags=None ) -> bool:
        """Сравнение слова со словом в фразе с учетом морфологических признаков"""
        if word is None or not isinstance( word, str ) : return False

        nf = normalFormOf( word, tags )
        for p in self.terminal.words[index]:
            #if ( tags is None or tags in p.tag ) and ( p.normal_form.replace( 'ё', 'e' ) == nf ): 
            if ( tags is None or tags in p.tag ) and ( p.normal_form == nf ): 
                return True
        return False

    def isInTag( self, index, tags ) -> bool:
        """Проверка соответствия слова в фразе морфологическим признакам"""
        for p in self.terminal.words[p]:
            if tags in p.tag: 
                return True
        return False

    def findWord( self, word: str, tags=None ) -> int:
        """Поиск в фразе слова с заданными морфологическими признаками"""
        nf = normalFormOf( word,tags )
        for index in range( len( self.terminal.words ) ):
            for p in self.terminal.words[index]:
                #if ( tags is None or tags in p.tag ) and p.normal_form.replace( 'ё', 'e' ) == nf: 
                if ( tags is None or tags in p.tag ) and p.normal_form == nf: 
                    return index
        return -1

    def findWordChain( self, chain: str, startIndex: int=0 ) :
        """Поиск в фразе цепочки слов по шаблону
       Возвращает индекс первого слова в цепочке и длину
       Поддерживаемые шаблоны: 
       ? - одно любое слово
       * - ноль или больше любых слов
       """

        cWords = wordsToList( chain )
        txt = wordsToList(self.terminal.text)
        lenW = len( self.terminal.words )
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
                    (p,l) = self.findWordChain( ' '.join( cWords[iCW:] ), iW )
                    if p<0 : found = False
                    iW = p+l
                    iCW = lenCW
                    break
                elif cWords[iCW] == '?' :
                    iW += 1
                    iCW += 1
                elif self.isWord( iW, cWords[iCW] ) : 
                    iW += 1
                    iCW += 1
                else :
                    found = False
                    break
            if found and iCW == lenCW : 
                return (index,iW - index)

        return (-1, 0)

    def findWordChainB( self, chain: str, startIndex: int=0 ) -> bool:
        """Поиск в фразе цепочки слов по шаблону
        Возвращает True если цепочка найдена в 
        Поддерживаемые шаблоны: 
        ? - одно любое слово
        * - ноль или больше любых слов
        """
        (start, len) = self.findWordChain( chain, startIndex )
        return ( start >= 0 )

    def deleteWord( self, index: int, wordsToDelete:int=1 ):
        """ Удаление одного или нескольких слов из фразы"""
        while wordsToDelete > 0 and index < len( self.terminal.words ):
           self.terminal.words.pop( index )
           wordsToDelete -= 1

    def insertWords( self, index:int, words: str ):
        """Вставить слово или цепочку слов в фразу"""
        words = wordsToList( words )

        for i in range( len( words ) ):
            p = parseWord( words[-i - 1] )
            # ?  do something with tags
            self.terminal.words.insert( index, p )

    def replaceWordChain( self, chain: str, replaceWithChain: str ) -> bool:
        """Найти в фразе цепочку слов chain и заменить ее на replaceWithChain """
        found = False
        while True:
            (p,l) = self.findWordChain( chain )
            if p >= 0:
                self.deleteWord( p, l )
                self.insertWords( p, replaceWithChain )
                found = True
            else:
                break

        return found

#endregion

#region Методы конфигурации скила и управление ходом разбора фразы ####################
    def subscribe( self, *topics ):
        """Привязать вызов process к состоянию"""
        for t in topics : self.subscriptions.add( str( t ) )

    def unsubscribe( self, *topics ):
        """Привязать вызов process к состоянию"""
        for t in topics : self.remove( str( t ) )

    def isSubscribed( self, topic ):
        """Возвращает True если скилл подписан на Topic с учетом маски *, """
        topic = str( topic ).strip()
        for s in self.subscriptions:
            if s == "*" :return True
            ab = s.split( '*' )
            if len( ab ) == 1 and ab[0] == topic : return True
            if len( ab ) > 1 and topic.startswith( ab[0] ) and topic.endswith( ab[-1] ): return True

    def setVocabulary( self, topic:str, vocabulary: set ):
        self.__vocabulary[topic] = wordsToVocabulary( vocabulary )

    def getVocabulary( self, topic:str ):
        if topic == TOPIC_ALL:
            vocabulary = set()
            for ( t, v) in self.__vocabulary:
               vocabulary.update( v )
        else:
            vocabulary = self.__vocabulary[topic] if topic in self.__vocabulary else set()

        return vocabulary

    def stopParsing( self ):
        """Прервать исполнение цепочки скиллов после выхода из обработчика onText"""
        self.terminal.parsingStopped = True

    def restartParsing( self ):
        """Прервать исполнение цепочки скиллов и перезапустить процесс анализа после выхода из обработчика onText"""
        self.terminal.parsingStopped = True
        self.terminal.parsingRestart = True
#endregion


