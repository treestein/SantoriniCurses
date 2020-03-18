import curses
import logging
from typing import List, Optional


TilePosition = List[int]

# TODO: Refactor
#       - Combine stdscr move and add str to one function call
#       - Potentially make hint system more robust (move to seperate class) - ability for more than 1 hint
#       - More elegant solution for list scrolling in the 2 selection methods
#       - Make draw_hint automatically draw 1 under board instead of manually setting it
#       - A lot of logic will have to be moved into Player class with the game handing it the board layout so Player
#           Can manipulate logic with god powers


def get_logger():
    logger = logging.getLogger(__file__)
    handler = logging.FileHandler(f"{__file__}.log")
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    return logger


class Player:

    MAX_BUILDERS = 2

    def __init__(self):
        self.builders = []
        self.has_placed_builders = False

    def play_turn(self):
        builder = self.select_builder()
        self.move_builder(builder)
        self.build(builder)

    def place_builder(self, location: TilePosition):
        if len(self.builders) <= Player.MAX_BUILDERS:
            self.builders.append(list(location))
        if len(self.builders) >= Player.MAX_BUILDERS:
            self.has_placed_builders = True

    def select_builder(self) -> int:
        return 0

    def move_builder(self, builder):
        pass

    def build(self, builder):
        pass


