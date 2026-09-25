from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional


SUITS = ["♥", "♦", "♣", "♠"]
RANKS = [
    "2", "3", "4", "5", "6", "7", "8",
    "9", "10", "J", "Q", "K", "A",
]


@dataclass
class Card:
    suit: str
    rank: str

    def to_dict(self):
        return {
            "suit": self.suit,
            "rank": self.rank,
        }


@dataclass
class Player:
    id: int
    name: str
    cards: List[Card] = field(default_factory=list)
    tricks: int = 0

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "cards": [c.to_dict() for c in self.cards],
            "tricks": self.tricks,
        }


@dataclass
class GameRoom:
    game_id: str
    creator_id: int
    creator_name: str
    max_players: int = 4

    players: Dict[int, Player] = field(
        default_factory=dict
    )

    started: bool = False
    hakim_id: Optional[int] = None
    hokm: Optional[str] = None

    current_player_id: Optional[int] = None

    current_trick: List[dict] = field(
        default_factory=list
    )

    scores: Dict[int, int] = field(
        default_factory=dict
    )

    winner_id: Optional[int] = None

    def add_player(
        self,
        player_id: int,
        player_name: str,
    ):
        if player_id in self.players:
            return self.players[player_id]

        if self.started:
            raise ValueError(
                "بازی شروع شده و بازیکن جدید نمی‌تواند وارد شود."
            )

        if len(self.players) >= self.max_players:
            raise ValueError(
                "ظرفیت اتاق تکمیل است."
            )

        player = Player(
            id=player_id,
            name=player_name,
        )

        self.players[player_id] = player
        self.scores[player_id] = 0

        return player


