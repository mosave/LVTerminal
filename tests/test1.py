#!/usr/bin/env python3
import json
import os
import sys
import asyncio
import ssl
import pathlib
import websockets
import logging
import time
from lvt.const import *
from lvt.protocol import *
from lvt.server.config import Config 
from lvt.server.terminal import Terminal
from lvt.server.speaker import Speaker
from lvt.server.speakers import Speakers
from lvt.server.skill import Skill
from lvt.server.skill_factory import SkillFactory
from lvt.server.state_machine import StateMachine

#set project folder to correct value
ROOT_DIR = os.path.abspath( os.path.join( os.path.dirname( __file__ ),'../') )


messageQueue = list()

config = Config( 'lvt_server.cfg' )

Terminal.setConfig( config )
Speakers.setConfig( config )

terminal = Terminal( config.terminals[0] )



terminal.processFinal("алиса привет")

terminal.onDisconnect()

for m in messageQueue:
    if isinstance(m,str): print( m )



