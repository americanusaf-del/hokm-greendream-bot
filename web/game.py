"""Game engine for Hokm."""

from __future__ import annotations

import random
import secrets
from dataclasses import dataclass, field


SUITS = ("♥", "♦", "♣", "♠")

RANKS = (
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "10",
    "J",
    "Q",
    "K",
    "A",
)

RANK_VALUE = {
    rank: index
    for index, rank in enumerate(RANKS, start=2)
}


@dataclass(frozen=True)
class Card:
    rank: str
    suit: str

    @property
    def value(self) -> int:
        return RANK_VALUE[self.rank]

    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"


@dataclass
class Player:
    user_id: int
    name: str
    is_bot: bool = False
    position: int = 0

    @property
    def team(self) -> int:
        return self.position % 2


@dataclass
class GameRoom:
    game_id: str
    creator_id: int
    max_players: int

    players: dict[int, Player] = field(default_factory=dict)

    started: bool = False
    finished: bool = False

    hakim_id: int | None = None
    hokm: str | None = None

    hands: dict[int, list[Card]] = field(default_factory=dict)

    current_player_id: int | None = None

    lead_suit: str | None = None

    current_trick: list[tuple[int, Card]] = field(
        default_factory=list
    )

    tricks_won: dict[int, int] = field(
        default_factory=dict
    )

    team_scores: dict[int, int] = field(
        default_factory=lambda: {
            0: 0,
            1: 0,
        }
    )

    winner_id: int | None = None