class GameState:
    def __init__(self):
        self.games: Dict[str, GameRoom] = {}

    # --------------------------------------------
    # ساخت اتاق
    # --------------------------------------------

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
            creator_name=creator_name,
            max_players=max_players,
        )

        game.add_player(
            creator_id,
            creator_name,
        )

        self.games[game_id] = game

        return game

    # --------------------------------------------
    # گرفتن اتاق
    # --------------------------------------------

    def get_game(
        self,
        game_id: str,
    ) -> GameRoom:

        if game_id not in self.games:
            raise ValueError(
                "اتاق بازی پیدا نشد."
            )

        return self.games[game_id]

    # --------------------------------------------
    # اضافه کردن بازیکن
    # --------------------------------------------

    def add_player(
        self,
        game_id: str,
        player_id: int,
        player_name: str,
    ) -> Player:

        game = self.get_game(game_id)

        return game.add_player(
            player_id,
            player_name,
        )

    # --------------------------------------------
    # شروع بازی
    # --------------------------------------------

    def start_game(
        self,
        game_id: str,
    ) -> GameRoom:

        game = self.get_game(game_id)

        if game.started:
            return game

        if len(game.players) < game.max_players:
            raise ValueError(
                "هنوز تعداد بازیکنان کامل نشده است."
            )

        deck = [
            Card(
                suit=suit,
                rank=rank,
            )
            for suit in SUITS
            for rank in RANKS
        ]

        random.shuffle(deck)

        players = list(
            game.players.values()
        )

        # پخش کارت
        for player in players:
            player.cards.clear()
            player.tricks = 0

        for index, card in enumerate(deck):
            players[
                index % len(players)
            ].cards.append(card)

        # حکم
        hakim = random.choice(players)

        game.hakim_id = hakim.id

        game.current_player_id = hakim.id

        game.started = True

        game.hokm = None

        game.current_trick.clear()

        return game

    # --------------------------------------------
    # تعیین حکم
    # --------------------------------------------

    def set_hokm(
        self,
        game_id: str,
        player_id: int,
        suit: str,
    ) -> GameRoom:

        game = self.get_game(game_id)

        if not game.started:
            raise ValueError(
                "بازی هنوز شروع نشده است."
            )

        if game.hakim_id != player_id:
            raise ValueError(
                "فقط حاکم می‌تواند حکم را تعیین کند."
            )

        if suit not in SUITS:
            raise ValueError(
                "خال نامعتبر است."
            )

        game.hokm = suit

        return game

    # --------------------------------------------
    # کارت‌های مجاز
    # --------------------------------------------

    def legal_cards(
        self,
        game_id: str,
        player_id: int,
    ) -> List[Card]:

        game = self.get_game(game_id)

        if player_id not in game.players:
            raise ValueError(
                "بازیکن در این اتاق نیست."
            )

        player = game.players[player_id]

        if not game.current_trick:
            return player.cards

        lead_suit = game.current_trick[0]["card"][
            "suit"
        ]

        same_suit = [
            card
            for card in player.cards
            if card.suit == lead_suit
        ]

        if same_suit:
            return same_suit

        return player.cards

    # --------------------------------------------
    # بازی کردن کارت
    # --------------------------------------------

    def play_card(
        self,
        game_id: str,
        player_id: int,
        suit: str,
        rank: str,
    ) -> GameRoom:

        game = self.get_game(game_id)

        if not game.started:
            raise ValueError(
                "بازی هنوز شروع نشده است."
            )

        if game.hokm is None:
            raise ValueError(
                "ابتدا باید حکم مشخص شود."
            )

        if game.current_player_id != player_id:
            raise ValueError(
                "الان نوبت شما نیست."
            )

        player = game.players.get(
            player_id
        )

        if player is None:
            raise ValueError(
                "بازیکن پیدا نشد."
            )

        selected = None

        for card in player.cards:
            if (
                card.suit == suit
                and card.rank == rank
            ):
                selected = card
                break

        if selected is None:
            raise ValueError(
                "این کارت در دست شما نیست."
            )

        legal = self.legal_cards(
            game_id,
            player_id,
        )

        if not any(
            c.suit == selected.suit
            and c.rank == selected.rank
            for c in legal
        ):
            raise ValueError(
                "این کارت در این نوبت مجاز نیست."
            )

        player.cards.remove(selected)

        game.current_trick.append(
            {
                "player_id": player_id,
                "player_name": player.name,
                "card": selected.to_dict(),
            }
        )

        # هنوز چهار کارت کامل نشده
        if len(game.current_trick) < len(
            game.players
        ):
            ids = list(game.players.keys())

            index = ids.index(player_id)

            game.current_player_id = ids[
                (index + 1) % len(ids)
            ]

            return game

        # تعیین برنده دست
        winner_id = self._trick_winner(
            game
        )

        game.players[
            winner_id
        ].tricks += 1

        game.scores[
            winner_id
        ] += 1

        game.current_player_id = winner_id

        # اگر هنوز کارت دارند، برنده دست بعدی را شروع می‌کند
        if any(
            player.cards
            for player in game.players.values()
        ):
            game.current_trick = []

        else:
            game.winner_id = winner_id

        return game

    # --------------------------------------------
    # برنده دست
    # --------------------------------------------

    def _trick_winner(
        self,
        game: GameRoom,
    ) -> int:

        lead_suit = game.current_trick[0][
            "card"
        ]["suit"]

        rank_value = {
            rank: index
            for index, rank in enumerate(
                RANKS
            )
        }

        best = None

        for item in game.current_trick:

            card = item["card"]

            value = rank_value[
                card["rank"]
            ]

            strength = value

            if card["suit"] == lead_suit:
                strength += 100

            if card["suit"] == game.hokm:
                strength += 200

            if (
                best is None
                or strength > best[0]
            ):
                best = (
                    strength,
                    item["player_id"],
                )

        return best[1]

    # --------------------------------------------
    # اطلاعات بازی
    # --------------------------------------------

    def state_for_player(
        self,
        game_id: str,
        player_id: int,
    ) -> dict:

        game = self.get_game(game_id)

        players = []

        for player in game.players.values():

            cards = []

            # فقط کارت‌های خود بازیکن نمایش داده می‌شود
            if player.id == player_id:
                cards = [
                    c.to_dict()
                    for c in player.cards
                ]

            players.append(
                {
                    "id": player.id,
                    "name": player.name,
                    "cards": cards,
                    "card_count": len(
                        player.cards
                    ),
                    "tricks": player.tricks,
                }
            )

        return {
            "game_id": game.game_id,
            "creator_id": game.creator_id,
            "max_players": game.max_players,
            "started": game.started,
            "players": players,
            "player_count": len(
                game.players
            ),
            "hakim_id": game.hakim_id,
            "hokm": game.hokm,
            "current_player_id": (
                game.current_player_id
            ),
            "current_trick": game.current_trick,
            "scores": game.scores,
            "winner_id": game.winner_id,
        }


game_state = GameState()
