from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional


SUITS = ["♥", "♦", "♣", "♠"]

RANKS = list(range(2, 15))

RANK_NAMES = {
    11: "J",
    12: "Q",
    13: "K",
    14: "A",
}


@dataclass
class Card:
    suit: str
    rank: int

    def to_dict(self) -> dict:
        return {
            "suit": self.suit,
            "rank": self.rank,
            "label": RANK_NAMES.get(
                self.rank,
                str(self.rank),
            ),
        }


@dataclass
class Player:
    id: int
    name: str
    is_bot: bool = False

    cards: list[Card] = field(
        default_factory=list
    )

    tricks: int = 0


@dataclass
class GameRoom:
    game_id: str
    creator_id: int

    # حالت انتخاب‌شده توسط سازنده
    mode: int = 4

    # تعداد صندلی‌های میز
    seat_count: int = 4

    players: list[Player] = field(
        default_factory=list
    )

    started: bool = False
    finished: bool = False

    phase: str = "waiting"

    hakim_id: Optional[int] = None

    hokm: Optional[str] = None

    current_player_id: Optional[int] = None

    lead_suit: Optional[str] = None

    current_trick: list[dict] = field(
        default_factory=list
    )

    winner_id: Optional[int] = None

    team_a_score: int = 0
    team_b_score: int = 0

    deck: list[Card] = field(
        default_factory=list
    )