class GameState:
    """Keeps the active Hokm game."""

    def __init__(self):
        self.games: dict[str, GameRoom] = {}

    # =====================================================
    # GAME CREATION
    # =====================================================

    def create_game(
        self,
        creator_id: int,
        creator_name: str,
        max_players: int,
    ) -> GameRoom:

        game_id = secrets.token_hex(4).upper()

        player = Player(
            user_id=creator_id,
            name=creator_name,
            position=0,
        )

        game = GameRoom(
            game_id=game_id,
            creator_id=creator_id,
            max_players=max_players,
            players={
                creator_id: player
            },
        )

        self.games[game_id] = game

        return game

    # =====================================================
    # GET GAME
    # =====================================================

    def get_game(
        self,
        game_id: str,
    ) -> GameRoom | None:

        return self.games.get(game_id)

    # =====================================================
    # ADD PLAYER
    # =====================================================

    def add_player(
        self,
        game_id: str,
        user_id: int,
        name: str,
    ) -> str:

        game = self.get_game(game_id)

        if game is None:
            return "no_game"

        if game.started:
            return "started"

        if user_id in game.players:
            return "already_joined"

        if len(game.players) >= game.max_players:
            return "full"

        position = len(game.players)

        game.players[user_id] = Player(
            user_id=user_id,
            name=name,
            position=position,
        )

        return "joined"

    # =====================================================
    # START GAME
    # =====================================================

    def start_game(
        self,
        game_id: str,
    ) -> str:

        game = self.get_game(game_id)

        if game is None:
            return "no_game"

        if game.started:
            return "already_started"

        if len(game.players) != game.max_players:
            return "wrong_count"

        if game.max_players == 1:
            return self._start_test_game(game)

        if game.max_players not in (2, 4):
            return "invalid_player_count"

        deck = self._create_deck()

        random.shuffle(deck)

        players = list(game.players.values())

        game.hakim_id = random.choice(players).user_id

        if game.max_players == 4:
            cards_per_player = 13
        else:
            cards_per_player = 26

        for player in players:
            game.hands[player.user_id] = []

        index = 0

        for player in players:
            game.hands[player.user_id] = deck[
                index:index + cards_per_player
            ]

            index += cards_per_player

        game.started = True

        game.current_player_id = game.hakim_id

        for player in players:
            game.tricks_won[player.user_id] = 0

        return "started"

    # =====================================================
    # TEST GAME
    # =====================================================

    def _start_test_game(
        self,
        game: GameRoom,
    ) -> str:

        deck = self._create_deck()

        random.shuffle(deck)

        player = next(
            iter(game.players.values())
        )

        # در حالت تست فقط ۱۳ کارت به بازیکن داده می‌شود.
        game.hands[player.user_id] = deck[:13]

        game.hakim_id = player.user_id

        game.started = True

        game.current_player_id = player.user_id

        game.tricks_won[player.user_id] = 0

        return "started"

    # =====================================================
    # HOKM
    # =====================================================

    def set_hokm(
        self,
        game_id: str,
        user_id: int,
        suit: str,
    ) -> str:

        game = self.get_game(game_id)

        if game is None:
            return "no_game"

        if not game.started:
            return "not_started"

        if game.finished:
            return "finished"

        if game.hakim_id != user_id:
            return "not_hakim"

        if game.hokm is not None:
            return "already_selected"

        if suit not in SUITS:
            return "invalid_suit"

        game.hokm = suit

        return "selected"

    # =====================================================
    # HAND
    # =====================================================

    def get_hand(
        self,
        game_id: str,
        user_id: int,
    ) -> list[Card]:

        game = self.get_game(game_id)

        if game is None:
            return []

        return list(
            game.hands.get(user_id, [])
        )

    # =====================================================
    # TURN
    # =====================================================

    def is_player_turn(
        self,
        game_id: str,
        user_id: int,
    ) -> bool:

        game = self.get_game(game_id)

        if game is None:
            return False

        return game.current_player_id == user_id

    # =====================================================
    # LEGAL CARDS
    # =====================================================

    def legal_cards(
        self,
        game_id: str,
        user_id: int,
    ) -> list[Card]:

        game = self.get_game(game_id)

        if game is None:
            return []

        hand = game.hands.get(
            user_id,
            [],
        )

        if not hand:
            return []

        if game.lead_suit is None:
            return list(hand)

        same_suit = [
            card
            for card in hand
            if card.suit == game.lead_suit
        ]

        if same_suit:
            return same_suit

        return list(hand)

    # =====================================================
    # PLAY CARD
    # =====================================================

    def play_card(
        self,
        game_id: str,
        user_id: int,
        card_index: int,
    ) -> dict:

        game = self.get_game(game_id)

        if game is None:
            return {
                "ok": False,
                "reason": "no_game",
            }

        if not game.started:
            return {
                "ok": False,
                "reason": "not_started",
            }

        if game.finished:
            return {
                "ok": False,
                "reason": "finished",
            }

        if game.hokm is None:
            return {
                "ok": False,
                "reason": "hokm_not_selected",
            }

        if game.current_player_id != user_id:
            return {
                "ok": False,
                "reason": "not_your_turn",
            }

        hand = game.hands.get(
            user_id,
            [],
        )

        if card_index < 0 or card_index >= len(hand):
            return {
                "ok": False,
                "reason": "invalid_card",
            }

        card = hand[card_index]

        legal = self.legal_cards(
            game_id,
            user_id,
        )

        if card not in legal:
            return {
                "ok": False,
                "reason": "must_follow_suit",
            }

        hand.pop(card_index)

        if game.lead_suit is None:
            game.lead_suit = card.suit

        game.current_trick.append(
            (user_id, card)
        )

        result = {
            "ok": True,
            "card": card,
            "trick_finished": False,
            "winner_id": None,
            "next_player_id": None,
        }

        if len(game.current_trick) < len(game.players):

            next_player = self._next_player(game)

            game.current_player_id = next_player

            result["next_player_id"] = next_player

            return result

        winner_id = self._trick_winner(game)

        game.tricks_won[winner_id] = (
            game.tricks_won.get(
                winner_id,
                0,
            )
            + 1
        )

        winner = game.players[winner_id]

        game.team_scores[winner.team] += 1

        result["trick_finished"] = True
        result["winner_id"] = winner_id

        game.current_trick.clear()
        game.lead_suit = None

        if all(
            len(hand) == 0
            for hand in game.hands.values()
        ):

            game.finished = True

            game.winner_id = self._game_winner(game)

            return result

        game.current_player_id = winner_id

        result["next_player_id"] = winner_id

        return result

    # =====================================================
    # TRICK WINNER
    # =====================================================

    def _trick_winner(
        self,
        game: GameRoom,
    ) -> int:

        cards = game.current_trick

        winner_id, winner_card = cards[0]

        for player_id, card in cards[1:]:

            if self._beats(
                card,
                winner_card,
                game.lead_suit,
                game.hokm,
            ):
                winner_id = player_id
                winner_card = card

        return winner_id

    # =====================================================
    # CARD COMPARISON
    # =====================================================

    @staticmethod
    def _beats(
        challenger: Card,
        current: Card,
        lead_suit: str | None,
        hokm: str | None,
    ) -> bool:

        if hokm:

            if challenger.suit == hokm:
                if current.suit != hokm:
                    return True

                return (
                    challenger.value
                    > current.value
                )

            if current.suit == hokm:
                return False

        if challenger.suit == current.suit:
            return (
                challenger.value
                > current.value
            )

        if current.suit == lead_suit:
            return False

        return challenger.suit == lead_suit

    # =====================================================
    # NEXT PLAYER
    # =====================================================

    def _next_player(
        self,
        game: GameRoom,
    ) -> int:

        players = list(
            game.players.values()
        )

        current_index = next(
            index
            for index, player in enumerate(players)
            if player.user_id == game.current_player_id
        )

        next_index = (
            current_index + 1
        ) % len(players)

        return players[next_index].user_id

    # =====================================================
    # GAME WINNER
    # =====================================================

    @staticmethod
    def _game_winner(
        game: GameRoom,
    ) -> int | None:

        if not game.players:
            return None

        best_player = None
        best_score = -1

        for player in game.players.values():

            score = game.tricks_won.get(
                player.user_id,
                0,
            )

            if score > best_score:
                best_score = score
                best_player = player.user_id

        return best_player

    # =====================================================
    # DECK
    # =====================================================

    @staticmethod
    def _create_deck() -> list[Card]:

        return [
            Card(
                rank=rank,
                suit=suit,
            )
            for suit in SUITS
            for rank in RANKS
        ]

    # =====================================================
    # CURRENT TRICK
    # =====================================================

    def current_trick(
        self,
        game_id: str,
    ) -> list[tuple[int, Card]]:

        game = self.get_game(game_id)

        if game is None:
            return []

        return list(
            game.current_trick
        )

    # =====================================================
    # REMOVE GAME
    # =====================================================

    def remove_game(
        self,
        game_id: str,
    ) -> None:

        self.games.pop(
            game_id,
            None,
        )


# یک نمونه مشترک از موتور بازی
game_state = GameState()
