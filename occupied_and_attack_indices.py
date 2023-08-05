from ContextTimer import ContextTimer

from typing import Dict, List, Tuple
import bitarray
import chess
import chess.pgn
import io


BB_DOUBLE_PAWN_MOVE_RANKS = chess.BB_RANK_1 | chess.BB_RANK_2 | chess.BB_RANK_7 | chess.BB_RANK_8
# noinspection PyProtectedMember
BB_PAWN_MOVES = [[chess._step_attacks(sq, deltas[0] if chess.BB_SQUARES[sq] & BB_DOUBLE_PAWN_MOVE_RANKS else deltas[1])
                  for sq in chess.SQUARES]
                 for deltas in (((-7, -8, -9, -16), (-7, -8, -9)), ((7, 8, 9, 16), (7, 8, 9)))]
# noinspection PyProtectedMember
BB_KNIGHT_MOVES = chess.BB_KNIGHT_ATTACKS
# noinspection PyProtectedMember
BB_BISHOP_MOVES = [chess._sliding_attacks(sq, 0, (-9, -7, 7, 9)) for sq in chess.SQUARES]
# noinspection PyProtectedMember
BB_ROOK_MOVES = [chess._sliding_attacks(sq, 0, (-8, -1, 1, 8)) for sq in chess.SQUARES]
BB_QUEEN_MOVES = [BB_ROOK_MOVES[sq] | BB_BISHOP_MOVES[sq] for sq in chess.SQUARES]
BB_KING_MOVES = chess.BB_KING_ATTACKS
# Manually add castling moves, TODO support 960 castling to_squares?
BB_KING_MOVES[chess.E1] |= chess.BB_SQUARES[chess.G1] | chess.BB_SQUARES[chess.C1]
BB_KING_MOVES[chess.E8] |= chess.BB_SQUARES[chess.G8] | chess.BB_SQUARES[chess.C8]

BB_PIECE_MOVES: Dict[chess.PieceType, List] = {
    chess.PAWN: BB_PAWN_MOVES,
    chess.KNIGHT: BB_KNIGHT_MOVES,
    chess.BISHOP: BB_BISHOP_MOVES,
    chess.ROOK: BB_ROOK_MOVES,
    chess.QUEEN: BB_QUEEN_MOVES,
    chess.KING: BB_KING_MOVES
}


def format_fullmove(fullmove: int, color: chess.Color, /) -> str:
    """ Return a string representation of the fullmove number and color. """
    return f'{fullmove}.{".." if color == chess.BLACK else ""}'


def bit_len(max_states: int, /) -> int:
    """ Return the number of bits needed to represent ``max_states`` unique states. Note: may return 0. """
    return (max_states - 1).bit_length()


def get_actions_bb(from_square: chess.Square,
                   board: chess.Board,
                   *,
                   mask_legal: bool = False,
                   mask_pseudo_legal: bool = False) -> chess.Bitboard:
    """
    Return a bitboard with all the squares the piece at ``from_square`` could possibly move to or capture, assuming
    an empty board, and pawns have both available captures. Pawns on the first rank can move forward two squares.
    If ``from_legal`` or ``from_pseudo_legal`` is ``True``, return a bitboard with all the legal/pseudo-legal
    moves from ``from_square`` for the given piece type.
    """
    if mask_legal:
        piece_moves = 0
        for m in board.generate_legal_moves(from_mask=chess.BB_SQUARES[from_square]):
            piece_moves |= chess.BB_SQUARES[m.to_square]
        return piece_moves

    if mask_pseudo_legal:
        piece_moves = 0
        for m in board.generate_pseudo_legal_moves(from_mask=chess.BB_SQUARES[from_square]):
            piece_moves |= chess.BB_SQUARES[m.to_square]
        return piece_moves

    # Return pre-generated bit masks, which assume an empty board, and pawns can capture
    piece = board.piece_at(from_square)
    if piece.piece_type == chess.PAWN:
        return BB_PIECE_MOVES[piece.piece_type][piece.color][from_square]
    return BB_PIECE_MOVES[piece.piece_type][from_square]


