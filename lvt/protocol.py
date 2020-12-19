
# Lite Voice Terminal communication protocol messages
MSG_IDLE = "Idle"                   # Force terminal to Idle mode
MSG_STATUS = "Status"               # Request / Send server-side terminal status
MSG_CONFIG = "Config"               # Request / Send server configuration and status
MSG_DISCONNECT = "Disconnect"       # Close current session

# Authorize terminal on server.
MSG_TERMINAL = "Terminal"# <TerminalId> <Pasword> <Version>

# Server request to display a text (if supported)
MSG_TEXT = "Text" # <any text to display goes after the command without quotes>

# Server request to play animation.  See const.ANIMATION* constants
MSG_ANIMATE = "Animate" # <AnimationName>

# Mute microphone
MSG_MUTE = "Mute"
# Unmute microphone
MSG_UNMUTE = "Unmute"               

# Command to update client
MSG_UPDATE = "Update" # <update package>

# All available commands (for command validation
MSG_ALL = { \
    MSG_IDLE, MSG_STATUS, MSG_CONFIG, MSG_DISCONNECT, MSG_TERMINAL, \
    MSG_TEXT, MSG_ANIMATE, MSG_MUTE, MSG_UNMUTE, MSG_UPDATE \
    }

def split2( s: str ):
    if not isinstance( s, str ) : return (None, None)
    s = s.strip()
    if len( s ) <= 0 : return (None,None)
    p = s.find( ' ' )
    if p < 0 :return (s, None)
    return (s[:p], s[p:].strip())

def split3( s: str ):
    a,b = split2( s )
    if b == None : return (a,b,None)
    b,c = split2( b )
    return a,b,c

# Returns tuple: message name and parameters
def parseMessage( message ) :
    m, p = split2( message.strip() )
    if m in MSG_ALL: return (m, p)
    return (None, None) 


def MESSAGE( msg: str, p1: str=None, p2: str=None, p3: str=None ) -> str:
    if msg not in MSG_ALL: raise Exception( f'Invalid message "{msg}"' )
    if p1 != None: msg += ' ' + str( p1 ).strip()
    if p2 != None: msg += ' ' + str( p2 ).strip()
    if p3 != None: msg += ' ' + str( p3 ).strip()
    return msg


