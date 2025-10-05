import chess


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
