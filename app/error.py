# error type
INVALID_MOVE = "INVALID_MOVE"
INVALID_PLAYER_NUM = "INVALID_PLAYER_NUM"
INVALID_PLAYER_ID = "INVALID_PLAYER_ID"
INVALID_WIN_COND = "INVALID_WIN_COND"
INVALID_GAME_ID = "INVALID_GAME_ID"
INVALID_PARAMS = "INVALID_PARAMS"
SYSTEM_ERROR = "SYSTEM_ERROR"

class GameError(Exception):
    def __init__(self, code: str, detail: str = None):
        self.code = code
        self.detail = detail
        super().__init__(self.detail or self.code)