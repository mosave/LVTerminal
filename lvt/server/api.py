import json
import asyncio
from aiohttp import web, WSMsgType

import time

from lvt.const import *
from lvt.protocol import *
from lvt.logger import *
from lvt.server.tts import TTS
import lvt.server.config as config
import lvt.server.terminal as terminals
import lvt.server.persistent_state as persistent_state

api_tts = None
api_queue = []

def sendMessage( msg: str, statusCode: int = 0, status: str = None, data = None) -> bool:
    global api_queue
    message = {
            'Message': msg,
            'StatusCode': statusCode
            }
    if status is not None :
        message['Status'] = str(status)
    if data is not None:
        message['Data'] = json.dumps( data )

    api_queue.append( message )

def sendError( errorCode: int, errorMessage: str ):
    sendMessage( MSG_API_ERROR, errorCode, errorMessage )

def fireIntent( intent_type: str, terminal_id: str, text: str, intent_data ):
    terminal = terminals.get(terminal_id)
    data = dict(intent_data) if intent_data is not None else {}
    data["speaker"] = terminal_id
    if ("location" not in data) or (data["location"] is None):
        data["location"] = terminal.location
    if ("person" not in data) or (data["person"] is None):
        data["person"] = terminal.speaker

    sendMessage( MSG_API_FIRE_INTENT, data = {
        'Intent': intent_type,
        'Terminal': terminal_id,
        'Text': text,
        'Data' : data
    } )


