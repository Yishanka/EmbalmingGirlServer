import random
from app.model import Card, SingleMoveData, InterMoveData, Player, GameState, PersonalState, GameInfo
from app.error import GameError
import app.error as err
import asyncio
import time

# <===== global const =====>
MAX_NUM_PLAYERS = 6
MIN_NUM_PLAYERS = 3

# single move type
DEFAULT = "DEFAULT"
TAKE_FROM_PLAYED = "TAKE_FROM_PLAYED"
CHECK_PLAYER_CARDS = "CHECK_PLAYER_CARDS"
CHECK_EMBED_CARDS = "CHECK_EMBED_CARDS"
MOVE_IMPED_CARD = "MOVE_IMPED_CARD"
PICK_FROM_EMBED = "PICK_FROM_EMBED"
EXCHANGE_WITH_EMBED = "EXCHANGE_WITH_EMBED"
PICK_PLAYER_PICK_CARD = "PICK_PLAYER_PICK_CARD"
PICK_PLAYER = "PICK_PLAYER"
SINGLE_MOVE_TYPES: list[str] = [
    DEFAULT, TAKE_FROM_PLAYED, CHECK_PLAYER_CARDS, CHECK_EMBED_CARDS, MOVE_IMPED_CARD, PICK_FROM_EMBED, PICK_PLAYER_PICK_CARD, PICK_PLAYER
]

# interact move type
EXCHANGE_CARD = "EXCHANGE_CARD"
CHECK_FANREN_PLAYER = "CHECK_FANREN_PLAYER"
GIVE_TO_NEXT = "GIVE_TO_NEXT"
INTER_MOVE_TYPES: list[str] = [
    EXCHANGE_CARD, CHECK_FANREN_PLAYER, GIVE_TO_NEXT
]

# success type
ADD_PLAYER = "ADD_PLAYER"
START_GAME = "START_GAME"
QUIT_PLAYER = "QUIT_PLAYER"

PLYAER_NUM_EMP_POINTS: dict = {
    3: 9,
    4: 8,
    5: 7,
    6: 6,
}

