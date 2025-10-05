from copy import copy

from src import (
    get_action_space_size,
    get_underpromotion_action_space_size,
    iter_action_space,
)
import chess


def test_get_action_space_size():
    assert get_action_space_size() == 1924


def test_get_underpromotion_action_space_size():
    assert get_underpromotion_action_space_size() == 132


def test_iter_action_space():
    assert len(set(iter_action_space())) == 1924


def test_can_be_pawn_promotion():
    def can_be_pawn_promotion_inefficient(
        from_square: chess.Square, to_square: chess.Square
    ) -> bool:
        def get_adjacent_squares(
            square: chess.Square,
        ) -> tuple[chess.Square | None, chess.Square | None]:
            """
            Get the squares to the left and right of `square`, or `None` for squares that would fall off the board.
            """
            file = chess.square_file(square)
            rank = chess.square_rank(square)
            left_file = file - 1
            right_file = file + 1
            if left_file < 0:
                left_sq = None
            else:
                assert 0 <= left_file <= 7
                left_sq = chess.square(left_file, rank)
            if right_file > chess.FILE_NAMES.index("h"):
                right_sq = None
            else:
                assert 0 <= right_file <= 7
                right_sq = chess.square(right_file, rank)
            return left_sq, right_sq

        b = chess.Board.empty()
        b.set_piece_at(from_square, chess.Piece.from_symbol("P"))
        for sq in get_adjacent_squares(to_square):
            if sq is None:
                continue
            b.set_piece_at(sq, chess.Piece.from_symbol("q"))

        return b.is_legal(chess.Move(from_square, to_square, chess.QUEEN))

    action_space_moves = set(iter_action_space())
    for move in action_space_moves:
        if move.promotion:
            move_copy = copy(move)
            move_copy.promotion = None
            assert move_copy in action_space_moves
            # Will check via the non-promotion version of the move
            continue
        if can_be_pawn_promotion_inefficient(move.from_square, move.to_square):
            move_knight_promo = copy(move)
            move_bishop_promo = copy(move)
            move_rook_promo = copy(move)
            move_knight_promo.promotion = chess.KNIGHT
            move_bishop_promo.promotion = chess.BISHOP
            move_rook_promo.promotion = chess.ROOK
            assert all(
                m in action_space_moves
                for m in (move_knight_promo, move_bishop_promo, move_rook_promo)
            )


def test_no_queen_promotions():
    # The action for a queen promotion should just be the action for the move
    for move in iter_action_space():
        if move.promotion:
            assert move.promotion != chess.QUEEN
