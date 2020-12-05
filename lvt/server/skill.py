import sys
import importlib
from lvt.const import *
from lvt.grammar import *

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
        # Чем выше значение приоритета, тем ближе к началу в цепочке распознавания ставится скил
        this.priority = 0
        # Переход в новое состояние
        this.onLoad()

    def onLoad( this ):
        """Вызывается при инициализации скилла. 
        Обазательная конфигурация:
          * Состояния, к которым необходимо прибиндить скил
          * Ключевые слова, которые необходимо добавить в словарь фильтрации распознавалки
        """

        # Состояния, в которых скилл должен вызываться в при распозновании фразы
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
        """Вызывается сразу после перехода синтаксического анализатора в состояние, на которое подписан скилл
        """
        pass

        
    def onTimer( this ):
        """Вызывается примерно 1 раз в секунду, в зависимости от """
        pass


    def getSkillFileName(this, ext: str) -> str:
        """Generate skill-related file name by adding extension"""
        if not isinstance(ext,str) :
            ext = ''
        elif not ext.startswith('.'):
            ext = '.'+ext
        # :)
        if ext=='.py': ext = '.py.dat'
        return os.path.splitext(moduleFileName)[0] + ext

# Config-related stuff
#region 
    def subscribe( this, topic:str ):
        """Привязать вызов process к состоянию"""
        this.subscriptions.add( str(topic).lower() )

    def unsubscribe( this, topic:str ):
        """Привязать вызов process к состоянию"""
        this.subscriptions.remove( str(topic).lower() )

    def isSubscribed( this, topic ):
        topic = str(topic).strip().lower()
        for s in this.subscriptions:
            if s=="*" :return True
            ab = s.split('*')
            if len(ab)==1 and ab[0]==topic : return True
            if len(ab)>1 and topic.startswith(ab[0]) and topic.endswith(ab[-1]): return True

    def extendVocabulary( this, words:str ):
        """Добавить список необходимых слов в словарь фильтрации распознавалки голоса"""
        this.vocabulary = joinWords( this.vocabulary, words )

    def changeText(this, newText:str ):
        this.terminal.newText = newText

    def changeTopic( this, newTopic ):
        this.terminal.newTopic = str(newTopic).lower()

    def stopParsing( this ):
        this.terminal.parsingStopped = True
#endregion


