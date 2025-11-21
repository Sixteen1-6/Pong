import socket
import threading
import json
import time
import http.server
import socketserver

# ------------------------------------------------------------------------------
# Basic configuration
# ------------------------------------------------------------------------------

HOST = "localhost"    # game server address
GAME_PORT = 5000      # match the port used by your Pong client
HTTP_PORT = 8000      # port for leaderboard HTTP server (non-privileged)
WIN_SCORE = 5         # points needed to win a game

# ------------------------------------------------------------------------------
# Shared state: games and leaderboard
# ------------------------------------------------------------------------------

class GameSession:
    """
    Represents a single Pong match between two players.

    The design here follows the instructor's threaded chat server:
    - one GameSession per match
    - a small lock to coordinate updates between both player threads
    """

    def __init__(self, game_id: int):
        self.game_id = game_id

        # player info: side -> {"name": str, "sock": socket, "addr": (ip, port)}
        self.players = {
            "left": None,
            "right": None,
        }

        # a simple, shared game state for both players
        self.state = {
            "sync": 0,                         # server-side tick counter
            "paddles": {                       # paddle positions by side
                "left": [0.0, 0.0],
                "right": [0.0, 0.0],
            },
            "ball": [0.0, 0.0],                # last reported ball position
            "score": {                         # logical scores by side
                "left": 0,
                "right": 0,
            },
            "running": True                    # set False to end the game
        }

        # used by both player threads to avoid race conditions
        self.lock = threading.Lock()


# all ongoing games, indexed by game_id
games: dict[int, GameSession] = {}

# used to pair players into games (similar idea to a “waiting room”)
waiting_player = None  # (game_id, side)

# used to hand out unique game IDs
next_game_id = 1

# leaderboard: player_name -> wins
leaderboard: dict[str, int] = {}
leaderboard_lock = threading.Lock()


# ------------------------------------------------------------------------------
# Leaderboard utilities
# ------------------------------------------------------------------------------

def update_leaderboard(winner_name: str) -> None:
    """
    Increment the winner's score and write out leaderboard.json.

    The file format is a simple list of objects:
        [{}, {"name": "Alice", "score": 3}, ...]
    """


# ------------------------------------------------------------------------------
# HTTP server to expose leaderboard.json
# ------------------------------------------------------------------------------

def start_http_server() -> None:
    """
    Very small HTTP server that serves files from the current directory.
    This follows the instructor's SimpleHTTPRequestHandler examples.
    """

# ------------------------------------------------------------------------------
# Game logic helpers
# ------------------------------------------------------------------------------

def decide_winner(score_dict: dict[str, int]) -> str | None:
    """
    Given the internal score dictionary, decide if there is a winner.
    Returns 'left', 'right', or None.
    """


def build_state_for_client(session: GameSession, side: str) -> dict:
    """
    Convert the internal GameSession.state into the JSON structure expected
    by the Pong client. This keeps the JSON keys aligned with the client
    while we are free to store things however we like internally.
    """


# ------------------------------------------------------------------------------
# Per-player thread
# ------------------------------------------------------------------------------

