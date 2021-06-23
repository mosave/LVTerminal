import sys
import time
import os
import asyncio
from hbmqtt.client import MQTTClient
from hbmqtt.mqtt.constants import QOS_0, QOS_1, QOS_2

from lvt.logger import *

config = None
queue = None
client = None

async def mqttClient():
    global config
    global queue
    global client
    while True:
        try:
            print(f'Connecting "{config.mqttServer}"')
            await client.connect(config.mqttServer)
            while True:
                try:
                    (topic, data) = await asyncio.wait_for( queue.get(), timeout=10 )
                    await client.publish(topic, data, qos=QOS_0)
                except asyncio.TimeoutError:
                    await client.ping()
                except KeyboardInterrupt as e:
                    raise e
        except KeyboardInterrupt as e:
            raise e
        except Exception as e:
            printError( f'MQTT: exception: {e}' )
            asyncio.sleep(10)
        finally:
            try: await client.disconnect()
            except: pass

class MQTT:
    def initialize( gConfig ):
        """Initialize module' config variable for easier access """
        global config
        global queue
        global client
        config = gConfig
        queue = asyncio.Queue()
        client = MQTTClient(client_id='LVTServer')

    def publish(topic, message):
        global config
        global queue
        if config.mqttServer != '' :
            queue.put_nowait( (topic, message) )

    def subscribe(topic):
        global config
        global queue
        if config.mqttServer != '' :
            pass
