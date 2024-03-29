
def one_hot_encode(number, buckets=None):
    if not buckets or buckets < 0:
        buckets = number

    lst = [0]*buckets
    if number > 0:
        lst[number - 1] = 1
    return lst


class Hex:

    def __init__(self, size=5):
        self.size = size

    def get_initial_state(self):
        return [0] * (self.size**2), 0

    def get_moves(self, state):
        moves = []
        board = state[0]
        player = state[1]
        for i in range(self.size):
            for j in range(self.size):
                if board[i * self.size + j] == 0:
                    new_board = board[:]
                    new_board[i * self.size + j] = player + 1
                    moves.append((((i, j), player), (new_board, int(not player))))
        return moves

    def get_outcome_state(self, initial_state, move):
        pos = move[0]
        board = initial_state[0][:]
        player = initial_state[1]
        player_moving = move[1]

        if player != player_moving:
            raise Exception('Player ' + str(player_moving) + ' is not in the move in the given state!')
        if board[pos[0] * self.size + pos[1]] != 0:
            raise Exception('There is already a stone in the given position!')
        board[pos[0] * self.size + pos[1]] = player_moving + 1
        return board, int(not player)

    def get_move_string(self, inital_state, move):
        return "Player {} put a stone down in position ({}, {}).".format(move[1], move[0][0], move[0][1])

    def get_state_string(self, state):
        newsize = self.size * 2 - 1
        grid = [[" " for x in range(newsize)] for y in range(newsize)]
        for i in range(self.size):
            for j in range(self.size):
                y = i + j
                x = (self.size - 1) + j - i
                grid[y][x] = state[0][i * self.size + j]
        return '\n'.join([" ".join(str(item) for item in row) for row in grid])

    def unflatten(self, board):
        for i in range(0, len(board), self.size):
            yield board[i:i + self.size]

    def _get_neighbours(self, slot):
        y = slot[0]
        x = slot[1]
        neighbours = []
        if y > 0:
            neighbours.append((y-1, x))
            if x + 1 < self.size:
                neighbours.append((y-1, x+1))
        if y + 1 < self.size:
            if x > 0:
                neighbours.append((y+1, x-1))
            neighbours.append((y+1, x))
        if x > 0:
            neighbours.append((y, x-1))
        if x + 1 < self.size:
            neighbours.append((y, x+1))
        return neighbours

    def evaluate_state(self, state):
        player = state[1]

        for i in range(self.size):
            if self.is_connected_to_edge(state, (0, i), 0, True):
                return 1
            if self.is_connected_to_edge(state, (i, 0), 1, True):
                return -1

        return 0

    def is_connected_to_edge(self, state, pos, player=None, last_edge=False):
        visited = []
        board = state[0]

        if player is None:
            player = board[pos[0]*self.size + pos[1]]
        else:
            player += 1

        if player == 0:
            return False

        def is_connected(pos):
            if board[pos[0]*self.size + pos[1]] != player:
                return False

            visited.append(pos)
            if player == 1 and (pos[0] == self.size - 1 and last_edge or pos[0] == 0 and not last_edge)\
                    or player == 2 and (pos[1] == self.size - 1 and last_edge or pos[1] == 0 and not last_edge):
                return True

            for neighbour in self._get_neighbours(pos):
                if state[0][neighbour[0] * self.size + neighbour[1]] == player\
                        and neighbour not in visited:
                    result = is_connected(neighbour)
                    if result:
                        return True
            visited.remove(pos)
            return False
        return is_connected(pos)

    def is_finished(self, state):
        return self.evaluate_state(state) != 0

    def num_possible_moves(self):
        return self.size**2

    def state_size(self, format='one_hot'):
        if format == 'one_hot':
            return self.size**2 * 2 + 2
        if format == '6-channel':
            return self.size**2 * 6 + 2
        return self.size**2 + 1

    def format_for_nn(self, state, format='one_hot'):
        player = state[1]
        board = state[0]

        formatted_state = []
        for i in range(self.size):
            for j in range(self.size):
                s = board[i * self.size + j]
                if format == 'one_hot':
                    formatted_state.extend(one_hot_encode(s, 2))
                elif format == '6-channel':
                    formatted_state.extend(one_hot_encode(s, 2))
                    
                    conn_start = self.is_connected_to_edge(state, (i, j))
                    conn_end = self.is_connected_to_edge(state, (i, j), last_edge=True)
                    formatted_state.append(int(conn_start and s == 1))
                    formatted_state.append(int(conn_end and s == 1))
                    formatted_state.append(int(conn_start and s == 2))
                    formatted_state.append(int(conn_end and s == 2))
                else:
                    if s == 1:
                        formatted_state.append(1)
                    elif s == 2:
                        formatted_state.append(-1)
                    else:
                        formatted_state.append(0)

        if format in ['one_hot', '6-channel']:
            formatted_state.extend(one_hot_encode(player + 1, 2))
        else:
            if player == 0:
                formatted_state.append(1)
            else:
                formatted_state.append(-1)

        return formatted_state


if __name__ == '__main__':
    hex = Hex()
    board = [
        1, 1, 2, 1, 1,
        2, 1, 1, 1, 2,
        2, 0, 2, 1, 0,
        0, 2, 2, 2, 2,
        2, 0, 0, 2, 0,
    ]

    s = (board, 0)
    print(hex.is_connected_to_edge(s, (4, 0), last_edge=True))
    print(hex.is_finished(s))
