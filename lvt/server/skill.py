import sys

from lvt.const import *
from lvt.server.terminal import Terminal
from lvt.grammar import *



#Define base skill class
class Skill:
    def __init__( this, terminal: Terminal, moduleName: str, moduleFileName: str ):

        this.terminal = terminal
        this.moduleName = moduleName
        this.moduleFileName = moduleFileName

        this.enable = True
        this.subscriptions = set()
        this.dependsOn = set()
        # Список слов (через пробел), которые необходимо добавить в фильтр
        # распозновалки для работы этого скила
        this.vocabulary = ""
        this.configure()

    def configure( this ) -> dict():
        """Этот метод необходимо перекрыть для конфигурирования скилла
        Обазательная конфигурация:
          * Состояния, к которым необходимо прибиндить скил
          * Ключевые слова, которые необходимо добавить в словарь фильтрации распознавалки
        """

        # Запретить использование скила
        # cfgEnable(False)

        # Список скиллов, от которых зависит работа данного скила
        # Допустимо использовать как полное имя класса, так частичное
        # cfgDependsOn('lvt.server.skills.SingTheSong')
        # cfgDependsOn('skills.SingTheSong')
        # cfgDependsOn('SingTheSong')

        # Состояния, в которых скилл должен вызываться в при распозновании фразы
        # (stateName, <фраза распознана полностью>, <обнаружено обращение к ассистенту>)
        # cfgSubscribe( STATE_DEFAULT )
        pass

    def onText( this, state:str, text:str, isFinal: bool, isAppeal:bool ):
        """Вызывается при появлении нового текста в случае если скилл привязан к текущему состоянию
          * isFinal - распознавание фразы завершено
          * isAppeal - в фразе присутствует обращение к ассистенту
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
        
    def onTimer( this, state:str, ):
        pass

# Config-related stuff
#region 
    def cfgEnable( this, enable:bool=True ):
        """Разрешить использование скилла"""
        this.enable = enable

    def cfgDependsOn( this, classsName:str ):
        """Добавить имя класса скила, от которого зависит работа"""
        this.dependsOn = set(this.dependsOn.add(className))
        
    def cfgSubscribe( this, stateName:str ):
        """Привязать вызов process к состоянию"""
        this.subscriptions.add( stateName )

    def cfgUnsubscribe( this, stateName:str ):
        """Привязать вызов process к состоянию"""
        this.subscriptions.remove( stateName )

    def cfgVocabulary( this, words:str ):
        """Добавить список необходимых слов в словарь фильтрации распознавалки голоса"""
        this.keywords = joinWords( this.keywords, words )
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

