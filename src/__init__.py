import os
from copy import copy
from os import PathLike
from typing import Iterable

import chess

from pathlib import Path


def get_possible_to_squares_mask(from_square: chess.Square) -> chess.Bitboard:
    b = chess.BaseBoard.empty()

    # Place queen and see where it attacks
    b.set_piece_at(from_square, chess.Piece.from_symbol('Q'))
    q_moves = b.attacks_mask(from_square)

    # Place knight and see where it attacks
    b.set_piece_at(from_square, chess.Piece.from_symbol('N'))
    n_moves = b.attacks_mask(from_square)

    b.remove_piece_at(from_square)
    # Done with the board now

    # Logical or to combine bitmaps (ex. 1100 | 0101 = 1101)
    all_moves = q_moves | n_moves

    return all_moves


def can_be_pawn_promotion(from_square: chess.Square, to_square: chess.Square) -> bool:
    from_rank = chess.square_rank(from_square)
    to_rank = chess.square_rank(to_square)
    if (from_rank, to_rank) not in ((6, 7), (1, 0)):
        return False

    from_file = chess.square_file(from_square)
    to_file = chess.square_file(to_square)
    if abs(from_file - to_file) > 1:
        return False

    return True


def get_underpromotion_action_space_size() -> int:
    """
    Return the size of the underpromotion action space, which is equal to `132 = (8 + 7 + 7) * (4 - 1) * 2`.
    For both white and black directions, we have:

    - 8 forward promotions
    - 7 right-capture promotions
    - 7 left-capture promotions

    which can all promote to 3 pieces (4 minus 1 for the queen, which is not an underpromotion).
    """
    return (8 + 7 + 7) * (4 - 1) * 2


def get_action_space_size() -> int:
    # Each chess piece moves like either a queen or a knight from one square to another square.
    # All possible moves except pawn promotions can be specified by the "from" square and the "to" square
    # (even castling, ex. e1->g1, or e1->c1).
    action_space = 0
    for from_square in chess.SQUARES:
        # Get # possible moves from this square
        all_moves_mask = get_possible_to_squares_mask(from_square)
        action_space += all_moves_mask.bit_count()

    # Count underpromotions.
    # Note that we choose to define the action that was already counted above as the "default" promotion to a queen.
    action_space += get_underpromotion_action_space_size()

    return action_space


def iter_action_space() -> Iterable[chess.Move]:
    non_queen_promotion_piece_types = (chess.KNIGHT, chess.BISHOP, chess.ROOK)
    for from_square in chess.SQUARES:
        # Get # possible moves from this square
        all_moves_mask = get_possible_to_squares_mask(from_square)
        for to_square in chess.SquareSet(all_moves_mask):
            move = chess.Move(from_square, to_square)
            yield move

            # Yield underpromotion moves
            if not can_be_pawn_promotion(from_square, to_square):
                continue
            for piece_type in non_queen_promotion_piece_types:
                promotion_move = copy(move)
                promotion_move.promotion = piece_type
                yield promotion_move


def export(path: str | Path | PathLike, *, allow_overwrite: bool = False) -> None:
    if os.path.exists(path) and not allow_overwrite:
        raise FileExistsError(f'File {path} already exists')
    with open(path, 'w') as f:
        f.write("".join(f"{m.uci()}\n" for m in iter_action_space()))