def get_movable_pieces_bb(board: chess.Board,
                          *,
                          mask_legal: bool = False,
                          mask_pseudo_legal: bool = False) -> chess.Bitboard:
    if mask_legal:
        occupied_movable = 0
        for m in board.generate_legal_moves():
            occupied_movable |= chess.BB_SQUARES[m.from_square]
        return occupied_movable

    if mask_pseudo_legal:
        occupied_movable = 0
        for m in board.generate_pseudo_legal_moves():
            occupied_movable |= chess.BB_SQUARES[m.from_square]
        return occupied_movable

    return board.occupied_co[board.turn]


def to_int(bits: bitarray.bitarray) -> int:
    assert bits.endian() == 'big'
    i = 0
    for bit in bits:
        i = (i << 1) | bit
    return i


# def validate_is_legal(move: chess.Move,
#                       board: chess.Board,
#                       *,
#                       do_raise: bool = True) -> bool:
#     if not board.is_legal(move):
#         if do_raise:
#             raise ValueError(f'Move is not legal: {move} in {board.fen()}')
#         return False
#     return True
#
#
# def validate_is_pseudo_legal(move: chess.Move,
#                              board: chess.Board,
#                              *,
#                              do_raise: bool = True) -> bool:
#     if not board.is_pseudo_legal(move):
#         if do_raise:
#             raise ValueError(f'Move is not pseudo-legal: {move} in {board.fen()}')
#         return False
#     return True
#
#
# def concatenate_bits(a: int,
#                      b: int,
#                      *,
#                      min_len_a: int = 0,
#                      min_len_b: int = 0) -> int:
#     # TODO not working (ChatGPT)
#     num_bits_a = max(a.bit_length(), min_len_a)
#     num_bits_b = max(b.bit_length(), min_len_b)
#
#     shift_amount = num_bits_b
#
#     a_shifted = a << shift_amount
#     result = a_shifted | b
#     return result


def occupied_idx(s: chess.Square,
                 occupied: chess.Bitboard) -> int:
    """
    Take a square and return the number of truthy bits that come
    before it in the ``occupied`` bitboard for the side to move.
    """
    assert chess.BB_SQUARES[s] & occupied, 'Expected ``s`` to be an occupied square'
    return occupied.bit_count() - (occupied >> s).bit_count()


def decode_occupied_idx(index: int,
                        occupied: chess.Bitboard) -> chess.Square:
    """
    Take the number of truthy bits that come before a square in the occupied_co

    Thanks, ChatGPT!
    """
    # Initialize variables
    square = None  # Represents an invalid square

    # Iterate through the bits of the occupied bitboard
    while occupied:
        # Find the least significant set bit
        lsb = occupied & -occupied

        # Decrement the index and check if it matches the target index
        if index == 0:
            square = chess.lsb(lsb)
            break

        # Clear the least significant set bit
        occupied ^= lsb

        # Decrement the index
        index -= 1

    if square is None:
        print(f'index: {index}')
        print(f'occupied:')
        print(chess.SquareSet(occupied))
        raise AssertionError
    return square


def encode_from_square(move: chess.Move,
                       board: chess.Board,
                       *,
                       mask_legal: bool = False,
                       mask_pseudo_legal: bool = False) -> bitarray.bitarray:
    movable_pieces_bb = get_movable_pieces_bb(board,
                                              mask_legal=mask_legal,
                                              mask_pseudo_legal=mask_pseudo_legal)
    assert movable_pieces_bb
    idx = occupied_idx(move.from_square, movable_pieces_bb)
    num_bits = bit_len(movable_pieces_bb.bit_count())
    if num_bits == 0:
        return bitarray.bitarray()
    return bitarray.bitarray(format(idx, f'0{num_bits}b'))


def decode_from_square(from_square_bits: bitarray.bitarray,
                       board: chess.Board,
                       *,
                       mask_legal: bool = False,
                       mask_pseudo_legal: bool = False) -> chess.Square:
    movable_pieces_bb = get_movable_pieces_bb(board,
                                              mask_legal=mask_legal,
                                              mask_pseudo_legal=mask_pseudo_legal)
    return decode_occupied_idx(to_int(from_square_bits), movable_pieces_bb)


