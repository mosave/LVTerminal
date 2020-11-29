
# Lite Voice Terminal communication protocol messages
MSG_IDLE = "Idle"                   # Force terminal to Idle mode
MSG_STATUS = "Status"               # Request / Send server-side terminal status
MSG_CONFIG = "Config"               # Request / Send server configuration and status
MSG_DISCONNECT = "Disconnect"       # Close current session
MSG_TERMINAL = "Terminal"           # Authorize terminal on server.
                                    # Parameters are <TerminalId> and <Pasword>
MSG_TERMINAL_NAME = "TerminalName"  # Send terminal name to server.  Parameter is <Terminal Name>
MSG_ANIMATE = "Animate"             # Server request to play animation

# All available commands (for command validation
MSG_ALL = { MSG_IDLE, MSG_STATUS, MSG_CONFIG, MSG_DISCONNECT, MSG_TERMINAL, MSG_TERMINAL_NAME, MSG_ANIMATE }

def split2( s: str):
    if not isinstance(s, str) : return (None, None)
    s = s.strip()
    if len(s)<=0 : return (None,None)
    p = s.find(' ')
    if p<0 :return (s, None)
    return (s[:p], s[p:].strip() )


# Returns tuple: message name and parameters
def parseMessage( message ) :
    m, p = split2(message.strip())
    if m in MSG_ALL: return (m, p)
    return (None, None) 


def MESSAGE( msg: str, p1: str=None, p2: str=None ) -> str:
    if msg not in MSG_ALL: raise Exception( 'Invalid message passed' )
    if p1 != None: msg += ' ' + str(p1).strip()
    if p2 != None: msg += ' ' + str(p2).strip()
    return msg


