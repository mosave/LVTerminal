import sys
import time
import os
import threading
#import queue as Queue
import asyncio
from lvt.const import *
from lvt.logger import *
from lvt.client.config import Config

class Animator:
    def __init__( this, config: Config, shared ):
        this.config = config
        this.shared = shared
        # shared.animation - текущая анимация
        # shared.isTerminated - необходимо прекратить работу
        this.queue = asyncio.Queue()
        this.animation = ANIMATION_NONE
        this.locked = False
        this.timeout = 0.2
        this.muted = False

    def start( this ):
        this.thread = threading.Thread( target=this.__run__ )
        this.thread.daemon = False
        this.thread.start()

### Effects implementation ##############################################################
#region
    def animationAwake( this, restart:bool )->bool:
        """Wake up and listening
        Returns effect lock status: True if should not be interrupted
        """
        #if restart : print( 'Animation: Awake' )
        return False

    def animationThink( this, restart:bool )->bool:
        """Thinking
        Returns effect lock status: True if should not be interrupted
        """
        #if restart : print( 'Animation: Thinking' )
        return False

    def animationAccept( this, restart:bool )->bool:
        """Accepted, play and back to current animation
        Returns effect lock status: True if should not be interrupted
        """
        #if restart : print( 'Animation: Confirmed' )
        this.timeout = 1
        return restart


    def animationCancel( this, restart:bool )->bool:
        """Cancelled / Ignoring, play and back to current animation
        Returns effect lock status: True if should not be interrupted
        """
        #if restart : print( 'Animation: Cancelled' )
        this.timeout = 1
        return restart

    def animationNone( this, restart:bool )->bool:
        """standby animation
        Returns effect lock status: True if should not be interrupted
        """
        #if restart : print( 'Animation: Off' )
        return False

    def off( this )->bool:
        """Alias to none()
        Returns effect lock status: True if should not be interrupted
        """
        return this.animationNone( True )
#endregion

    def __run__( this ):
        muted = False
        locked = False
        try:
            while not this.shared.isTerminated:
                animation = this.animation
                restart = False
                if not locked:
                    if not this.queue.empty() :
                        this.animation = this.queue.get_nowait()
                        restart = animation != this.animation
                    elif this.animation not in ANIMATION_STICKY:
                        this.animation = ANIMATION_NONE

                if this.animation == ANIMATION_AWAKE : 
                    locked = this.animationAwake( restart )
                elif this.animation == ANIMATION_THINK : 
                    locked = this.animationThink( restart )
                elif this.animation == ANIMATION_ACCEPT : 
                    locked = this.animationAccept( restart )
                elif this.animation == ANIMATION_CANCEL : 
                    locked = this.animationCancel( restart )
                else: 
                    locked = this.animationNone(restart)

                #sleep 10ms
                time.sleep(this.timeout)
        except KeyboardInterrupt as e:
            this.shared.isTerminated = True
        except Exception as e:
            logError( f'Exception in animator thread: {e} ')

        try: this.off()
        except: pass

    def animate( this, animation ):
        this.queue.put_nowait( animation )
    