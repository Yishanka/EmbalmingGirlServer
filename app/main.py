# get data from frontend, check data, call game api
# get status from game, check changed data, return to frontend
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import json
import uuid

from app.game import Game, SINGLE_MOVE_TYPES, INTER_MOVE_TYPES
from app.model import *
import app.error as err
from app.error import GameError
import uuid
from app.manager import ConnectionManager

app = FastAPI()

# 跨域配置（生产环境需限定具体域名）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

games: dict[str, Game] = {}
manager = ConnectionManager()

@app.post("/create")
async def create_game(data: GameCreateRequest):
    try:
        game_id = str(uuid.uuid4())
        while game_id in games:
            game_id = str(uuid.uuid4())
        games[game_id] = Game(set_num=data.set_num)
        return ApiResponse[str](code=200, msg='Game_Created', data=game_id)
    except GameError as e:
        raise HTTPException(status_code=400, detail=ApiResponse(code=400, msg=e.code))
    except Exception as e:
        raise HTTPException(status_code=500, detail=ApiResponse(code=500, msg=err.SYSTEM_ERROR))

@app.post("/join/{game_id}")
async def join_game(data: JoinGameRequest):
    try:
        game = games[data.game_id]
        pid: str = str(uuid.uuid4())
        while pid in game.pid_int_map:
            pid = str(uuid.uuid4())
        game.add_player(pid)
        return ApiResponse[str](code=200, msg='PLAYER_JOINED', data=pid)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=ApiResponse(code=404, msg=err.INVALID_GAME_ID))
    except GameError as e:
        raise HTTPException(status_code=400, detail=ApiResponse(code=400, msg=e.code))
    except Exception as e:
        raise HTTPException(status_code=500, detail=ApiResponse(code=500, msg=err.SYSTEM_ERROR))
    

@app.websocket("/ws/{game_id}/{pid}")
async def websocket_endpoint(websocket: WebSocket, game_id: str, pid: str):
    try:
        game: Game = games[game_id]
        manager.connect(websocket, game_id, pid)
    except KeyError as e:
        await websocket.close(code=1008, reason=err.INVALID_GAME_ID)
        return
    except Exception as e:
        raise HTTPException(status_code=500, detail=WsResponse(code=500, msg=err.SYSTEM_ERROR))

    try:
        while True:
            data = await websocket.receive_json()
            try:
                req_data: WsMoveRequest = WsMoveRequest(**data)
            except Exception as e:
                await websocket.send_json(WsResponse(code=500, msg=err.INVALID_PARAMS))
                continue  # 校验失败，跳过后续逻辑，等待重发
            # 处理逻辑
            try:
                if req_data.type == "START": # todo: 此处暂时让一个人处理启动游戏
                    game.start_game()
                elif req_data.type in ["EMB", "IMP", "PLAY"]: 
                    if req_data.type == "EMB":
                        game.emb_card(req_data.move_data)
                    elif req_data.type == "IMP":
                        game.imp_card(req_data.move_data)
                    elif req_data.type == "PLAY":
                        game.play_card(req_data.move_data)
                    
                    for pid in game.pid_int_map.keys():
                        personal_state: PersonalState = game.get_personal_state(pid)
                        await manager.send_personal_message(message=WsResponse(state=personal_state), game_id=game_id, pid=pid)

                elif game.curr_move_type in SINGLE_MOVE_TYPES: 
                    if game.curr_move_type == "PICK_FROM_EMBED": 
                        game.pick_from_embed(req_data.move_data)
                    elif game.curr_move_type == "TAKE_FROM_PLAYED": 
                        game.take_from_played(req_data.move_data)
                    elif game.curr_move_type == "CHECK_PLAYER_CARDS": 
                        game.check_player_cards(req_data.move_data)
                    elif game.curr_move_type == "PICK_PLAYER_PICK_CARD": 
                        game.pick_player_pick_card(req_data.move_data)
                    elif game.curr_move_type == "CHECK_EMBED_CARDS":
                        game.check_embed_cards(req_data.move_data)
                    elif game.curr_move_type == "MOVE_IMPED_CARD":
                        game.move_imped_card(req_data.move_data)
                    elif game.curr_move_type == "EXCHANGE_WITH_EMBED":
                        game.exchange_with_embed(req_data.move_data)
                    elif game.curr_move_type == "PICK_PLAYER": 
                        game.pick_player(req_data.move_data)      
                    for pid in game.pid_int_map.keys():
                        personal_state: PersonalState = game.get_personal_state(pid)
                        await manager.send_personal_message(message=WsResponse(state=personal_state), game_id=game_id, pid=pid)


                elif game.curr_move_type in INTER_MOVE_TYPES:
                    if game.curr_move_type == "EXCHANGE_CARD":
                        game.collect_interdata(pid, req_data.move_data)
                        if game.inter_is_ready(req_num=2):
                            game.exchange_card()
                            for pid in game.pid_int_map.keys():
                                personal_state: PersonalState = game.get_personal_state(pid)
                                await manager.send_personal_message(message=WsResponse(state=personal_state), game_id=game_id, pid=pid)

                    elif game.curr_move_type == "CHECK_FANREN_PLAYER": 
                        game.collect_interdata(pid, req_data.move_data)
                        if game.inter_is_ready(req_num=2):
                            game.check_fanren_player()
                            for pid in game.pid_int_map.keys():
                                personal_state: PersonalState = game.get_personal_state(pid)
                                await manager.send_personal_message(message=WsResponse(state=personal_state), game_id=game_id, pid=pid)

                    elif game.curr_move_type == "GIVE_TO_NEXT": 
                        game.collect_interdata(pid, req_data.move_data)
                        if game.inter_is_ready(req_num=4):
                            game.give_to_next()
                            for pid in game.pid_int_map.keys():
                                personal_state: PersonalState = game.get_personal_state(pid)
                                await manager.send_personal_message(message=WsResponse(state=personal_state), game_id=game_id, pid=pid)
                                
            except GameError as e:
                await websocket.send_json(WsResponse(code=400, msg=e.code))
                continue

    except WebSocketDisconnect:
        game.quit_player(pid)
        manager.disconnect(game_id, pid)
        await websocket.close(code=2000)
        manager.broadcast(message=WsResponse(code=500, msg=f"LEAVING_GAME_{pid}"))

# TODO: 注意现在的逻辑每开一盘游戏新分配唯一ID，跟登录无关，感觉是适合分布式的。记得处理错误traceback和逻辑整合
# TODO: Timeout 功能
# TODO: 锁
# TODO: 错误类型    
# TODO: 目前是只实现了 advanced mode
# TODO: AUTH