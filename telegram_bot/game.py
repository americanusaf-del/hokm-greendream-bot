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
            "label": RANK_NAMES.get(self.rank, str(self.rank)),
        }


@dataclass
class Player:
    id: int
    name: str
    cards: list[Card] = field(default_factory=list)
    tricks: int = 0


@dataclass
class GameRoom:
    game_id: str
    creator_id: int
    players: list[Player] = field(default_factory=list)

    max_players: int = 4

    started: bool = False
    finished: bool = False

    hakim_id: Optional[int] = None
    hokm: Optional[str] = None

    current_player_id: Optional[int] = None

    lead_suit: Optional[str] = None

    current_trick: list[dict] = field(default_factory=list)

    winner_id: Optional[int] = None

    team_a_score: int = 0
    team_b_score: int = 0


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

        game = GameRoom(
            game_id=game_id,
            creator_id=creator_id,
            max_players=max_players,
        )

        game.players.append(
            Player(
                id=creator_id,
                name=creator_name,
            )
        )

        self.games[game_id] = game

        return game

    def get_game(self, game_id: str) -> Optional[GameRoom]:
        return self.games.get(game_id)

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

        for player in game.players:
            if player.id == player_id:
                return True, "شما قبلاً وارد بازی شده‌اید."

        if len(game.players) >= game.max_players:
            return False, "ظرفیت بازی تکمیل است."

        game.players.append(
            Player(
                id=player_id,
                name=player_name,
            )
        )

        return True, "با موفقیت وارد بازی شدید."

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
            return False, "سازنده بازی نمی‌تواند خارج شود."

        before = len(game.players)

        game.players = [
            player
            for player in game.players
            if player.id != player_id
        ]

        if len(game.players) == before:
            return False, "شما در این بازی نیستید."

        return True, "از بازی خارج شدید."

    def start_game(
        self,
        game_id: str,
        player_id: int,
    ) -> tuple[bool, str]:

        game = self.get_game(game_id)

        if not game:
            return False, "بازی پیدا نشد."

        if player_id != game.creator_id:
            return False, "فقط سازنده بازی می‌تواند بازی را شروع کند."

        if game.started:
            return False, "بازی قبلاً شروع شده است."

        if len(game.players) != game.max_players:
            return (
                False,
                f"برای شروع بازی باید {game.max_players} بازیکن حاضر باشند.",
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

        for player in game.players:
            player.cards.clear()
            player.tricks = 0

        for index, card in enumerate(deck):
            player = game.players[index % len(game.players)]
            player.cards.append(card)

        hakim = random.choice(game.players)

        game.hakim_id = hakim.id
        game.current_player_id = hakim.id
        game.started = True
        game.finished = False
        game.hokm = None
        game.lead_suit = None
        game.current_trick.clear()
        game.winner_id = None
        game.team_a_score = 0
        game.team_b_score = 0

        return True, "بازی شروع شد."

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

        if game.hakim_id != player_id:
            return False, "فقط حاکم می‌تواند حکم را انتخاب کند."

        if game.hokm:
            return False, "حکم قبلاً انتخاب شده است."

        if suit not in SUITS:
            return False, "خال نامعتبر است."

        game.hokm = suit

        return True, "حکم انتخاب شد."

    def get_player(
        self,
        game: GameRoom,
        player_id: int,
    ) -> Optional[Player]:

        for player in game.players:
            if player.id == player_id:
                return player

        return None

    def legal_cards(
        self,
        game: GameRoom,
        player_id: int,
    ) -> list[Card]:

        player = self.get_player(game, player_id)

        if not player:
            return []

        if not game.current_trick:
            return list(player.cards)

        if not game.lead_suit:
            return list(player.cards)

        same_suit = [
            card
            for card in player.cards
            if card.suit == game.lead_suit
        ]

        if same_suit:
            return same_suit

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

        if game.hokm is None:
            return False, "ابتدا باید حکم انتخاب شود."

        if game.current_player_id != player_id:
            return False, "الان نوبت شما نیست."

        player = self.get_player(game, player_id)

        if not player:
            return False, "بازیکن پیدا نشد."

        selected_card = None

        for card in player.cards:
            if card.suit == suit and card.rank == rank:
                selected_card = card
                break

        if selected_card is None:
            return False, "این کارت در دست شما نیست."

        legal = self.legal_cards(
            game,
            player_id,
        )

        if not any(
            card.suit == selected_card.suit
            and card.rank == selected_card.rank
            for card in legal
        ):
            return False, "باید از خال شروع‌شده پیروی کنید."

        player.cards.remove(selected_card)

        if not game.current_trick:
            game.lead_suit = selected_card.suit

        game.current_trick.append(
            {
                "player_id": player_id,
                "player_name": player.name,
                "card": selected_card.to_dict(),
            }
        )

        next_index = (
            game.players.index(player) + 1
        ) % len(game.players)

        if len(game.current_trick) < len(game.players):

            game.current_player_id = (
                game.players[next_index].id
            )

            return True, "کارت بازی شد."

        winner = self._trick_winner(game)

        winner_player = self.get_player(
            game,
            winner,
        )

        if winner_player:
            winner_player.tricks += 1

        if winner_player:
            if game.players.index(winner_player) % 2 == 0:
                game.team_a_score += 1
            else:
                game.team_b_score += 1

        game.current_trick.clear()
        game.lead_suit = None

        cards_left = sum(
            len(p.cards)
            for p in game.players
        )

        if cards_left == 0:

            game.finished = True
            game.winner_id = winner

            return True, "بازی تمام شد."

        game.current_player_id = winner

        return True, "دست کامل شد."

    def _trick_winner(
        self,
        game: GameRoom,
    ) -> int:

        if not game.current_trick:
            raise RuntimeError("دست خالی است.")

        best = game.current_trick[0]

        for current in game.current_trick[1:]:

            best_card = best["card"]
            current_card = current["card"]

            if self._card_beats(
                game,
                current_card,
                best_card,
            ):
                best = current

        return best["player_id"]

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

        if current_suit == hokm and best_suit != hokm:
            return True

        if best_suit == hokm and current_suit != hokm:
            return False

        if current_suit == lead and best_suit != lead:
            return True

        return False

    def state_for_player(
        self,
        game_id: str,
        player_id: int,
    ) -> Optional[dict]:

        game = self.get_game(game_id)

        if not game:
            return None

        viewer = self.get_player(
            game,
            player_id,
        )

        if not viewer:
            return None

        players_data = []

        for player in game.players:

            cards = []

            if player.id == player_id:
                cards = [
                    card.to_dict()
                    for card in player.cards
                ]

            players_data.append(
                {
                    "id": player.id,
                    "name": player.name,
                    "cards": cards,
                    "card_count": len(player.cards),
                    "tricks": player.tricks,
                    "is_hakim": player.id == game.hakim_id,
                    "is_turn": player.id == game.current_player_id,
                }
            )

        return {
            "game_id": game.game_id,

            "viewer_id": player_id,

            "creator_id": game.creator_id,

            "started": game.started,

            "finished": game.finished,

            "max_players": game.max_players,

            "player_count": len(game.players),

            "players": players_data,

            "hakim_id": game.hakim_id,

            "hokm": game.hokm,

            "current_player_id": game.current_player_id,

            "lead_suit": game.lead_suit,

            "current_trick": game.current_trick,

            "winner_id": game.winner_id,

            "team_a_score": game.team_a_score,

            "team_b_score": game.team_b_score,

            "cards_left": sum(
                len(player.cards)
                for player in game.players
            ),
        }


game_state = GameState()