def handle_player(session: GameSession, side: str) -> None:
    """
    Thread entry point for a single player in a GameSession.

    Patterned after the instructor's threaded chat server:
    - one thread per client
    - each loop iteration: recv, process, send
    """

    player_info = session.players[side]
    sock = player_info["sock"]
    name = player_info["name"]
    addr = player_info["addr"]

    print(f"[GAME {session.game_id}] {name} ({side}) connected from {addr}")

    # initial handshake: tell the client which side it is and the screen size
    # (match these values with what your Pong client expects)
    handshake = {
        "side": side,
        "width": 640,
        "height": 480,
    }
    sock.send(json.dumps(handshake).encode())

    try:
        while True:
            # small delay to avoid busy-looping
            time.sleep(0.01)

            data = sock.recv(4096)
            if not data:
                # client disconnected
                print(f"[GAME {session.game_id}] {name} disconnected")
                break

            try:
                msg = json.loads(data.decode())
            except json.JSONDecodeError:
                print(f"[GAME {session.game_id}] Bad JSON from {name}: {data!r}")
                continue

            # Extract fields from client's message. These key names must match what
            # your Pong client actually sends.
            client_sync = msg.get("sync", 0)
            client_score = msg.get("score", [0, 0])
            client_paddle = msg.get("paddle", [0.0, 0.0])
            client_ball = msg.get("ball", [0.0, 0.0])

            with session.lock:
                # Update server-side sync as a simple max of what we've seen.
                # This is different from "copy opponent state if behind" and is
                # more like a monotonic tick counter.
                session.state["sync"] = max(session.state["sync"], client_sync)

                # Update this player's paddle position
                session.state["paddles"][side] = [
                    float(client_paddle[0]),
                    float(client_paddle[1]),
                ]

                # Trust the last reported ball position; whichever side sends last wins
                session.state["ball"] = [
                    float(client_ball[0]),
                    float(client_ball[1]),
                ]

                # Update score if this update represents progress
                # Map client score array to internal left/right
                left_score, right_score = int(client_score[0]), int(client_score[1])

                # Only accept a score update if the total has increased
                current_total = session.state["score"]["left"] + session.state["score"]["right"]
                new_total = left_score + right_score

                if new_total >= current_total:
                    session.state["score"]["left"] = left_score
                    session.state["score"]["right"] = right_score

                # Check for winner
                winner_side = decide_winner(session.state["score"])
                if winner_side is not None and session.state["running"]:
                    session.state["running"] = False
                    winner_name = session.players[winner_side]["name"]
                    print(f"[GAME {session.game_id}] {winner_name} ({winner_side}) wins!")

                    # record win in leaderboard
                    update_leaderboard(winner_name)

            # Build and send response based on the shared state
            response = build_state_for_client(session, side)
            sock.send(json.dumps(response).encode())

            # If the game has ended, close this player's loop
            if not session.state["running"]:
                break

    except (ConnectionResetError, OSError):
        print(f"[GAME {session.game_id}] Connection error with {name}")

    finally:
        sock.close()
        print(f"[GAME {session.game_id}] Closed socket for {name} ({side})")


# ------------------------------------------------------------------------------
# Connection handling: pairing players into games
# ------------------------------------------------------------------------------

def accept_and_pair_clients(server_socket: socket.socket) -> None:
    """
    Main loop for the game server.

    This follows the instructor's pattern:
    - accept a client
    - create a thread to handle that client
    - use a shared "waiting_player" to pair two clients into a GameSession
    """
    global waiting_player, next_game_id

    print(f"[GAME SERVER] Listening on {HOST}:{GAME_PORT}")

    while True:
        conn, addr = server_socket.accept()

        # first thing the client does: send its chosen name
        try:
            raw_name = conn.recv(1024)
        except OSError:
            conn.close()
            continue

        name = raw_name.decode().strip()
        if not name or not name.isalnum():
            print("[GAME SERVER] Rejected connection with invalid name")
            conn.close()
            continue

        # Pair this player into a game session.
        # We mimic a simple matchmaking queue using waiting_player.
        with threading.Lock():  # short-lived lock for pairing
            if waiting_player is None:
                # Create new GameSession and assign this player as left
                game_id = next_game_id
                next_game_id += 1

                session = GameSession(game_id)
                games[game_id] = session

                session.players["left"] = {
                    "name": name,
                    "sock": conn,
                    "addr": addr,
                }

                waiting_player = (game_id, "left")
                print(f"[GAME SERVER] {name} is waiting in game {game_id} as left")

            else:
                game_id, other_side = waiting_player
                session = games[game_id]

                # assign this player as the opposite side
                side = "right" if other_side == "left" else "left"
                session.players[side] = {
                    "name": name,
                    "sock": conn,
                    "addr": addr,
                }

                print(f"[GAME SERVER] Game {game_id} matched: "
                      f"{session.players['left']['name']} (left) vs "
                      f"{session.players['right']['name']} (right)")

                # clear waiting_player since we just formed a full game
                waiting_player = None

                # start threads for both players
                left_thread = threading.Thread(
                    target=handle_player,
                    args=(session, "left"),
                    daemon=True,
                )
                right_thread = threading.Thread(
                    target=handle_player,
                    args=(session, "right"),
                    daemon=True,
                )

                left_thread.start()
                right_thread.start()

        # Note: we do not start a thread for the waiting player yet; their thread
        # is only started once they are paired. You could also start immediately,
        # but then you'd need to block until an opponent arrives.


# ------------------------------------------------------------------------------
# Entry point: start HTTP and game servers
# ------------------------------------------------------------------------------

def start_game_server() -> None:
    """
    Create the TCP server socket (following the instructor's examples),
    then call accept_and_pair_clients to handle incoming connections.
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, GAME_PORT))
    server_socket.listen()

    try:
        accept_and_pair_clients(server_socket)
    finally:
        server_socket.close()


if __name__ == "__main__":
    # Start HTTP leaderboard server in the background
    http_thread = threading.Thread(target=start_http_server, daemon=True)
    http_thread.start()

    # Start the main game server loop
    start_game_server()
