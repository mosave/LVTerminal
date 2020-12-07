import sys
import importlib
from lvt.const import *
from lvt.server.grammar import *

#Define base skill class
class Skill:
    def __init__( this, terminal, moduleFileName: str, name: str ):
        this.terminal = terminal
        this.moduleFileName = moduleFileName
        this.name = name

        this.enable = True
        this.subscriptions = set()
        # Список слов (через пробел), которые необходимо добавить в фильтр
        # распозновалки для работы этого скила
        this.vocabulary = ''
        # Чем выше значение приоритета, тем ближе к началу в цепочке
        # распознавания ставится скил
        this.priority = 0
        # Переход в новое состояние
        this.onLoad()

    def onLoad( this ):
        """Вызывается при инициализации скилла. 
        Обазательная конфигурация:
          * Состояния, к которым необходимо прибиндить скил
          * Ключевые слова, которые необходимо добавить в словарь фильтрации распознавалки
        """

        # Состояния, в которых скилл должен вызываться в при распозновании
        # фразы
        # subscribe( TOPIC_ALL )
        # subscribe( TOPIC_DEFAULT )
        # unsubscribe( TOPIC_DEFAULT )
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
# Terminal wrappers
#region
    @property
    def config( this ): return this.terminal.getConfig()
    @property
    def morphy( this ): return this.terminal.morphy
    @property
    def assistantNames( this ): return this.terminal.assistantNames
    @property
    def isAppealed( this ): return this.terminal.appealPos!=None
    @property
    def appealPos( this ): return this.terminal.appealPos
    @property
    def appeal( this ): return this.terminal.appeal
    @property
    def words( this ): return this.terminal.words
    @property
    def text( this ): return this.terminal.text
    @property
    def topic( this ): return this.terminal.topic

    def say( this, text ): this.terminal.say( text )
    def play( this, waveFileName ): this.terminal.play( waveFileName )
#endregion
# Words manipulation
#region
    def getNormalFormOf( this, word: str, tags=None ) -> str:
        """Возвращает нормальную форму слова с учетом морфологических признаков"""
        parses = this.morphy.parse( word )
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
        """Сравнение слова в фразе с заданным с учетом морфологических признаков"""
        nf = this.getNormalFormOf( word, tags )
        for p in this.terminal.words[index]:
            if ( tags == None or tags in p.tag ) and p.normal_form == nf: 
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
        return None
    def deleteWord( this, index ):
        #delete word
        this.terminal.words.pop( index )
        this.updateText()

    def insertWords( this, index, words ):
        words = wordsToList( words )

        for i in range(len(words)):
            this.terminal.words.insert(index, this.terminal.morphy.parse(words[-i-1]) )
        this.updateText()

    def updateText( this ):
        text = ''
        for w in this.terminal.words:
            text = text + w[0].word + ' '
        text = text.strip()
        if text != this.terminal.text :
            this.terminal.text = text
            this.terminal.logDebug(f'Text changed: "{text}"')


#endregion

# Config-related stuff
#region
    def subscribe( this, topic:str ):
        """Привязать вызов process к состоянию"""
        this.subscriptions.add( str( topic ) )

    def unsubscribe( this, topic:str ):
        """Привязать вызов process к состоянию"""
        this.subscriptions.remove( str( topic ) )

    def isSubscribed( this, topic ):
        topic = str( topic ).strip()
        for s in this.subscriptions:
            if s == "*" :return True
            ab = s.split( '*' )
            if len( ab ) == 1 and ab[0] == topic : return True
            if len( ab ) > 1 and topic.startswith( ab[0] ) and topic.endswith( ab[-1] ): return True

    def extendVocabulary( this, words:str ):
        """Добавить список необходимых слов в словарь фильтрации распознавалки голоса"""
        this.vocabulary = joinWords( this.vocabulary, words )

    def changeText( this, newText:str ):
        this.terminal.newText = normalizeWords( newText )

    def changeTopic( this, newTopic ):
        this.terminal.newTopic = str( newTopic )

    def stopParsing( this ):
        this.terminal.parsingStopped = True

    def restartParsing( this ):
        this.terminal.parsingStopped = True
        this.terminal.parsingRestart = True
#endregion


