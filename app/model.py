from pydantic import BaseModel, Field
from typing import Optional, Generic, TypeVar

# game model
class Card(BaseModel):
    name: str
    point: int
    # visible: bool = False

class Player(BaseModel):
    pid: str = None
    hand_cards: list[Card] = []
    imped_cards: list[tuple[str, Card]] = []
    checked_player_cards: dict[str, list[Card]] = {}
    checked_embed_cards: list[tuple[str, Card]] = []
    checked_players: list[str] = []
    
class GameState(BaseModel):
    # game_id: str
    players: list[Player]
    played_cards: list[tuple[str, Card]]
    embed_cards: list[tuple[str, Card]] = [] # pid, c
    curr: int  
    # jump_curr: int
    set_num: int
    started: bool
    finished: bool
    curr_move_type: str
    winners: list[str]

class PersonalState(BaseModel):
    player: Player
    other_cards_num: dict[str, int] = {}
    other_imped_cards: dict[str, list[str]] = {}
    played_cards: list[tuple[str, Card]]
    embed_cards: list[str] = [] # pid
    curr: int  
    set_num: int
    started: bool
    finished: bool
    curr_move_type: str
    winners: list[str]

class SingleMoveData(BaseModel):
    tpids: list[str]
    cindexs: list[int]

class InterMoveData(BaseModel):
    ops: dict[str, SingleMoveData]
    
# request model: more detailed model type
class GameCreateRequest(BaseModel):
    set_num: int

class JoinGameRequest(BaseModel):
    game_id: str

class WsMoveRequest(BaseModel):
    type: str = Field(..., description="START/EMB/IMP/PLAY/CONT_PLAY")
    move_data: SingleMoveData = None

# response model
T = TypeVar("T")
class ApiResponse(BaseModel, Generic[T]):
    code: int = 200  # 200成功，4xx/5xx失败
    msg: str = "SUCCESS"  # 提示信息
    data: Optional[T] = None  # 业务数据（泛型，支持不同类型）

class WsResponse(BaseModel):
    code: int = 200  # 200成功，4xx/5xx失败
    msg: str = "SUCCESS"  # 提示信息
    state: Optional[PersonalState] = None


# class ExceptionPayload(BaseModel):
#     code: str
#     msg: str