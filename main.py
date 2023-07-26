import chess


def get_action_space_size() -> int:
    # Each chess piece moves like either a queen or a knight from one square to another square.
    # All possible moves except pawn promotions can be specified by the "from" square and the "to" square
    # (even castling, ex. e1->g1, or e1->c1).
    action_space = 0
    b = chess.BaseBoard.empty()
    for square in range(64):
        # Place queen and see where it attacks
        b.set_piece_at(square, chess.Piece.from_symbol('Q'))
        q_moves = b.attacks(square)

        # Place knight and see where it attacks
        b.set_piece_at(square, chess.Piece.from_symbol('N'))
        n_moves = b.attacks(square)

        # Logical or to combine bitmaps (ex. 1100 | 0101 = 1101)
        all_moves = q_moves | n_moves

        # Get # possible moves from this square
        action_space += all_moves.mask.bit_count()

        b.remove_piece_at(square)

    # Count underpromotions manually:
    # 8 forward promotions, 7 right-capture promotions, and 7 left-capture promotions,
    # which can all promote to 4 pieces.
    # Note that each of these movements are already counted once above (as if a normal piece
    # were moving there), so below we only distinguish three (4-1) additional promotion types
    # for each base move. We can choose to define the action that was already counted above as
    # the "default" promotion to a queen.
    action_space += (8 + 7 + 7) * (4 - 1) * 2

    return action_space


if __name__ == '__main__':
    print(get_action_space_size())
