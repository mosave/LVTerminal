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

        if __printLevel is not None and messageLevel >= __printLevel:
                sys.__stdout__.write( message if message.endswith('\n') else f'{message}\n' )

        if __logLevel is not None and str( message ).strip() != "" :
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

            if self.captureTo is not None : 
                self.captureTo.append( m )

    def flush( self ):
        self.logger.handlers[0].flush()
        pass
#endregion

#region exported functions
def log( message:str, level = logging.INFO ):
    """Вывод сообщения на экран и в журнал. Синоним для print()"""
    global __printLevel

    if __writer is not None :
        __writer.logMessage( level, message )
    elif __printLevel is not None and level >= __printLevel :
        print( message )

def logDebug( message:str ):
    """Вывод отладочного сообщения на экран и в журнал"""
    log( message, logging.DEBUG )

def logError( message: str ):
    """Вывод сообщения об ошибке на экран и в журнал"""
    log( message, logging.ERROR )

def fatalError( message: str ):
    global __printLevel
    __printLevel = logging.ERROR
    log( message, logging.CRITICAL )
    quit(1)


def loggerInit( config ):
    """Инициализация журнала"""
    global __writer

    if ((config.logFileName is not None) and config.logLevel is not None) or (config.printLevel is not None):
        __writer = Logger( config )
        sys.stdout = __writer
        sys.stderr = __writer

def loggerSetCapture( captureTo: list ):
    """Зарегистрировать list, в который будут копироваться все журналируемые сообщения без фильтрации"""
    global __writer
    if __writer is not None : __writer.captureTo = captureTo
#endregion