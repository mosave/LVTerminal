import sys
import os
import logging
import logging.handlers
from lvt.const import *

config = None
logWriter = None

def log( message:str ):
    """Вывод сообщения на экран и в журнал. Синоним для print()"""
    print( message )

def logError( message: str ):
    """Вывод сообщения об ошибке на экран и в журнал"""
    if logWriter != None :
        logWriter.logMessage( logging.ERROR, message )
    elif logging.ERROR >= config.printLevel if (config!=None) else 0:
        print( message )

def printError( message:str ):
    """Вывод сообщения об ошибке на экран и в журнал, синоним logError()"""
    logError( message )

def printDebug( message:str ):
    """Вывод отладочного сообщения на экран и в журнал"""
    if logWriter != None :
        logWriter.logMessage( logging.DEBUG, message )
    elif logging.DEBUG >= config.printLevel if (config!=None) else 0:
        print( message )

def logDebug( message: str ):
    """Вывод отладочного сообщения на экран и в журнал, синоним logDebug()"""
    printDebug( message )

def fatalError( message:str):
    """Вывод сообщения об ошибке на экран и в журнал и завершение работы"""
    print( message )
    if logWriter != None :
        logWriter.logMessage( logging.ERROR, message )
    quit(1)

class Logger:

    def __init__( this ):
        global config

        fn = config.logFileName
        if not fn.startswith( '/' ) and not fn.startswith( '\\' ) :
            fn = os.path.join( ROOT_DIR, fn )

        this.logger = logging.getLogger()
        this.logger.setLevel( logging.CRITICAL )
        this.captureTo = None
        # Make a handler that writes to a file, making a new file at midnight
        # and keeping 3 backups
        this.handler = logging.handlers.TimedRotatingFileHandler( fn, when="midnight", backupCount=3 )
        # Format each log message like this
        this.formatter = logging.Formatter( '%(asctime)s %(message)s' )
        # Attach the formatter to the handler
        this.handler.setFormatter( this.formatter )
        # Attach the handler to the logger
        this.logger.addHandler( this.handler )

    def write( this, message ):
        """This method is for stdout/stderr redirection only. Turn print() into log()/logInfo() """
        if message.strip() != "" or message=='' :
            this.logMessage( logging.INFO, message )

    def logMessage( this, messageLevel: int, message: str ):
        """"""
        global config

        if messageLevel >= config.printLevel:
            sys.__stdout__.write( message if message.endswith('\n') else f'{message}\n' )

        if str( message ).strip() != "" :
            if messageLevel >= logging.ERROR : 
                prefix = "E"
            elif messageLevel >= logging.WARNING : 
                prefix = "W"
            elif messageLevel >= logging.INFO : 
                prefix = "I"
            else : 
                prefix = "D"

            m = f'{prefix} {message}'

            if messageLevel >= config.logLevel and message.strip() != "": 
                this.logger.log( logging.CRITICAL, m )

            if this.captureTo != None : 
                this.captureTo.append( m )

    def flush( this ):
        this.logger.handlers[0].flush()
        pass
# Static methods
#region
    def initialize( gConfig ):
        """Инициализация журнала"""
        global config
        global logWriter
        config = gConfig

        if config.logFileName != None :
            logWriter = Logger()
            sys.stdout = logWriter
            sys.stderr = logWriter

    def setLogCapture( captureTo: list ):
        """Зарегистрировать list, в который будут копироваться все журналируемые сообщения без фильтрации"""
        if logWriter != None : logWriter.captureTo = captureTo
#endregion