class GameState:

    def __init__(self):
        self.games: dict[str, GameRoom] = {}

    def create_game(
        self,
        game_id: str,
        creator_id: int,
        creator_name: str,
        max_players: int = 4,
    ) -> GameRoom:

        if max_players not in (1, 2, 4):
            max_players = 4

        game = GameRoom(
            game_id=game_id,
            creator_id=creator_id,
            mode=max_players,
            seat_count=4,
        )

        game.players.append(
            Player(
                id=creator_id,
                name=creator_name,
                is_bot=False,
            )
        )

        self.games[game_id] = game

        return game

    def get_game(
        self,
        game_id: str,
    ) -> Optional[GameRoom]:

        return self.games.get(game_id)

    def get_player(
        self,
        game: GameRoom,
        player_id: int,
    ) -> Optional[Player]:

        for player in game.players:
            if player.id == player_id:
                return player

        return None

    def add_player(
        self,
        game_id: str,
        player_id: int,
        player_name: str,
    ) -> tuple[bool, str]:

        game = self.get_game(game_id)

        if not game:
            return False, "بازی پیدا نشد."

        if game.started:
            return False, "بازی شروع شده است."

        if any(
            player.id == player_id
            for player in game.players
        ):
            return True, "شما قبلاً وارد بازی شده‌اید."

        # حالت تک‌نفره فقط برای سازنده است.
        if game.mode == 1:
            return False, "این بازی تک‌نفره است."

        if len(game.players) >= game.mode:
            return False, "ظرفیت بازیکنان واقعی تکمیل است."

        game.players.append(
            Player(
                id=player_id,
                name=player_name,
                is_bot=False,
            )
        )

        return True, "با موفقیت وارد بازی شدید."

    def fill_with_bots(
        self,
        game_id: str,
    ) -> tuple[bool, str]:

        game = self.get_game(game_id)

        if not game:
            return False, "بازی پیدا نشد."

        if game.started:
            return False, "بازی شروع شده است."

        # در حالت ۱ نفره:
        # ۱ انسان + ۳ ربات
        #
        # در حالت ۲ نفره:
        # تا ۲ بازیکن، بقیه صندلی‌ها ربات
        #
        # در حالت ۴ نفره:
        # فقط ۴ انسان مجاز هستند.

        if game.mode == 1:
            target_humans = 1
        elif game.mode == 2:
            target_humans = 2
        else:
            target_humans = 4

        if game.mode == 4:
            if len(game.players) != 4:
                return (
                    False,
                    "برای بازی ۴ نفره باید ۴ بازیکن حاضر باشند.",
                )

            return True, "میز کامل است."

        # برای حالت ۱ و ۲،
        # صندلی‌های خالی با ربات پر می‌شوند.
        while len(game.players) < 4:

            bot_number = len(
                [
                    p
                    for p in game.players
                    if p.is_bot
                ]
            ) + 1

            bot_id = -(
                100000
                + bot_number
            )

            game.players.append(
                Player(
                    id=bot_id,
                    name=f"بازیکن کامپیوتری {bot_number}",
                    is_bot=True,
                )
            )

        return True, "بازیکنان کامپیوتری اضافه شدند."

    def remove_player(
        self,
        game_id: str,
        player_id: int,
    ) -> tuple[bool, str]:

        game = self.get_game(game_id)

        if not game:
            return False, "بازی پیدا نشد."

        if game.started:
            return False, "بعد از شروع بازی امکان خروج وجود ندارد."

        if player_id == game.creator_id:
            return False, "سازنده نمی‌تواند خارج شود."

        before = len(game.players)

        game.players = [
            player
            for player in game.players
            if player.id != player_id
        ]

        if len(game.players) == before:
            return False, "شما در این بازی نیستید."

        return True, "از بازی خارج شدید."

    def _new_deck(self) -> list[Card]:

        return [
            Card(
                suit=suit,
                rank=rank,
            )
            for suit in SUITS
            for rank in RANKS
        ]

    def start_game(
        self,
        game_id: str,
        player_id: int,
    ) -> tuple[bool, str]:

        game = self.get_game(game_id)

        if not game:
            return False, "بازی پیدا نشد."

        if player_id != game.creator_id:
            return False, "فقط سازنده می‌تواند بازی را شروع کند."

        if game.started:
            return False, "بازی قبلاً شروع شده است."

        if game.mode == 4:

            if len(game.players) != 4:
                return (
                    False,
                    "برای بازی ۴ نفره باید ۴ بازیکن حاضر باشند.",
                )

        else:

            ok, message = self.fill_with_bots(
                game_id
            )

            if not ok:
                return False, message

        deck = self._new_deck()

        random.shuffle(deck)

        game.deck = deck

        for player in game.players:
            player.cards.clear()
            player.tricks = 0

        # انتخاب حاکم
        hakim = random.choice(
            game.players
        )

        game.hakim_id = hakim.id

        # ابتدا فقط ۵ کارت به هر بازیکن
        for _ in range(5):

            for player in game.players:

                if not game.deck:
                    break

                player.cards.append(
                    game.deck.pop()
                )

        game.started = True
        game.finished = False

        game.phase = "choose_hokm"

        game.hokm = None

        # حاکم باید حکم انتخاب کند
        game.current_player_id = game.hakim_id

        game.current_trick.clear()
        game.lead_suit = None

        game.winner_id = None

        game.team_a_score = 0
        game.team_b_score = 0

        return (
            True,
            "بازی شروع شد. حاکم باید حکم را انتخاب کند.",
        )

    def set_hokm(
        self,
        game_id: str,
        player_id: int,
        suit: str,
    ) -> tuple[bool, str]:

        game = self.get_game(game_id)

        if not game:
            return False, "بازی پیدا نشد."

        if not game.started:
            return False, "بازی هنوز شروع نشده است."

        if game.finished:
            return False, "بازی تمام شده است."

        if game.phase != "choose_hokm":
            return False, "زمان انتخاب حکم نیست."

        if player_id != game.hakim_id:
            return False, "فقط حاکم می‌تواند حکم را انتخاب کند."

        if suit not in SUITS:
            return False, "خال نامعتبر است."

        game.hokm = suit

        self._deal_remaining_cards(game)

        game.phase = "playing"

        game.current_player_id = game.hakim_id

        return (
            True,
            f"حکم {suit} انتخاب شد.",
        )

    def _deal_remaining_cards(
        self,
        game: GameRoom,
    ):

        if not game.deck:
            return

        player_index = 0

        while game.deck:

            player = game.players[
                player_index
                % len(game.players)
            ]

            player.cards.append(
                game.deck.pop()
            )

            player_index += 1

    def legal_cards(
        self,
        game: GameRoom,
        player_id: int,
    ) -> list[Card]:

        player = self.get_player(
            game,
            player_id,
        )

        if not player:
            return []

        if game.phase != "playing":
            return []

        if not game.current_trick:
            return list(player.cards)

        if not game.lead_suit:
            return list(player.cards)

        matching = [
            card
            for card in player.cards
            if card.suit == game.lead_suit
        ]

        if matching:
            return matching

        return list(player.cards)

    def play_card(
        self,
        game_id: str,
        player_id: int,
        suit: str,
        rank: int,
    ) -> tuple[bool, str]:

        game = self.get_game(game_id)

        if not game:
            return False, "بازی پیدا نشد."

        if not game.started:
            return False, "بازی هنوز شروع نشده است."

        if game.finished:
            return False, "بازی تمام شده است."

        if game.phase != "playing":
            return False, "ابتدا باید حکم انتخاب شود."

        if game.current_player_id != player_id:
            return False, "الان نوبت شما نیست."

        player = self.get_player(
            game,
            player_id,
        )

        if not player:
            return False, "بازیکن پیدا نشد."

        selected = None

        for card in player.cards:

            if (
                card.suit == suit
                and card.rank == rank
            ):
                selected = card
                break

        if selected is None:
            return False, "این کارت در دست شما نیست."

        legal = self.legal_cards(
            game,
            player_id,
        )

        if not any(
            card.suit == selected.suit
            and card.rank == selected.rank
            for card in legal
        ):
            return (
                False,
                "باید از خال شروع‌شده پیروی کنید.",
            )

        player.cards.remove(
            selected
        )

        if not game.current_trick:
            game.lead_suit = selected.suit

        game.current_trick.append(
            {
                "player_id": player_id,
                "player_name": player.name,
                "card": selected.to_dict(),
            }
        )

        if len(game.current_trick) < len(
            game.players
        ):

            current_index = game.players.index(
                player
            )

            next_index = (
                current_index + 1
            ) % len(game.players)

            game.current_player_id = (
                game.players[next_index].id
            )

            return True, "کارت بازی شد."

        winner_id = self._trick_winner(
            game
        )

        winner = self.get_player(
            game,
            winner_id,
        )

        if winner:
            winner.tricks += 1

        game.current_trick.clear()
        game.lead_suit = None

        cards_left = sum(
            len(player.cards)
            for player in game.players
        )

        if cards_left == 0:

            game.finished = True
            game.phase = "finished"
            game.winner_id = winner_id
            game.current_player_id = None

            return True, "بازی تمام شد."

        game.current_player_id = winner_id

        return True, "دست تمام شد."

    def _trick_winner(
        self,
        game: GameRoom,
    ) -> int:

        winner = game.current_trick[0]

        for current in game.current_trick[1:]:

            if self._card_beats(
                game,
                current["card"],
                winner["card"],
            ):
                winner = current

        return winner["player_id"]

    def _card_beats(
        self,
        game: GameRoom,
        current: dict,
        best: dict,
    ) -> bool:

        current_suit = current["suit"]
        current_rank = current["rank"]

        best_suit = best["suit"]
        best_rank = best["rank"]

        lead = game.lead_suit
        hokm = game.hokm

        if current_suit == best_suit:
            return current_rank > best_rank

        if current_suit == hokm:
            return best_suit != hokm

        if best_suit == hokm:
            return False

        if current_suit == lead:
            return best_suit != lead

        return False

    def bot_turn(
        self,
        game_id: str,
    ) -> Optional[dict]:

        game = self.get_game(
            game_id
        )

        if not game:
            return None

        if not game.started:
            return None

        if game.finished:
            return None

        current = self.get_player(
            game,
            game.current_player_id,
        )

        if not current:
            return None

        if not current.is_bot:
            return None

        # اگر ربات حاکم باشد،
        # خودش حکم را انتخاب می‌کند.
        if (
            game.phase == "choose_hokm"
            and current.id == game.hakim_id
        ):

            chosen = self._bot_choose_hokm(
                current
            )

            self.set_hokm(
                game_id,
                current.id,
                chosen,
            )

            return {
                "type": "hokm",
                "player_id": current.id,
                "suit": chosen,
            }

        if game.phase != "playing":
            return None

        legal = self.legal_cards(
            game,
            current.id,
        )

        if not legal:
            return None

        card = self._bot_choose_card(
            game,
            legal,
        )

        self.play_card(
            game_id,
            current.id,
            card.suit,
            card.rank,
        )

        return {
            "type": "card",
            "player_id": current.id,
            "card": card.to_dict(),
        }

    def _bot_choose_hokm(
        self,
        player: Player,
    ) -> str:

        counts = {
            suit: 0
            for suit in SUITS
        }

        for card in player.cards:
            counts[card.suit] += 1

        return max(
            counts,
            key=counts.get,
        )

    def _bot_choose_card(
        self,
        game: GameRoom,
        legal: list[Card],
    ) -> Card:

        # ربات فعلاً ضعیف ولی قانونی بازی می‌کند.
        return sorted(
            legal,
            key=lambda card: (
                card.rank,
                SUITS.index(card.suit),
            )
        )[0]

    def state_for_player(
        self,
        game_id: str,
        player_id: int,
    ) -> Optional[dict]:

        game = self.get_game(
            game_id
        )

        if not game:
            return None

        viewer = self.get_player(
            game,
            player_id,
        )

        if not viewer:
            return None

        hakim = self.get_player(
            game,
            game.hakim_id,
        )

        current = self.get_player(
            game,
            game.current_player_id,
        )

        players = []

        for player in game.players:

            visible_cards = []

            if player.id == player_id:

                visible_cards = [
                    card.to_dict()
                    for card in player.cards
                ]

            players.append(
                {
                    "id": player.id,
                    "name": player.name,
                    "is_bot": player.is_bot,
                    "cards": visible_cards,
                    "card_count": len(
                        player.cards
                    ),
                    "tricks": player.tricks,
                    "is_hakim": (
                        player.id
                        == game.hakim_id
                    ),
                    "is_turn": (
                        player.id
                        == game.current_player_id
                    ),
                }
            )

        if game.phase == "waiting":
            status_text = "منتظر شروع بازی"

        elif game.phase == "choose_hokm":

            if game.hakim_id == player_id:
                status_text = "👑 شما حاکم هستید؛ حکم را انتخاب کنید"
            else:
                status_text = (
                    f"👑 حاکم: {hakim.name if hakim else 'نامشخص'}"
                    " — منتظر انتخاب حکم"
                )

        elif game.phase == "playing":

            if game.current_player_id == player_id:
                status_text = "🎯 نوبت شماست"

            else:
                status_text = (
                    f"🎯 نوبت: "
                    f"{current.name if current else 'نامشخص'}"
                )

        elif game.phase == "finished":
            status_text = "🏆 بازی تمام شد"

        else:
            status_text = "در حال بازی"

        return {
            "game_id": game.game_id,

            "viewer_id": player_id,

            "creator_id": game.creator_id,

            "mode": game.mode,

            "max_players": game.mode,

            "seat_count": 4,

            "player_count": len(
                [
                    p
                    for p in game.players
                    if not p.is_bot
                ]
            ),

            "started": game.started,

            "finished": game.finished,

            "phase": game.phase,

            "status_text": status_text,

            "hakim_id": game.hakim_id,

            "hakim_name": (
                hakim.name
                if hakim
                else None
            ),

            "hokm": game.hokm,

            "current_player_id": (
                game.current_player_id
            ),

            "current_player_name": (
                current.name
                if current
                else None
            ),

            "lead_suit": game.lead_suit,

            "current_trick": (
                game.current_trick
            ),

            "winner_id": game.winner_id,

            "team_a_score": (
                game.team_a_score
            ),

            "team_b_score": (
                game.team_b_score
            ),

            "cards_left": sum(
                len(player.cards)
                for player in game.players
            ),

            "players": players,
        }


game_state = GameState()
