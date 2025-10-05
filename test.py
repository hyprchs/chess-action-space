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
        from_rank = chess.square_rank(from_square)
        if from_rank not in (chess.RANK_NAMES.index('7'), chess.RANK_NAMES.index('2')):
            return False

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
            if right_file > chess.FILE_NAMES.index('h'):
                right_sq = None
            else:
                assert 0 <= right_file <= 7
                right_sq = chess.square(right_file, rank)
            return left_sq, right_sq

        b = chess.Board.empty()

        adjacent_to_from_square = get_adjacent_squares(from_square)
        if from_rank == chess.RANK_NAMES.index('7'):
            pawn_color = chess.WHITE
            capturable_squares = [
                next(iter(chess.SquareSet(chess.shift_up(chess.BB_SQUARES[sq]))))
                for sq in adjacent_to_from_square if sq is not None
            ]
        elif from_rank == chess.RANK_NAMES.index('2'):
            pawn_color = chess.BLACK
            capturable_squares = [
                next(iter(chess.SquareSet(chess.shift_down(chess.BB_SQUARES[sq]))))
                for sq in adjacent_to_from_square
                if sq is not None
            ]
        else:
            raise AssertionError('Bad logic above')

        b.turn = pawn_color
        b.set_piece_at(from_square, chess.Piece(chess.PAWN, pawn_color))
        for sq in capturable_squares:
            if sq is None:
                continue
            b.set_piece_at(sq, chess.Piece(chess.QUEEN, not pawn_color))

        return b.is_legal(chess.Move(from_square, to_square, chess.QUEEN))

    action_space_moves = set(iter_action_space())
    for move in action_space_moves:
        if move.promotion:
            move_copy = copy(move)
            move_copy.promotion = None
            assert move_copy in action_space_moves
            # Will check via the non-promotion version of the move
            continue
        move_knight_promo = copy(move)
        move_bishop_promo = copy(move)
        move_rook_promo = copy(move)
        move_knight_promo.promotion = chess.KNIGHT
        move_bishop_promo.promotion = chess.BISHOP
        move_rook_promo.promotion = chess.ROOK
        if can_be_pawn_promotion_inefficient(move.from_square, move.to_square):
            assert move_knight_promo in action_space_moves
            assert move_bishop_promo in action_space_moves
            assert move_rook_promo in action_space_moves
        else:
            assert move_knight_promo not in action_space_moves
            assert move_bishop_promo not in action_space_moves
            assert move_rook_promo not in action_space_moves


def test_no_queen_promotions():
    # The action for a queen promotion should just be the action for the move
    for move in iter_action_space():
        if move.promotion:
            assert move.promotion != chess.QUEEN
