import sys
import importlib
from lvt.const import *
from lvt.grammar import *

#Define base skill class
class Skill:
    def __init__( this, terminal, moduleFileName: str ):
        this.terminal = terminal
        this.moduleFileName = moduleFileName

        this.enable = True
        this.subscriptions = set()
        # Список слов (через пробел), которые необходимо добавить в фильтр
        # распозновалки для работы этого скила
        this.vocabulary = ''
        this.priority = 9999
        # Переход в новое состояние
        this.onLoad()

    def onLoad( this ):
        """Вызывается при инициализации скилла. 
        Обазательная конфигурация:
          * Состояния, к которым необходимо прибиндить скил
          * Ключевые слова, которые необходимо добавить в словарь фильтрации распознавалки
        """

        # Состояния, в которых скилл должен вызываться в при распозновании фразы
        # subscribe( STATE_ALL )
        # subscribe( STATE_DEFAULT )
        # unsubscribe( STATE_DEFAULT )
        pass

    def onText( this, state:str, text:str, final: bool, appeal:bool ):
        """Вызывается при появлении нового текста в случае если скилл привязан к текущему состоянию
          * state - текущее состояние 
          * final - распознавание фразы завершено
          * appeal - в фразе присутствует обращение к ассистенту
        Возвращаемое значение, tuple:
        (<новое состояние>, <прервать дальнейшую обработку фразы> )
        """

        pass

    def onEnterState( this, state:str, text:str, isFinal: bool, isAppeal:bool ):
        """Вызывается сразу после перехода синтаксического анализатора в состояние, на которое подписан скилл
        """

        pass

    def onExitState( this, state:str, text:str, isFinal: bool, isAppeal:bool ):
        """Вызывается перед выходом синтаксического анализатора из состояния, на которое подписан скилл
        """
        pass
        
    def onTimer( this, state:str ):
        """Вызывается примерно 1 раз в секунду, в зависимости от """
        pass


# Config-related stuff
#region 
    def subscribe( this, stateName:str ):
        """Привязать вызов process к состоянию"""
        this.subscriptions.add(stateName)

    def unsubscribe( this, stateName:str ):
        """Привязать вызов process к состоянию"""
        this.subscriptions.remove( stateName )

    def extendVocabulary( this, words:str ):
        """Добавить список необходимых слов в словарь фильтрации распознавалки голоса"""
        this.vocabulary = joinWords( this.vocabulary, words )
#endregion
    def getSkillFileName(this, ext: str) -> str:
        """Generate skill-related file name by adding extension"""
        if not isinstance(ext,str) :
            ext = ''
        elif not ext.startswith('.'):
            ext = '.'+ext
        # :)
        if ext=='.py': ext = '.py.dat'
        return os.path.splitext(moduleFileName)[0] + ext

