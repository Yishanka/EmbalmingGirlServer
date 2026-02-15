from fastapi import WebSocket

from fastapi import WebSocket
from typing import Optional, List
from app.model import *

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, dict[str, WebSocket]] = {}

    async def connect(self, websocket: WebSocket, game_id: str, pid: str):
        await websocket.accept()
        if game_id not in self.active_connections:
            self.active_connections[game_id] = {}
        # 避免重复连接
        if pid in self.active_connections[game_id]:
            await self.disconnect(game_id, pid)
        self.active_connections[game_id][pid] = websocket

    def disconnect(self, game_id: str, pid: str):
        if game_id in self.active_connections and pid in self.active_connections[game_id]:
            del self.active_connections[game_id][pid]
            if not self.active_connections[game_id]:
                del self.active_connections[game_id]

    async def send_personal_message(self, message: WsResponse, game_id: str, pid: str):
        if game_id in self.active_connections and pid in self.active_connections[game_id]:
            websocket = self.active_connections[game_id][pid]
            # WsResponse is a Pydantic model; convert to dict for JSON serialization
            try:
                await websocket.send_json(message.dict())
            except Exception:
                # If sending fails (client closed), clean up the connection
                try:
                    await websocket.close()
                except Exception:
                    pass
                self.disconnect(game_id, pid)

    async def broadcast(self, message: WsResponse, game_id: str, exclude_pid: Optional[str] = None):
        if game_id not in self.active_connections:
            return
        # Iterate over a static list to allow removal during iteration
        for pid, websocket in list(self.active_connections[game_id].items()):
            if pid == exclude_pid:
                continue
            try:
                await websocket.send_json(message.dict())
            except Exception:
                try:
                    await websocket.close()
                except Exception:
                    pass
                self.disconnect(game_id, pid)

    def get_connection_count(self, game_id: str) -> int:
        return len(self.active_connections.get(game_id, {}))

    async def close_all_connections(self, game_id: str):
        if game_id not in self.active_connections:
            return
        for websocket in self.active_connections[game_id].values():
            await websocket.close(code=1001, reason="Game ended")
        del self.active_connections[game_id]

