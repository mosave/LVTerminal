import sys
import time
import os
import audioop
import pyaudio
from lvt.const import *
from lvt.protocol import *
from lvt.client.animator import Animator


def MessageHandler( config, messages, shared ):
    print( "Event handler thread starting" )
    while not shared.isTerminated:
        try:
            message = messages.get()
            m,p = parseMessage(message)
            if isinstance( message, str ) :
                if m == MSG_ANIMATE:
                    if str(p) in ANIMATION_ALL:
                        Animator().animate(p)
                else:
                    print( f'Message "{msg}" handler not yet implemented' )
            else:
                print( f'Play audio, {len(m)}' )
        except KeyboardInterrupt:
            if not shared.isTerminated : print( "Terminating..." )
            shared.isTerminated = True
        except Exception as e:
            print( f'Event handler thread exception: {e}' )

    print( "Finishing Event handler thread" )