async def server( request ):
    global api_tts
    global api_queue
    if api_tts is None:
        api_tts = TTS()

    connection = web.WebSocketResponse()
    await connection.prepare(request)

    statusSent = 0
    authorized = False
    tsCache = {}

    def sendLVTStatus():
        data = terminals.getState()
        for id, state in terminals.states.items():
            tsCache[id] = json.dumps(state)
        persistent_state.save()
        sendMessage( MSG_API_SERVER_STATUS, data=data )


    log("API Thread: Starting")
    while True: # <== Breaking out of here will close connection
        try:
            # send messages in queue
            while len(api_queue)>0:
                try:
                    await asyncio.wait_for( connection.send_json( api_queue.pop(0) ), 5 )
                except Exception:
                    break

            # Авторизуем клиента если пароль не задан:
            if not authorized and config.apiServerPassword is None:
                sendMessage( MSG_API_AUTHORIZE, 0, "Authorized" )
                authorized = True

            # Отправляем состояние сервера раз в минуту:
            if authorized and ((time.time() - statusSent) >= 60):
                #logDebug(f"API Thread: Sending status by timeout")
                sendLVTStatus()
                statusSent = time.time()
                persistent_state.save()

            try:
                message = await connection.receive(0.5)
            except asyncio.TimeoutError:
                if authorized: # No message received - just send terminal status updates if any
                    #logDebug(f"checking updates")
                    updates = {}
                    for id, t in terminals.terminals.items():
                        s = json.dumps(t.getState())
                        if tsCache[id] != s:
                            tsCache[id] = s
                            updates[id] = terminals.states[id]
                    if bool(updates):
                        sendMessage( MSG_API_TERMINAL_STATUS, data=updates )
                continue

            if message.type == WSMsgType.CLOSED:
                break
            elif message.type == WSMsgType.TEXT: # Получено текстовое сообщение
                # Разбираем сообщение. Ошибки разбора тупо игнорируем
                request = json.loads( str(message.data) )
                message = str(request['Message'])
                data =  json.loads( str( request['Data'] ) ) if 'Data' in request else None

                if message is not None:
                    if not authorized:
                        if message == MSG_API_AUTHORIZE:
                            if str(data) == str(config.apiServerPassword):
                                sendMessage( MSG_API_AUTHORIZE, statusCode=0, status="Authorized" )
                                authorized = True
                            else:
                                sendMessage( MSG_API_AUTHORIZE, statusCode=-1, status="Invalid Password" )
                                break

                    elif message == MSG_API_SERVER_STATUS:
                        sendLVTStatus()
                        statusSent = time.time()

                    elif message == MSG_API_TERMINAL_STATUS:
                        for tid, status in data.items():
                            terminal = terminals.get( tid )
                            if terminal is not None:
                                if 'Volume' in status:
                                    terminal.volume = int( status['Volume'] )
                                if 'Filter' in status:
                                    terminal.filter = int( status['Filter'] )

                    elif message == MSG_API_SAY:
                        text = data["Say"]
                        trms = data["Terminals"] if isinstance(data["Terminals"], list ) else [str(data["Terminals"])]
                        voice = await api_tts.textToSpeechAsync(text)

                        for tid in trms:
                            terminal = terminals.get( tid )
                            await terminal.playVoiceAsync(voice)

                    elif message == MSG_API_PLAY:
                        sound = data["Sound"]
                        trms = data["Terminals"] if isinstance(data["Terminals"], list ) else [str(data("Terminals"))]

                        for tid in trms:
                            terminal = terminals.get( tid )
                            await terminal.playAsync(sound)

                    elif message == MSG_API_RESTART_TERMINAL:
                        say = data["Say"] if "Say" in data else ""
                        say_on_connect = data["SayOnConnect"] if "SayOnConnect" in data else ""
                        force_update = bool(data["Update"]) if "Update" in data else False
                        trms = data["Terminals"] if isinstance(data["Terminals"], list ) else [str(data("Terminals"))]


                        for tid in trms:
                            terminal = terminals.get( tid )
                            if terminal is not None and terminal.connected:
                                if force_update:
                                    await terminal.updateClient(say, say_on_connect)
                                else:
                                    await terminal.reboot(say, say_on_connect)

                    elif message == MSG_API_SET_INTENTS:
                        for tid, terminal in terminals.terminals.items():
                            skill = terminal.getSkill(HA_INTENTS_SKILL)
                            if bool(data) and skill is None:
                                sendError( 2, f'Terminal "{tid}" not have {HA_INTENTS_SKILL} enabled' )
                                continue
                            if skill is not None:
                                skill.intents = data

                    elif message == MSG_API_NEGOTIATE:
                        trms = data["Terminals"] if isinstance(data["Terminals"], list ) else [str(data("Terminals"))]
                        for tid in trms:
                            terminal = terminals.get( tid )
                            if terminal is None:
                                sendError( 1, f'Terminal "{tid}" not found' )
                                continue

                            skill = terminal.getSkill(HA_NEGOTIATE_SKILL)
                            if skill is None:
                                sendError( 2, f'Terminal "{tid}" not have {HA_NEGOTIATE_SKILL} enabled' )
                                await terminal.sayAsync("Скилл Home Assistant Negotiate не загружен")
                                continue

                            params = {}
                            if ('Say' in data) and (data['Say'] is not None):
                                params['Say'] = data['Say']
                            else:
                                sendError( 2, f'"Say" parameter not defined' )

                            if ('Prompt' in data) and (data['Prompt'] is not None):
                                params['Prompt'] = data['Prompt']
                            
                            if ('Options' in data) and isinstance(data['Options'], list) and len(data['Options']) > 1:
                                params['Options'] = data['Options']
                            else:
                                sendError( 3, 'Invalid "Options" parameter' )

                            if ('DefaultIntent' in data) and (data['DefaultIntent'] is not None):
                                params['DefaultIntent'] = data['DefaultIntent']
                            else:
                                sendError( 3, ' "DefaultIntent" parameter not defined' )

                            if ('DefaultTimeout' in data) and (data['DefaultTimeout'] is not None):
                                params['DefaultTimeout'] = int(data['DefaultTimeout'])

                            if ('DefaultUtterance' in data) and (data['DefaultUtterance'] is not None):
                                params['DefaultUtterance'] = data['DefaultUtterance']

                            if ('DefaultSay' in data) and (data['DefaultSay'] is not None):
                                params['DefaultSay'] = data['DefaultSay']

                            if ('DefaultData' in data) and (data['DefaultData'] is not None):
                                params['DefaultData'] = data['DefaultData']

                            await terminal.changeTopicAsync( TOPIC_HA_NEGOTIATE, params )

                    else:
                        raise Exception( 'Invalid Command' ) 
        except KeyboardInterrupt:
            break
        except Exception as e:
            logError(f"API Thread: {type(e).__name__}: {e}")
            sendMessage( MSG_API_ERROR, statusCode=-1, status=f"{type(e).__name__}: {e}" )

    log("API Thread: Exiting")