def encode_to_square(move: chess.Move,
                     board: chess.Board,
                     *,
                     mask_legal: bool = False,
                     mask_pseudo_legal: bool = False) -> bitarray.bitarray:
    actions_bb = get_actions_bb(move.from_square,
                                board,
                                mask_legal=mask_legal,
                                mask_pseudo_legal=mask_pseudo_legal)
    idx = occupied_idx(move.to_square, actions_bb)
    num_bits = bit_len(actions_bb.bit_count())
    if num_bits == 0:
        return bitarray.bitarray()
    return bitarray.bitarray(format(idx, f'0{num_bits}b'))


def decode_to_square(from_square: chess.Square,
                     to_square_bits: bitarray.bitarray,
                     board: chess.Board,
                     *,
                     mask_legal: bool = False,
                     mask_pseudo_legal: bool = False) -> chess.Square:
    actions_bb = get_actions_bb(from_square,
                                board,
                                mask_legal=mask_legal,
                                mask_pseudo_legal=mask_pseudo_legal)
    assert actions_bb
    return decode_occupied_idx(to_int(to_square_bits), actions_bb)


def encode_move(move: chess.Move,
                board: chess.Board,
                *,
                mask_legal: bool = False,
                mask_pseudo_legal: bool = False) -> bitarray.bitarray:
    encoded_from_sq = encode_from_square(move,
                                         board,
                                         mask_legal=mask_legal,
                                         mask_pseudo_legal=mask_pseudo_legal)
    encoded_to_sq = encode_to_square(move,
                                     board,
                                     mask_legal=mask_legal,
                                     mask_pseudo_legal=mask_pseudo_legal)
    return encoded_from_sq + encoded_to_sq


def decode_move(bits: bitarray.bitarray,
                board: chess.Board,
                *,
                mask_legal: bool = False,
                mask_pseudo_legal: bool = False) -> Tuple[chess.Move, int]:
    """ Decode a move from the given bitarray; return it and the number of bits consumed (``bits`` may
    contain more bits than necessary to decode the move). """

    movable_pieces_bb = get_movable_pieces_bb(board,
                                              mask_legal=mask_legal,
                                              mask_pseudo_legal=mask_pseudo_legal)
    from_square_bit_len = bit_len(movable_pieces_bb.bit_count())

    from_square = decode_from_square(bits[:from_square_bit_len],
                                     board,
                                     mask_legal=mask_legal,
                                     mask_pseudo_legal=mask_pseudo_legal)

    actions_bb = get_actions_bb(from_square,
                                board,
                                mask_legal=mask_legal,
                                mask_pseudo_legal=mask_pseudo_legal)

    to_square_bit_len = bit_len(actions_bb.bit_count())
    to_square = decode_to_square(from_square,
                                 bits[from_square_bit_len:from_square_bit_len + to_square_bit_len],
                                 board,
                                 mask_legal=mask_legal,
                                 mask_pseudo_legal=mask_pseudo_legal)

    return chess.Move(from_square, to_square), from_square_bit_len + to_square_bit_len


def encode_moves(moves: List[chess.Move],
                 starting_fen: str,
                 *,
                 mask_legal: bool = False,
                 mask_pseudo_legal: bool = False) -> bitarray.bitarray:
    """ Return a tuple of the starting FEN and the encoded moves for the given game. """
    encoded_moves = bitarray.bitarray()
    board = chess.Board(starting_fen)
    for move in moves:
        encoded_moves += encode_move(move,
                                     board,
                                     mask_legal=mask_legal,
                                     mask_pseudo_legal=mask_pseudo_legal)
        board.push(move)
    return encoded_moves


def decode_moves(bits: bitarray.bitarray,
                 starting_fen: str,
                 *,
                 mask_legal: bool = False,
                 mask_pseudo_legal: bool = False,
                 moves: List[chess.Move] = None) -> List[chess.Move]:
    board = chess.Board(starting_fen)
    while bits:
        move, num_consumed = decode_move(bits,
                                         board,
                                         mask_legal=mask_legal,
                                         mask_pseudo_legal=mask_pseudo_legal)
        if moves is not None:
            if moves[board.ply()] != move:
                move_num = format_fullmove(board.fullmove_number, board.turn)
                print(f'Error: decoded to {move_num}{move}, '
                      f'expected {move_num}{moves[board.ply()]}')

        board.push(move)
        bits = bits[num_consumed:]


    return board.move_stack


