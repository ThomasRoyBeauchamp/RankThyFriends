import discord
import numpy as np
import numpy.random
import logging

from typing import Dict
from copy import deepcopy

class RankingGame:
    CONTINUE: bool = True
    RUNNING: bool = False
    CALCULATING_ROUND_SCORES: bool = False

    def __init__(self,  categories: list[str], channel_id: int | None = None,) -> None:
        self._players: list[discord.Member | discord.User] = []
        self._lobby: list[discord.Member] = []
        self._anti_lobby: list[discord.Member] = []

        self.log = logging.getLogger('RankYourFriends_Log')

        self._categories: list[str] = categories
        self._used_categories: list[str] = []


        self._rng = numpy.random.default_rng()
        self._channel_id = channel_id

        self._current_round_score: np.ndarray = np.zeros((0, 0))

        self._has_current_round_submission: dict[str, bool] = {}
        self._current_round_position_guesses: dict[str, int | None] = {}
        self._current_round_ranks: dict[str, int] = {}

        self._current_question: str = ''

        self.overall_score: Dict[str, int] = {}

    @property
    def player_names(self):
        return [player.display_name for player in self._players]

    @property
    def overall_scores(self):
        scores = list(self.overall_score.items())
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores

    @property
    def current_question(self):
        return self._current_question

    @property
    def current_round_position_guesses_entries(self):
        return self._current_round_position_guesses.items()


    def has_submitted_ranking(self, player: str) -> bool:
        if player in self._has_current_round_submission:
            return self._has_current_round_submission[player]
        else:
            return False

    def has_submitted_current_round_guess(self, player: str) -> bool:
        if player in self._current_round_position_guesses:
            return self._current_round_position_guesses[player] is not None
        else:
            return False

    @property
    def current_round_ranking(self):
        return self._current_round_ranks

    @property
    def channel_id(self):
        return self._channel_id

    def add_player(self, player: discord.Member):
        if player not in self._players:
            if not self.RUNNING:
                self._players.append(player)
            else:
                self._lobby.append(player)
            

    def remove_player(self, player: discord.Member):
        if not self.RUNNING:
            if player in self._players:
                self._players.remove(player)
        else:
            self._anti_lobby.append(player)


    @property
    def received_all_responses(self):
        return None not in self._current_round_position_guesses.values()

    @property
    def players(self):
        return self._players

    @property
    def number_of_players(self):
        return len(self._players)

    def reset_game(self, categories: list[str], channel_id: int | None = None):
        self.__init__(categories, channel_id)

    def start_new_round(self):
        self.RUNNING = True
        # admits players waiting in the lobby
        for player in self._lobby:
            self.players.append(player)

        # Removes players waiting to be removed
        for player in self._anti_lobby:
            if player in self._players:
                self._players.remove(player)

        self._current_round_score = np.zeros((self.number_of_players, self.number_of_players))
        self._current_round_position_guesses = {player.display_name: None for player in self._players}

        self._has_current_round_submission: dict[str, bool] = {player.display_name: False for player in self._players}
        self._current_round_ranks = {}


        if len(self._categories) == 0:
            self._categories = deepcopy(self._used_categories)
            self._used_categories.clear()


        self._current_question = np.random.choice(self._categories)

        self._used_categories.append(self.current_question)
        self._categories.remove(self.current_question)  # removes categories from selection to avoid duplicate rounds.

    def is_valid_response(self, order: str):
        if (
                all(x.isdigit() for x in order) and  # checks for valid digits
                all(order.count(x) == 1 for x in set(order)) and  # checks for duplicates
                len(order) <= self.number_of_players and  # checks for too many entries
                all(1 <= int(x) <= self.number_of_players for x in order)  # checks that all entries correspond to players
        ):
            return True
        else:
            return False
        
    def submit_ranking(self, order, player) -> int:
        """
        
        :param order: ordering submitted by the player
        :param player: display_name of the player
        :return: code 0 = success, 1 = invalid order, 2 = player not in game
        """
        if not self.is_valid_response(order):
            return 1
        if player not in self._has_current_round_submission:
            return 2
        
        self._current_round_score += self._order_matrix(order)
        self._has_current_round_submission[player] = True
        return 0

    def submit_position_guess(self, guess, player) -> int:
        """

        :param guess: message from player
        :param player: which player submitted the guess
        :return: code 0 = success, 1 = invalid guess
        """

        if not (
            len(guess) == 1 and
            guess[0].isdigit() and
            0 < int(guess[0]) <= self.number_of_players
        ):
            return 1
        else:
            self._current_round_position_guesses[player] = int(guess[0])
        pass


    def _order_matrix(self, order: str) -> np.ndarray:
        matrix = np.zeros((self.number_of_players, self.number_of_players))
        unranked_players = list(range(1, self.number_of_players + 1))
        for x in order:
            if x != "0":
                unranked_players.remove(int(x))
        row = np.ones(self.number_of_players)
        for x in order:
            # The row starts as all 1s, indicating a preference above all other players. 
            # As each player is then placed, the 1 in their position is removed
            # to indicate that subsequently ranked players aren't preferred over formerly ranked players.
            if x != "0":
                row[int(x)-1] -= 1
                matrix[int(x)-1] += row
            else:
                # A '0' in the ranking is a placeholder for "all other players in an unspecified order", 
                # this system is to speed up difficult and inconsequential decision-making.
                for y in unranked_players:
                    row[y-1] -= 1
                for y in unranked_players:
                    matrix[y-1] += row
        return matrix

    def calculate_rankings(self):
        wins = np.zeros(self.number_of_players)
        for x in range(self.number_of_players):
            for y in range(self.number_of_players):
                if x < y:
                    if self._current_round_score[x, y] > self._current_round_score[y, x]:
                        wins[x] += 1
                    elif self._current_round_score[y, x] > self._current_round_score[x, y]:
                        wins[y] += 1
        ranks = np.zeros((3, self.number_of_players))
        ranks[0] += np.arange(1, self.number_of_players + 1)
        ranks[1] += wins
        for x in range(self.number_of_players):
            players_above = 0
            for y in range(self.number_of_players):
                if ranks[1, x] < ranks[1, y]:
                    players_above += 1
            # ranks[2, x] = players_above + 1
            self._current_round_ranks[self.players[x].display_name] = players_above + 1

    def calculate_points(self) -> dict[str, int]:
        round_score = {}
        for player in self._players:
            if player.display_name not in self.overall_score:
                self.overall_score[player.display_name] = 0

            if (self.current_round_ranking[player.display_name] ==
                    self._current_round_position_guesses[player.display_name]):
                round_score[player] = 2
                self.overall_score[player.display_name] += 2
            elif abs(self.current_round_ranking[player.display_name] -
                     self._current_round_position_guesses[player.display_name]) == 1:
                round_score[player] = 1
                self.overall_score[player.display_name] += 1
            else:
                round_score[player.display_name] = 0

        return round_score

