import sys
import time
import os
import threading
import queue as Queue
from lvt.const import *
from lvt.client.config import Config

class Animator:
    def __init__( this, config: Config, shared ):
        this.config = config
        this.shared = shared
        # shared.animation - текущая анимация
        # shared.isTerminated - необходимо прекратить работу
        this.queue = Queue.Queue()
        this.animation = ANIMATION_NONE
        this.previousAnimation = this.animation
        this.timeout = 0.2

    def start( this ):
        this.thread = threading.Thread( target=this.__run__ )
        this.thread.daemon = True
        this.thread.start()

    def awake( this, restart:bool ):
        """Wake up and listening"""
        if restart : print( 'Awaken' )

    def think( this, restart:bool ):
        """Thinking"""
        if restart : print( 'Thinking' )

    def accept( this, restart:bool ):
        """Accepted"""
        if restart : print( 'Confirmed' )

    def cancel( this, restart:bool ):
        """Cancelled / Ignoring"""
        if restart : print( 'Cancelled' )

    def none( this, restart:bool ):
        """standby animation"""
        if restart : print( 'None' )

    def off( this ):
        """Alias to none() """
        this.none( True )

    def __run__( this ):
        while not this.shared.isTerminated:
            _animation = this.animation
            if not this.queue.empty() :
                this.animation = this.queue.get()

            restart = _animation != this.animation
            if this.animation == ANIMATION_AWAKE : this.awake( restart )
            elif this.animation == ANIMATION_THINK : this.think( restart )
            elif this.animation == ANIMATION_ACCEPT : this.accept( restart )
            elif this.animation == ANIMATION_CANCEL : this.cancel( restart )
            else: this.none(restart)
            #sleep 10ms
            time.sleep(this.timeout)
        this.off

    def animate( this, animation ):
        this.queue.put( animation )
    