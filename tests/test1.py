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
from lvt.server.skill import Skill

#set project folder to correct value
ROOT_DIR = os.path.abspath( os.path.join( os.path.dirname( __file__ ),'../') )


config = Config( 'lvt_server.cfg' )

Terminal.Initialize( config )
Speaker.Initialize( config )

messageQueue = list()

terminal = Terminal.authorize( 'testterminal', 'Password')
terminal.onConnect(messageQueue)

terminal.onText("слушай, мажордом!", True)

terminal.onText("мажордом, включи свет на кухне", True)

terminal.onDisconnect()

for m in messageQueue:
    if isinstance(m,str): print( m )