class Santorini:

    GAME_STATES = {
        "setup": 0,
        "play": 1,
        "finish": 2
    }

    KEYS = {
        "right": (curses.KEY_RIGHT, 68, 100),
        "left": (curses.KEY_LEFT, 65, 97),
        "up": (curses.KEY_UP, 87, 119),
        "down": (curses.KEY_DOWN, 83, 115),
        "select": (curses.KEY_ENTER, 10, 13)
    }

    def __init__(self, board_size: tuple):
        self.stdscr = None
        self.running = False
        self.board = []
        for row in range(board_size[1]):
            self.board.append([0] * board_size[0])
        self.state = Santorini.GAME_STATES["setup"]
        self.players = [Player(), Player()]  # TODO: Change so that people can choose 2-3 players
        self.current_hint = ""
        self.debug = True
        self.debug_hint = ""
        self.logger = get_logger()

        self.selection_cursor = [0, 0]

    def main(self, stdscr: object):
        curses.curs_set(False)
        # Player Colours
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_CYAN)
        # Sys Colours
        curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_GREEN)
        curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_RED)
        self.stdscr = stdscr
        self.running = True
        self.run()

    def run(self):
        if not self.stdscr:
            raise ValueError("Curses has not been initialised.")
        while self.running:
            self.draw()

            if self.state == Santorini.GAME_STATES["setup"]:
                for i, player in enumerate(self.players):
                    self.current_hint = f"Player {i+1}: Place builders."
                    self.player_place_builders(player)
                self.state = Santorini.GAME_STATES["play"]
                self.selection_cursor = None
            elif self.state == Santorini.GAME_STATES["play"]:
                for i, player in enumerate(self.players):
                    self.current_hint = f"Player {i+1}: Select your builder."
                    if Player.MAX_BUILDERS > 1:
                        builder = self.player_select_builder(player)
                    else:
                        builder = 0
                    self.current_hint = f"Player {i+1}: Move your selected builder."
                    self.player_move_builder(player, builder)
                    # Check if player has one after they have moved
                    if self.check_for_player_win(player):
                        self.current_hint = f"Player {i + 1} has WON!!!"
                        self.draw()
                        self.stdscr.getch()
                        self.running = False
                        return
                    self.current_hint = f"Player {i+1}: Build."
                    self.player_build(player, builder)

            self.stdscr.refresh()

    def get_if_all_players_placed(self):
        return any([player.has_placed_builders for player in self.players])

    def player_place_builders(self, player: Player):
        self.draw()
        while not player.has_placed_builders:
            key = self.stdscr.getch()
            if key in Santorini.KEYS["down"]:
                self.selection_cursor[1] = min(self.selection_cursor[1] + 1, len(self.board) - 1)
            elif key in Santorini.KEYS["up"]:
                self.selection_cursor[1] = max(self.selection_cursor[1] - 1, 0)
            elif key in Santorini.KEYS["left"]:
                self.selection_cursor[0] = max(self.selection_cursor[0] - 1, 0)
            elif key in Santorini.KEYS["right"]:
                self.selection_cursor[0] = min(
                    self.selection_cursor[0] + 1,
                    len(self.board[self.selection_cursor[1]]) - 1
                )
            elif key == curses.KEY_ENTER or key == 10 or key == 13:
                if not self.is_builder_at_tile(self.selection_cursor):
                    player.place_builder(self.selection_cursor)
                else:
                    self.current_hint = "Cannot place builder on top of another builder."
            self.draw()

    def is_builder_at_tile(self, tile_pos: TilePosition):
        for player in self.players:
            if tile_pos in player.builders:
                return True
        return False

    def force_player_to_select_tile(self, tiles: List[TilePosition]) -> int:
        self.selection_cursor = None
        self.draw()
        key = None
        selected_tile = 0
        while True:
            if key in Santorini.KEYS["select"]:
                break
            elif key in Santorini.KEYS["right"]:
                selected_tile += 1
                if selected_tile > len(tiles) - 1:
                    selected_tile = 0
            elif key in Santorini.KEYS["left"]:
                selected_tile -= 1
                if selected_tile < 0:
                    selected_tile = len(tiles) - 1
            self.selection_cursor = tiles[selected_tile]
            self.draw()
            for tile in tiles:
                if self.selection_cursor == tile:
                    continue  # We don't want to render over our selected tile
                self.stdscr.move(*self.convert_tile_to_coord(tile))
                self.stdscr.addch(self.get_tile(tile), curses.color_pair(4))
            key = self.stdscr.getch()
        return selected_tile

    def player_select_builder(self, player: Player) -> int:
        self.selection_cursor = None
        self.draw()
        key = None
        selected_builder = 0
        while True:
            if key in Santorini.KEYS["select"]:
                break
            elif key in Santorini.KEYS["right"]:
                selected_builder += 1
                if selected_builder > len(player.builders) - 1:
                    selected_builder = 0
            elif key in Santorini.KEYS["left"]:
                selected_builder -= 1
                if selected_builder < 0:
                    selected_builder = len(player.builders) - 1
            self.selection_cursor = player.builders[selected_builder]
            self.draw()
            key = self.stdscr.getch()
        return selected_builder

    def player_move_builder(self, player: Player, builder_index: int):
        moveable_tiles = self.get_adjacent_moveable_tiles(player.builders[builder_index])
        selected_tile = self.force_player_to_select_tile(moveable_tiles)
        player.builders[builder_index] = moveable_tiles[selected_tile]

    def player_build(self, player: Player, builder_index: int):
        buildable_tiles = self.get_adjacent_buildable_tiles(player.builders[builder_index])
        selected_tile = self.force_player_to_select_tile(buildable_tiles)
        build_tile = buildable_tiles[selected_tile]
        self.board[build_tile[1]][build_tile[0]] += 1

    def get_adjacent_tiles(self, tile_pos: TilePosition) -> List[TilePosition]:
        adjacent_tiles = []
        for x in range(tile_pos[0] - 1, tile_pos[0] + 2):
            for y in range(tile_pos[1] - 1, tile_pos[1] + 2):
                if (-1 < x < len(self.board) and
                    -1 < y < len(self.board[x]) and
                    (x != tile_pos[0] or y != tile_pos[1]) and
                    (0 <= x <= len(self.board) and
                    (0 <= y <= len(self.board[x])))
                ):
                    adjacent_tiles.append([x, y])
        return adjacent_tiles

    def get_adjacent_moveable_tiles(self, builder_pos: TilePosition) -> List[TilePosition]:
        moveable_tiles = []
        all_builders = [builder for player in self.players for builder in player.builders]
        for tile in self.get_adjacent_tiles(builder_pos):
            # Check that the tile is either at the same level or 1 above and check tile is not occupied by builder
            if not(int(self.get_tile(builder_pos)) + 1 < int(self.get_tile(tile)) or int(self.get_tile(tile)) >= 4 or tile in all_builders):
                moveable_tiles.append(tile)
        return moveable_tiles

    def get_adjacent_buildable_tiles(self, builder_pos: TilePosition) -> List[TilePosition]:
        buildable_tiles = []
        all_builders = [builder for player in self.players for builder in player.builders]
        for tile in self.get_adjacent_tiles(builder_pos):
            if not(int(self.get_tile(tile)) >= 4 or tile in all_builders):
                buildable_tiles.append(tile)
        return buildable_tiles

    def check_for_player_win(self, player: Player) -> Optional[int]:
        for builder in player.builders:
            if int(self.get_tile(builder)) == 3:
                return True
        return False

    def draw(self):
        self.stdscr.clear()
        self.draw_board()
        self.draw_hint()

    def draw_board(self):
        # Draw standard board
        for y, row in enumerate(self.board):
            for x, tile in enumerate(row):
                self.stdscr.move(*self.convert_tile_to_coord([x, y]))
                self.stdscr.addch(str(tile))
        # Draw builders
        for i, player in enumerate(self.players):
            for builder in player.builders:
                self.stdscr.move(*self.convert_tile_to_coord(builder))
                self.stdscr.addch(
                    self.get_tile(builder),
                    curses.A_BOLD | curses.color_pair(i+1) | curses.A_UNDERLINE
                )
        # Draw selection cursor
        if self.selection_cursor:
            self.stdscr.move(*self.convert_tile_to_coord(self.selection_cursor))
            self.stdscr.addch(self.get_tile(self.selection_cursor), curses.A_BLINK | curses.A_STANDOUT)

    # Helper method for getting the character at a certain tile
    def get_tile(self, tile_pos: TilePosition) -> str:
        """Gets the value of a tile at given position

        :param tile_pos: Position of a tile
        :return tile character: The current level of that tile e.g. 0-4
        """
        return str(self.board[tile_pos[1]][tile_pos[0]])

    @staticmethod
    def convert_tile_to_coord(tile_pos: TilePosition):
        """Helper method for converting tile index to actual character coordinate on screen

        :param tile_pos: Indexes for accessing tile in the board 2d list
        :return coord: Coordinate for plotting tile in Curses format y,x
        """
        x_buff, y_buff, x_spacing = 1, 1, 2
        return int(tile_pos[1])+y_buff, int(tile_pos[0])*x_spacing+x_buff

    def draw_hint(self):
        """Shows a hint to help the player with their next move. Also shows debug info if it has been set"""
        self.stdscr.move(10, 0)
        self.stdscr.addstr(self.current_hint)
        if self.debug:
            self.stdscr.move(11, 0)
            self.stdscr.addstr(
                f"DEBUG: {self.debug_hint}",
                curses.color_pair(5) | curses.A_STANDOUT | curses.A_BOLD
            )


if __name__ == "__main__":
    s = Santorini(board_size=(5, 5))
    curses.wrapper(s.main)
