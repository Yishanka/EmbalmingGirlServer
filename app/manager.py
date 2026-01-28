from fastapi import WebSocket

from fastapi import WebSocket
from typing import Optional, List
from model import *

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
            await websocket.send_json(message)

    async def broadcast(self, message: WsResponse, game_id: str, exclude_pid: Optional[str] = None):
        if game_id not in self.active_connections:
            return
        for pid, websocket in self.active_connections[game_id].items():
            if pid != exclude_pid:
                await websocket.send_json(message)

    def get_connection_count(self, game_id: str) -> int:
        return len(self.active_connections.get(game_id, {}))

    async def close_all_connections(self, game_id: str):
        if game_id not in self.active_connections:
            return
        for websocket in self.active_connections[game_id].values():
            await websocket.close(code=1001, reason="Game ended")
        del self.active_connections[game_id]

