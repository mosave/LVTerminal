# Lite Voice Terminal communication protocol messages

# Server => Terminal: Перевести терминал в stand-by
MSG_IDLE = "Idle"

# Server => Terminal: Принудительный перевод терминала в активный режим
MSG_WAKEUP = "Wakeup"

# Terminal => Server: Запрос состояния терминала на стороне сервера
# Server => Terminal: Состояние терминала (JSON пакет)
MSG_STATUS = "Status" # [<terminal status, JSON>]

# Terminal => Server: Запрос конфигурации сервера
# Server => Terminal: Конфигурация сервера (JSON пакет)
MSG_CONFIG = "Config" # [<Server configuration, JSON>]

# Terminal => Server: Завершение текущей сессии
# Server => Terminal: Завершение текущей сессии
MSG_DISCONNECT = "Disconnect"

# Server => Terminal: Текст для отображения на терминале (если поддерживается)
MSG_TEXT = "Text" # text string to display

# Server => Terminal: play terminal animation (if supported by terminal)
# See const.ANIMATION* constants
MSG_ANIMATE = "Animate" # None|Awake|Think|Accept|Cancel 

# Server => Terminal: выключить/включить микрофон
MSG_MUTE = "Mute"
MSG_UNMUTE = "Unmute"               

# Server => Terminal: terminal client update package
MSG_UPDATE = "Update" # <client update JSON package>
# Update package is JSON data:
# [
#   ["lvt/const.py", "Content of file /lvt/const.py"],
#   ["File 2 to update, client-relative path", "Updated file content>"],
#   ["File 3 to update, client-relative path", "Updated file content>"],
#   ...
# ]

# Server => Terminal: Запрос на перезагрузку терминала
MSG_REBOOT = "Reboot" 

# Terminal => Server: Запрос терминала на авторизацию
# Server => Terminal: состояние авторизованного терминала либо disconnect если терминал не был авторизован
MSG_TERMINAL = "Terminal"# <TerminalId> <Password> <Version>

# All available commands
MSG_ALL = { \
    MSG_IDLE, MSG_STATUS, MSG_CONFIG, MSG_DISCONNECT, MSG_TERMINAL, MSG_REBOOT, \
    MSG_TEXT, MSG_ANIMATE, MSG_UPDATE, \
    MSG_MUTE, MSG_UNMUTE, \
    }

def split2( s: str ):
    """Разбивает строку на "первое ключевое слово и все остальное" """
    if not isinstance( s, str ) : return (None, None)
    s = s.strip()
    if len( s ) <= 0 : return (None,None)
    p = s.find( ' ' )
    if p < 0 :return (s, None)
    return (s[:p], s[p:].strip())

def split3( s: str ):
    """Разбивает строку на "ключевое слово, первый параметр и все остальное" """
    a,b = split2( s )
    if b == None : return (a,b,None)
    b,c = split2( b )
    return a,b,c

def parseMessage( message ) :
    """Разбивает сообщение на LVT команду и список параметров".
    Если ключевое слово не является командой - возвращает (None, None) """
    m, p = split2( message.strip() )
    if m in MSG_ALL: return (m, p)
    return (None, None) 

def MESSAGE( msg: str, p1: str=None, p2: str=None, p3: str=None ) -> str:
    """Конструирует LVT сообщение из команды и параметров"""
    if msg not in MSG_ALL: raise Exception( f'Invalid message "{msg}"' )
    if p1 != None: msg += ' ' + str( p1 ).strip()
    if p2 != None: msg += ' ' + str( p2 ).strip()
    if p3 != None: msg += ' ' + str( p3 ).strip()
    return msg