# <===== Game Class =====>
class Game:
    def __init__(self, 
                #  game_id: str, 
                #  mode: bool, 
                 set_num: int,
                 timeout: float = 30.0):
        if ((set_num < MIN_NUM_PLAYERS) or set_num > MAX_NUM_PLAYERS):
            raise GameError(err.INVALID_PLAYER_NUM)
        
        # self.id: str = game_id
        
        self.players: list[Player] = []
        
        # self.hand_cards: dict[int, list[Card]] = {}
        # self.imped_cards: dict[int, list[tuple[int, Card]]] = {} # tpid, pid, c
        # self.checked_player_cards: dict[int, dict[int, list[str]]] = {}
        # self.checked_embed_cards: dict[int, list[str]] = {}
        # self.checked_players: dict[int, list[int]] = {}

        self.played_cards: list[tuple[str, Card]] = []
        self.embed_cards: list[tuple[str, Card]] = [] # pid, c

        self.curr: int = None # 只负责三大操作的处理
        self.jump_curr: int = None
        
        # self.advanced_mode: bool = mode

        self.set_num: int = set_num
        self.started: bool = False
        self.finished: bool = False
        
        # self.avail_ids: set[int] = set([x for x in range(set_num)])
        self.pid_int_map: dict[str, int] = {}
        
        self.curr_move_type: str = DEFAULT
        self.jump_move_type: str = DEFAULT

        # self.timeout: float = timeout
        # self.start_time: float = 0.0

        self.inter_move_data: InterMoveData = None
        self.inter_data_num: int = 0

        self.timer_started: bool = False

        # self.permitted = False
        # self.op_lock = asyncio.Lock()
    
    def get_info(self) -> GameInfo:
        return GameInfo(
            game_id=None,
            set_num=self.set_num,
            num_players=len(self.players),
            started=self.started
        )
    
    def get_state(self) -> GameState:
        winners = self._calc_winner()
        return GameState(
            players=self.players,
            played_cards = self.played_cards,
            embed_cards=self.embed_cards,
            curr=self.curr,
            # set_num=self.set_num,
            started=self.started,
            finished=self.finished,
            curr_move_type=self.curr_move_type,
            jump_move_type=self.jump_move_type,
            winners = winners,
        )
    
    def get_personal_state(self, pid: str) -> PersonalState:
        winners = self._calc_winner()
        try:
            player: Player = [p for p in self.players if p.pid == pid][0]
            other_players: list[Player] = [p for p in self.players if p.pid != pid]
        except:
            raise GameError(err.INVALID_PLAYER_ID)
        return PersonalState(
            player=player,
            other_cards_num={
                p.pid: len(p.hand_cards)
                for p in other_players
            },
            other_imped_cards={
                p.pid: [c[0] for c in p.imped_cards]
                for p in other_players
            },
            played_cards = self.played_cards,
            embed_cards=[c[0] for c in self.embed_cards],
            curr=self.curr,
            # set_num=self.set_num,
            started=self.started,
            finished=self.finished,
            curr_move_type=self.curr_move_type,
            winners = winners,
        )
        
    def _next(self):
        for _ in range(len(self.players)):
            self.curr = (self.curr + 1) % len(self.players) 
            if len(self.players[self.curr].hand_cards) > 1:
                if self.jump_curr and (self.jump_curr == self.curr):
                    self.curr_move_type = self.jump_move_type
                    self.jump_curr = None
                    self.jump_move_type = None
                return
        # no next player, game is finished
        self.finished = True
    
    def add_player(self, pid: str):
        if self.started:
            raise GameError(err.INVALID_MOVE)
        if len(self.players) == self.set_num:
            raise GameError(err.INVALID_PLAYER_NUM)
        if pid in self.pid_int_map.keys():
            raise GameError(err.INVALID_PLAYER_ID)
        
        self.players.append(Player(pid=pid))
        self.pid_int_map[pid] = len(self.players) - 1
    
    def quit_player(self, pid: str):
        if not self.started:
            raise GameError(err.INVALID_MOVE)
        if len(self.players) == 0:
            raise GameError(err.INVALID_PLAYER_NUM)
        try:
            self.pid_int_map.pop(pid)
        except:
            raise GameError(err.INVALID_PLAYER_ID)

        self.players = [p for p in self.players if p.pid != pid]
        for i, p in enumerate(self.players):
            self.pid_int_map[p.pid] = i
        
    def _calc_winner(self) -> list[str]:
        if self.finished == False:
            return []
        winner: list[str] = []

        for p in self.players:
            if len(p.hand_cards) != 1:
                raise GameError(err.INVALID_WIN_COND)

        embed_points: int = sum([c.point for _, c in self.embed_cards])
        imped_points: dict[str, int] = {
            p.pid: sum([c.point for _, c in p.imped_cards])
            for p in self.players
        }
        max_imped_points = max(imped_points.values())
        
        # if waixingren imped, waixingren wins
        max_imped_pids: list[str] = [k for k, v in imped_points.items() if v == max_imped_points]
        if len(max_imped_pids) != len(self.players):
            winner = [pid for pid in max_imped_points if self.players[self.pid_int_map[pid]].hand_cards[0].name == 'wai-xing-ren']
            if len(winner) == 1:
                return winner
        else:
            max_imped_pids = []
        
        # if emb fails, ganranzhe wins
        if embed_points < PLYAER_NUM_EMP_POINTS[len(self.players)]:
            winner = [p.pid for p in self.players if p.hand_cards[0].name == 'gan-ran-zhe']
            if len(winner) == 1:
                return winner
        
        # if fanren not imped, fanren and gongfan win
        n_max_imped_pids: list[str] = [k for k in range(len(self.players)) if k not in max_imped_pids]
        winner = [pid for pid in n_max_imped_pids if self.players[self.pid_int_map[pid]].hand_cards[0].name == 'fan-ren']
        if len(winner) == 1:
            winner.extend([p.pid for p in self.players if p.hand_cards[0].name == 'gong-fan'])
            return winner
        
        # if emb points >= required, good characters win
        if embed_points >= PLYAER_NUM_EMP_POINTS[len(self.players)]:
            good_names = [
                'xue-sheng-hui-zhang', 
                'bao-jian-wei-yuan',
                'tu-shu-wei-yuan',
                'feng-ji-wei-yuan',
                'da-xiao-jie',
                'xin-wen-bu',
                'ban-zhang',
                'you-deng-sheng',
            ]
            winner = [p.pid for p in self.players if p.hand_cards[0].name in good_names]
            if len(winner) != 0:
                return winner
        
        # no one wins then guizhaibu wins
        winner = [p.pid for p in self.players if p.hand_cards[0].name == 'gui-zhai-bu']
        if len(winner) != 0:
            return winner
        
        return winner
        
    def start_game(self):
        if self.started:
            raise GameError(err.INVALID_MOVE)
        if (len(self.players) != self.set_num):
            raise GameError(err.INVALID_PLAYER_NUM)
        
        self.started = True
        self.curr_move_type = DEFAULT
        
        # generate deck
        deck: list[Card] = (
            [Card(name='xue-sheng-hui-zhang', point=3)] * 3 +
            [Card(name='bao-jian-wei-yuan', point=1)] * 2 +
            [Card(name='tu-shu-wei-yuan', point=1)] * (3 if len(self.players) == 5 else 2) +
            [Card(name='feng-ji-wei-yuan', point=1)] * (1 if len(self.players) == 3 else 2) +
            [Card(name='da-xiao-jie', point=1)] * (2 if len(self.players) == 3 else 3) +
            [Card(name='xin-wen-bu', point=1)] * (2 if len(self.players) == 3 else 3) +
            [Card(name='ban-zhang', point=2)] * 2 +
            [Card(name='you-deng-sheng', point=2)] * (1 if len(self.players) == 3 else 2) +
            [Card(name='fan-ren', point=0)] * 1 +
            [Card(name='gong-fan', point=0)] * (0 if len(self.players) == 3 else 1) +
            [Card(name='wai-xing-ren', point=-1)] * 1 +
            [Card(name='gan-ran-zhe', point=0)] * 1 +
            [Card(name='gui-zhai-bu', point=0)] * (2 if len(self.players) == 3 else 3)
        )
        num_card_p = len(deck) // len(self.players)
        
        # dispatch cards
        random.shuffle(deck)
        for p in self.players:
            p.hand_cards = deck[:num_card_p]
            deck = deck[num_card_p:]

        # determine start player
        for i, p in enumerate(self.players):
            start_card = [x for x in p.hand_cards if x.name == 'xue-sheng-hui-zhang']
            if (len(start_card) > 0):
                self.curr = i
                break
        

    def inter_is_ready(self, req_num: int) -> bool:
        return self.inter_data_num == req_num 
    
    def timer(self, duration: float) -> bool:
        if self.timer_started == True:
            return False
        
        import time
        start: float = time.time()
        while (True):
            if time.time() - start >= duration:
                self.timer_started = False
                return True

    def collect_interdata(self, pid: str, move_data: SingleMoveData):
        try:
            self.inter_data_num += 1
            self.inter_move_data.ops[pid] = move_data
        except:
            raise GameError(err.INVALID_MOVE)

    # moves
    def emb_card(self, move_data: SingleMoveData):
        try: 
            assert self.curr_move_type == DEFAULT
            if self.players[self.curr].hand_cards[move_data.cindexs[0]].name == 'fan-ren':
                raise GameError(err.INVALID_MOVE, "不可主动使用犯人卡")
            embed_card: Card = self.players[self.curr].hand_cards.pop(move_data.cindexs[0])
        except GameError as e:
            raise GameError(e.code, e.detail)
        except Exception:
            raise GameError(err.INVALID_MOVE)
        
        self.embed_cards.append((self.players[self.curr].pid, embed_card))
        self._next()
    
    def imp_card(self, move_data: SingleMoveData):
        try: 
            assert self.curr_move_type == DEFAULT
            if self.players[self.curr].hand_cards[move_data.cindexs[0]].name == 'fan-ren':
                raise GameError(err.INVALID_MOVE, "不可主动使用犯人卡")
            imped_card: Card = self.players[self.curr].hand_cards.pop(move_data.cindexs[0])
        except GameError as e:
            raise GameError(e.code, e.detail)
        except Exception:
            raise GameError(err.INVALID_MOVE)
        
        self.players[self.pid_int_map[move_data.tpids[0]]].imped_cards.append((self.players[self.curr].pid, imped_card))
        self._next()  

    def play_card(self, move_data: SingleMoveData):
        try:
            assert self.curr_move_type == DEFAULT
            if self.players[self.curr].hand_cards[move_data.cindexs[0]].name == 'fan-ren':
                raise GameError(err.INVALID_MOVE, "不可主动使用犯人卡")
            played_card: Card = self.players[self.curr].hand_cards.pop(move_data.cindexs[0])
        except GameError as e:
            raise GameError(e.code, e.detail)
        except Exception:
            raise GameError(err.INVALID_MOVE)

        # played_card.visible = True
        self.played_cards.append((self.players[self.curr].pid, played_card))

        # single move type
        if played_card.name == 'bao-jian-wei-yuan':
            self.curr_move_type = TAKE_FROM_PLAYED
        elif played_card.name == 'feng-ji-wei-yuan':
            self.curr_move_type = CHECK_PLAYER_CARDS 
        elif played_card.name == 'da-xiao-jie':
            self.curr_move_type = PICK_PLAYER_PICK_CARD
        elif played_card.name == 'you-deng-sheng':
            self.curr_move_type = CHECK_EMBED_CARDS
        elif played_card.name == 'gong-fan':
            self.curr_move_type = MOVE_IMPED_CARD
        elif played_card.name == 'gan-ran-zhe':
            self.jump_curr = self.curr
            self.jump_move_type = PICK_FROM_EMBED
        elif played_card.name == 'gui-zhai-bu':
            self.curr_move_type = EXCHANGE_WITH_EMBED

        # interact move type
        elif played_card.name == 'ban-zhang':
            self.curr_move_type = PICK_PLAYER
        elif played_card.name == 'you-deng-sheng':
            self.curr_move_type = CHECK_FANREN_PLAYER
        elif played_card.name == 'xin-wen-bu':
            self.curr_move_type = GIVE_TO_NEXT

    def take_from_played(self, move_data: SingleMoveData):
        try:
            assert self.curr_move_type == TAKE_FROM_PLAYED
            taken_card: Card = self.played_cards.pop(move_data.cindexs[0])[1]
        except:
            raise GameError(err.INVALID_MOVE)
        
        # taken_card.visible = False
        self.players[self.curr].hand_cards.append(taken_card)
        
        self.curr_move_type = DEFAULT
        self._next()

    def check_fanren_player(self):
        try:
            assert self.curr_move_type == CHECK_FANREN_PLAYER
        except GameError as e:
            raise GameError(e.code)
        
        for t_pid, _ in self.inter_move_data.ops.items():
            tmp_1 = [c for c in self.players[self.pid_int_map[t_pid]].hand_cards if (c.name == 'fan-ren') or (c.name == 'wai-xing-ren')]
            if len(tmp_1) == 0:
                raise GameError(err.INVALID_MOVE)
            self.players[self.curr].checked_players.append(t_pid)

        self.inter_move_data = None
        self.curr_move_type = DEFAULT
        self._next()
        
    def check_player_cards(self, move_data: SingleMoveData):
        try:
            assert self.curr_move_type == CHECK_PLAYER_CARDS
        except GameError as e:
            raise GameError(e.code)
        
        t_pid: str = move_data.tpids[0]
        t_cards: list[Card] = [Card(c.name, c.point, 
                                        #  c.visible
                                         ) for c in self.players[self.pid_int_map[t_pid]].hand_cards]
        self.players[self.curr].checked_player_cards[t_pid] = t_cards
        self.curr_move_type = DEFAULT
        self._next()

    def pick_player_pick_card(self, move_data: SingleMoveData):
        try:
            assert self.curr_move_type == PICK_PLAYER_PICK_CARD
        except GameError as e:
            raise GameError(e.code)
        t_pid: str = move_data.tpids[0]
        try:
            card: Card = self.players[self.curr].hand_cards.pop(move_data.cindexs[0])
            t_card: Card = self.players[self.pid_int_map[t_pid]].hand_cards.pop(move_data.cindexs[1])
        except:
            raise GameError(err.INVALID_MOVE)
        
        self.players[self.curr].hand_cards.append(card)
        self.players[self.pid_int_map[t_pid]].hand_cards.append(t_card)

        self.curr_move_type = DEFAULT
        self._next()

    def pick_player(self, move_data: SingleMoveData):
        try:
            assert self.curr_move_type == PICK_PLAYER
        except GameError as e:
            raise GameError(e.code)
        
        self.t_pid_interact: str = move_data.tpids[0]
        self.curr_move_type = EXCHANGE_CARD
        
    def exchange_card(self):
        try:
            assert self.curr_move_type == EXCHANGE_CARD
        except GameError as e:
            raise GameError(e.code)
        
        ops: dict[str, SingleMoveData] = self.inter_move_data.ops
        pid, t_pid = ops.keys()
        try:
            card: Card = self.players[self.pid_int_map[pid]].hand_cards.pop(ops[pid].cindexs[0])
            t_card: Card = self.players[self.pid_int_map[t_pid]].hand_cards.pop(ops[t_pid].cindexs[0])
        except:
            raise GameError(err.INVALID_MOVE)
        
        self.players[self.pid_int_map[pid]].hand_cards.append(t_card)
        self.players[self.pid_int_map[t_pid]].hand_cards.append(card)

        self.inter_move_data = None
        self.curr_move_type = DEFAULT
        self._next()

    def give_to_next(self):
        try:
            assert self.curr_move_type == GIVE_TO_NEXT
        except GameError as e:
            raise GameError(e.code)
        try:
            for pid, move_data in self.inter_move_data.ops.items():
                player_pos: int = self.pid_int_map[pid]
                next_pos: int = (player_pos + 1) % self.set_num
                card: Card = self.players[player_pos].hand_cards.pop(move_data.cindexs[0])
                self.players[next_pos].hand_cards.append(card)
        except:
            raise GameError(err.INVALID_MOVE)

        self.curr_move_type = DEFAULT
        self._next()

    def check_embed_cards(self, move_data: SingleMoveData):
        try:
            assert self.curr_move_type == CHECK_EMBED_CARDS
        except GameError as e:
            raise GameError(e.code)
        
        embed_cards: list[tuple[str, Card]] = [(pid, Card(c.name, c.point, 
                                                        #   c.visible
                                                          )) for pid, c in self.embed_cards]
        self.players[self.curr].checked_embed_cards = embed_cards
        
        self.curr_move_type = DEFAULT
        self._next()

    def move_imped_card(self, move_data: SingleMoveData):
        try:
            assert self.curr_move_type == MOVE_IMPED_CARD
        except GameError as e:
            raise GameError(e.code)
        
        tpid_1: str = move_data.tpids[0]
        tpid_2: str = move_data.tpids[1]
        tcindex: int = move_data.cindexs[0]
        
        try:
            moved_p_card: tuple[int, Card] = self.players[self.pid_int_map[tpid_1]].imped_cards.pop(tcindex)
        except:
            raise GameError(err.INVALID_MOVE)
        
        self.players[self.pid_int_map[tpid_2]].imped_cards.append(moved_p_card)

        self.curr_move_type = DEFAULT
        self._next()
    
    def pick_from_embed(self, move_data: SingleMoveData):
        try:
            assert self.curr_move_type == PICK_FROM_EMBED
        except GameError as e:
            raise GameError(e.code)
        
        try:
            card: Card = self.embed_cards.pop(move_data.cindexs[0])[1]
        except Exception as e:
            raise GameError(err.INVALID_MOVE)
        
        self.players[self.curr].hand_cards.append(card)
        self.curr_move_type = DEFAULT
        # no next, this move specifically for gan-ran-zhe, which means next is still him
        # todo: check whether gan-ran-zhe should be in embed card

    def exchange_with_embed(self, move_data: SingleMoveData):
        try:
            assert self.curr_move_type == EXCHANGE_WITH_EMBED
        except GameError as e:
            raise GameError(e.code)
        
        try:
            card_1: Card = self.players[self.curr].hand_cards.pop(move_data.cindexs[0])
            card_2: Card = self.embed_cards.pop(move_data.cindexs[1])[1]
        except Exception as e:
            raise GameError(err.INVALID_MOVE, str(e))
        
        self.players[self.curr].hand_cards.append(card_2)
        
        self.embed_cards.append(([pid for pid, p in self.pid_int_map.items() if p == self.curr][0], card_1))
        self.curr_move_type = DEFAULT
        self._next()

    # def _check_move_data_num(self, move_data: MoveData, num_pids: int, num_tpids: int, num_cindexs: int):
    #     try: 
    #         assert len(move_data.pids) == num_pids
    #         assert len(move_data.tpids) == num_tpids
    #         assert len(move_data.cindexs) == num_cindexs
    #     except Exception as e:
    #         raise GameError(err.INVALID_MOVE)

    # def _check_curr(self, move_data: MoveData):
    #     try:
    #         assert self.pid_int_map[move_data.pids[0]] == self.curr
    #     except:
    #         raise GameError(err.INVALID_PLAYER_ID)
    
    # def _check_move_type(self, move_type: str, move_type_1: str=None):
    #     try:
    #         if move_type_1:
    #             assert (self.curr_move_type == move_type) or (self.curr_move_type == move_type_1)
    #         else:
    #             assert self.curr_move_type == move_type
    #     except:
    #         raise GameError(err.INVALID_MOVE)
        
    # def _check_fan_ren(self, move_data: MoveData):
    #     try:
    #         assert self.players[self.curr].hand_cards[move_data.cindexs[0]].name != 'fan-ren'
    #     except:
    #         raise GameError(err.INVALID_MOVE)

# both: fanren can't be played, embalm, imprison
# advanced: 
# ordinary: waixingren no imprision other, last card can't be moved

if __name__ == '__main__':
    # ns = [1, 2, 3, 4, 5]
    # s = ''
    # for n in ns:
        # s += f'_{n}'
    hand_cards = {
        1: [Card('A', 1), Card('B', 2)],
        2: [Card('C', 3)]
    }
    print("=== 测试各种拷贝方法 ===")

    # 1. 错误方法：浅拷贝两次
    print("\n1. 浅拷贝两次:")
    t1 = hand_cards[1].copy().copy()
    print(t1)
    hand_cards[1][0].name = 'CHANGED'
    print(f"  原始卡片名称: {hand_cards[1][0].name}")
    print(f"  副本卡片名称: {t1[0].name}")  # ❌ 也被修改了