import sys
import os
import logging
import logging.handlers
from lvt.const import *

__writer = None
__printLevel = 20
__logLevel = 20
__fileName = None

#region class Logger
class Logger:
    def __init__( self, config ):
        global __fileName
        global __logLevel
        global __printLevel

        __fileName = config.logFileName
        __logLevel = config.logLevel
        __printLevel = config.printLevel

        fn = __fileName
        if not fn.startswith( '/' ) and not fn.startswith( '\\' ) :
            fn = os.path.join( ROOT_DIR, fn )

        self.logger = logging.getLogger()
        self.logger.setLevel( logging.CRITICAL )
        self.captureTo = None
        # Make a handler that writes to a file, making a new file at midnight
        # and keeping 3 backups
        self.handler = logging.handlers.TimedRotatingFileHandler( fn, when="midnight", backupCount=3 )
        # Format each log message like self
        self.formatter = logging.Formatter( '%(asctime)s %(message)s' )
        # Attach the formatter to the handler
        self.handler.setFormatter( self.formatter )
        # Attach the handler to the logger
        self.logger.addHandler( self.handler )

    def write( self, message ):
        """self method is for stdout/stderr redirection only. Turn print() into log()/logInfo() """
        if message.strip() != "" or message=='' :
            self.logMessage( logging.INFO, message )

    def logMessage( self, messageLevel: int, message: str ):
        """"""
        global __printLevel
        global __logLevel

        if __printLevel != None :
            return

        if messageLevel >= __printLevel:
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

            if messageLevel >= __logLevel and message.strip() != "": 
                self.logger.log( logging.CRITICAL, m )

            if self.captureTo != None : 
                self.captureTo.append( m )

    def flush( self ):
        self.logger.handlers[0].flush()
        pass
#endregion

#region exported functions
def log( message:str ):
    """Вывод сообщения на экран и в журнал. Синоним для print()"""
    print( message )

def logError( message: str ):
    """Вывод сообщения об ошибке на экран и в журнал"""
    global __printLevel
    if __printLevel == None:
       return
    if __writer != None :
        __writer.logMessage( logging.ERROR, message )
    elif logging.ERROR >= __printLevel:
        print( message )

def printError( message:str ):
    """Вывод сообщения об ошибке на экран и в журнал, синоним logError()"""
    logError( message )

def fatalError():
    printError()
    quit(1)


def printDebug( message:str ):
    """Вывод отладочного сообщения на экран и в журнал"""
    global __printLevel
    if __printLevel == None:
       return

    if __writer != None :
        __writer.logMessage( logging.DEBUG, message )
    elif logging.DEBUG >= __printLevel:
        print( message )

def logDebug( message: str ):
    """Вывод отладочного сообщения на экран и в журнал, синоним logDebug()"""
    printDebug( message )

def loggerInit( config ):
    """Инициализация журнала"""
    global __writer

    if ((config.logFileName != None) and config.logLevel != None) or (config.printLevel!=None):
        __writer = Logger( config )
        sys.stdout = __writer
        sys.stderr = __writer

def loggerSetCapture( captureTo: list ):
    """Зарегистрировать list, в который будут копироваться все журналируемые сообщения без фильтрации"""
    global __writer
    if __writer != None : __writer.captureTo = captureTo
#endregion