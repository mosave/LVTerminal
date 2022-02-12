import sys
import time
import os
import threading
#import queue as Queue
import asyncio
from lvt.const import *
from lvt.logger import *

class Animator:
    def __init__( self, shared ):
        # shared.animation - текущая анимация
        # shared.isTerminated - необходимо прекратить работу
        self.shared = shared
        self.animation = ANIMATION_NONE
        self.locked = False
        self.timeout = 0.2
        self.muted = False
        self.queue = asyncio.Queue()

    def start( self ):
        self.thread = threading.Thread( target=self.__run__ )
        self.thread.daemon = False
        self.thread.start()

### Effects implementation ##############################################################
#region
    def animationAwake( self, restart:bool )->bool:
        """Wake up and listening
        Returns effect lock status: True if should not be interrupted
        """
        #if restart : print( 'Animation: Awake' )
        return False

    def animationThink( self, restart:bool )->bool:
        """Thinking
        Returns effect lock status: True if should not be interrupted
        """
        #if restart : print( 'Animation: Thinking' )
        return False

    def animationAccept( self, restart:bool )->bool:
        """Accepted, play and back to current animation
        Returns effect lock status: True if should not be interrupted
        """
        #if restart : print( 'Animation: Confirmed' )
        self.timeout = 1
        return restart


    def animationCancel( self, restart:bool )->bool:
        """Cancelled / Ignoring, play and back to current animation
        Returns effect lock status: True if should not be interrupted
        """
        #if restart : print( 'Animation: Cancelled' )
        self.timeout = 1
        return restart

    def animationNone( self, restart:bool )->bool:
        """standby animation
        Returns effect lock status: True if should not be interrupted
        """
        #if restart : print( 'Animation: Off' )
        return False

    def off( self )->bool:
        """Alias to none()
        Returns effect lock status: True if should not be interrupted
        """
        return self.animationNone( True )
#endregion

    def __run__( self ):
        muted = False
        locked = False
        while not self.shared.isTerminated:
            try:
                animation = self.animation
                restart = False
                if not locked:
                    if not self.queue.empty() :
                        self.animation = self.queue.get_nowait()
                        restart = animation != self.animation
                    elif self.animation not in ANIMATION_STICKY:
                        self.animation = ANIMATION_NONE

                if self.animation == ANIMATION_AWAKE : 
                    locked = self.animationAwake( restart )
                elif self.animation == ANIMATION_THINK : 
                    locked = self.animationThink( restart )
                elif self.animation == ANIMATION_ACCEPT : 
                    locked = self.animationAccept( restart )
                elif self.animation == ANIMATION_CANCEL : 
                    locked = self.animationCancel( restart )
                else: 
                    locked = self.animationNone(restart)

                #sleep 10ms
                time.sleep(self.timeout)
            except KeyboardInterrupt as e:
                break
            except Exception as e:
                logError( f'Exception in animator thread: {e} ')
        try: 
            self.off()
        except Exception:
            pass

    def animate( self, animation ):
        self.queue.put_nowait( animation )
    