if __name__ == '__main__':
    pgn = '''[Event "Casual Bullet game"]
[Site "https://lichess.org/Y2hanlPl"]
[Date "2022.07.01"]
[White "Goldy35"]
[Black "penguingm1"]
[Result "0-1"]
[UTCDate "2022.07.01"]
[UTCTime "21:10:02"]
[WhiteElo "1133"]
[BlackElo "2481"]
[BlackTitle "GM"]
[Variant "Standard"]
[TimeControl "60+0"]
[ECO "D31"]
[Opening "Queen's Gambit Declined: Charousek Variation"]
[Termination "Time forfeit"]
[Annotator "lichess.org"]

1. d4 d5 2. c4 e6 3. Nc3 Be7 { D31 Queen's Gambit Declined: Charousek Variation } 4. Nf3 Nf6 5. cxd5 exd5 6. Bf4 c6 7. e3 Bf5 8. Be2 Nbd7 9. O-O O-O 10. h3 h6 11. Rc1 Re8 12. Re1 Nf8 13. e4?? { (0.13 → -2.18) Blunder. Ne5 was best. } (13. Ne5 Bd6 14. Bd3 Bxd3 15. Nxd3 Bxf4 16. Nxf4 Ne6 17. Nd3 a5 18. a3 Re7 19. b4 Nc7) 13... Nxe4 14. Bd3 Nxc3 15. bxc3 Bxd3 16. Qxd3 Ne6?! { (-1.70 → -0.85) Inaccuracy. Bf6 was best. } (16... Bf6 17. Be5) 17. Bh2?! { (-0.85 → -1.93) Inaccuracy. Rxe6 was best. } (17. Rxe6 fxe6) 17... Bd6 18. Bxd6 Qxd6 19. Ne5 Re7 20. Re3 Rae8 21. Rce1 Nf4?! { (-2.06 → -1.07) Inaccuracy. Ng5 was best. } (21... Ng5) 22. Qf5 Ne6 23. f4?! { (-1.43 → -2.50) Inaccuracy. h4 was best. } (23. h4 Nf8) 23... Nf8 24. Qd3 f6 25. Nxc6?? { (-2.82 → -7.78) Blunder. Nf3 was best. } (25. Nf3) 25... bxc6 26. Rxe7 Rxe7 27. Rxe7 Qxe7 { Black wins on time. } 0-1'''
    game = chess.pgn.read_game(io.StringIO(pgn))

    moves = list(game.mainline_moves())
    starting_fen = game.board().fen()

    results: Dict[Tuple[bool, bool], Tuple[float, int]] = {}

    for mask_legal, mask_pseudo_legal in ((False, False), (False, True), (True, True)):
        print(f'mask_legal: {mask_legal}, mask_pseudo_legal: {mask_pseudo_legal}')
        with ContextTimer(5) as t:
            for _ in range(1000):
                encoded = encode_moves(moves,
                                       starting_fen,
                                       mask_legal=mask_legal,
                                       mask_pseudo_legal=mask_pseudo_legal)
                decoded = decode_moves(encoded,
                                       starting_fen,
                                       mask_legal=mask_legal,
                                       mask_pseudo_legal=mask_pseudo_legal,
                                       moves=moves)

        print(f'Encoded: {encoded}')
        print(f'Decoded: {decoded}')
        print(f'Correct decoding: {moves == decoded}')
        print()

        results[(mask_legal, mask_pseudo_legal)] = t.time, len(encoded)

    # Get the baseline and compare the other results to it
    baseline = results[(False, False)]
    baseline_time, baseline_bits_used = baseline
    for (mask_legal, mask_pseudo_legal), (time, bits_used) in results.items():
        print(f'mask_legal: {mask_legal}, mask_pseudo_legal: {mask_pseudo_legal}')
        print(f'Time: {time:.3f} seconds')
        print(f'Bits used: {bits_used}')
        print(f'Time ratio to baseline: {time / baseline_time:.3f}')
        print(f'Bits used ratio to baseline: {bits_used / baseline_bits_used:.3f}')
        print()
