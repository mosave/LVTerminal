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

async def server( request ):
    global api_tts
    if api_tts is None:
        api_tts = TTS()

    connection = web.WebSocketResponse()
    await connection.prepare(request)

    statusSent = 0
    authorized = False
    tsCache = {}

    async def sendMessage( msg: str, statusCode: int = 0, status: str = None, data = None) -> bool:
        message = {
                'Message': msg,
                'StatusCode': statusCode
                }
        if status != None :
            message['Status'] = str(status)
        if data != None:
            message['Data'] = json.dumps( data )

        try:
            await asyncio.wait_for( connection.send_json( message ), 5 )
            return True
        except Exception:
            return False

    async def sendLVTStatus() -> bool:
        data = terminals.getState()
        for id, state in terminals.states.items():
            tsCache[id] = json.dumps(state)
        persistent_state.save()
        return await sendMessage( MSG_API_SERVER_STATUS, data=data )


    log("API Thread: Starting")
    while True: # <== Breaking out of here will close connection
        try:
            # Авторизуем клиента если пароль не задан:
            if not authorized and config.apiServerPassword is None:
                if not await sendMessage( MSG_API_AUTHORIZE, 0, "Authorized" ):
                    break
                authorized = True

            # Отправляем состояние сервера раз в минуту:
            if authorized and ((time.time() - statusSent) >= 60):
                #logDebug(f"API Thread: Sending status by timeout")
                if not await sendLVTStatus() : 
                    break
                statusSent = time.time()
                persistent_state.save()

            message = await connection.receive(0.5)
            if message.type == WSMsgType.CLOSED:
                break
            elif message.type == WSMsgType.TEXT: # Получено текстовое сообщение
                # Разбираем сообщение. Ошибки разбора тупо игнорируем
                request = json.loads( str(message.data) )
                message = str(request['Message'])
                data =  json.loads( str( request['Data'] ) ) if 'Data' in request else None

                if message != None:
                    if not authorized:
                        if message == MSG_API_AUTHORIZE:
                            if str(data) == str(config.apiServerPassword):
                                if not await sendMessage( MSG_API_AUTHORIZE, statusCode=0, status="Authorized" ):
                                    break
                                authorized = True
                            else:
                                if not await sendMessage( MSG_API_AUTHORIZE, statusCode=-1, status="Invalid Password" ):
                                    break

                    elif message == MSG_API_SERVER_STATUS:
                        if not await sendLVTStatus():
                            break
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
                        trms = data["Terminals"]
                        voice = await api_tts.textToSpeechAsync(text)

                        for tid in trms:
                            terminal = terminals.get( tid )
                            terminal.playVoice(voice)

                    elif message == MSG_API_PLAY:
                        sound = data["Sound"]
                        trms = data["Terminals"]

                        for tid in trms:
                            terminal = terminals.get( tid )
                            terminal.play(sound)

                    #elif m == MSG_API_ASK :
                    #    terminal.answerPrefix = data['answerPrefix'] if 'answerPrefix' in data else ''
                    #    if message:
                    #        await terminal.say( message )
                    #    await terminal.changeTopic( TOPIC_MD_ASK )
                    #elif m == MSG_API_YESNO :
                    #    terminal.answerPrefix = data['answerPrefix'] if 'answerPrefix' in data else ''
                    #    await terminal.changeTopic( "YesNo", \
                    #        message=message,
                    #        topicYes = TOPIC_MD_YES,
                    #        topicNo = TOPIC_MD_NO,
                    #        topicCancel = TOPIC_MD_CANCEL
                    #    )
                    else:
                        raise Exception( 'Invalid Command' ) 
                elif authorized: # No message received - just send terminal status updates if any
                    #logDebug(f"checking updates")
                    updates = {}
                    for id, t in terminals.terminals.items():
                        s = json.dumps(t.getState())
                        if tsCache[id] != s:
                            tsCache[id] = s
                            updates[id] = terminals.states[id]
                    if updates:
                        #logDebug(f"API Thread: Sending updates")
                        if not await sendMessage( MSG_API_TERMINAL_STATUS, data=updates ):
                            break
        except KeyboardInterrupt:
            break
        except asyncio.TimeoutError:
            continue
        except Exception as e:
            logError(f"API Thread: {type(e).__name__}: {e}")
            sendMessage( MSG_API_ERROR, statusCode=-1, status=f"{type(e).__name__}: {e}" )

    log("API Thread: Exiting")
