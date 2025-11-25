# =================================================================================================
# Contributing Authors:     Shubhanshu Pokharel, Aaron Lin, Ayham Yousef
# Email Addresses:          spo283@uky.edu, ayli222@uky.edu, afyo223@uky.edu
# Date:                     3 November 2025
# Purpose:                  Server side for multiplayer Pong game with authentication
# Misc:                     Handles TCP game state sync and HTTP leaderboard hosting
# =================================================================================================

import socket
import threading
import json
from dataclasses import dataclass, field
from typing import Optional, Dict, Tuple
import time
import http.server
import socketserver

# Import authentication modules
from token_manager import verify_token
from encryption import encrypt_message, decrypt_message
from auth_server import start_auth_server

leaderboard_lock = threading.Lock()

# -----------------------------------------------------------------------------------
# Game state representation with Play Again support
# -----------------------------------------------------------------------------------

SERVER_IP = "0.0.0.0"
START_DELAY = 1

@dataclass
class Vec2:
    """Represents a 2D vector/position with clear x,y semantics."""
    x: float = 0.0
    y: float = 0.0
    
    def to_list(self) -> list:
        """Convert to [x, y] list for JSON serialization."""
        return [self.x, self.y]
    
    @classmethod
    def from_list(cls, data: list) -> 'Vec2':
        """Create Vec2 from [x, y] list."""
        return cls(x=data[0], y=data[1])


@dataclass
class PaddleState:
    """Represents a single paddle's state."""
    position: Vec2 = field(default_factory=Vec2)
    
    def to_list(self) -> list:
        """Convert to [x, y] for JSON."""
        return self.position.to_list()
    
    @classmethod
    def from_list(cls, data: list) -> 'PaddleState':
        """Create PaddleState from [x, y] list."""
        return cls(position=Vec2.from_list(data))


@dataclass
class BallState:
    """Represents the ball's state."""
    position: Vec2 = field(default_factory=Vec2)
    
    def to_list(self) -> list:
        """Convert to [x, y] for JSON."""
        return self.position.to_list()
    
    @classmethod
    def from_list(cls, data: list) -> 'BallState':
        """Create BallState from [x, y] list."""
        return cls(position=Vec2.from_list(data))


@dataclass
class Score:
    """Represents the score for both players."""
    left: int = 0
    right: int = 0
    
    def to_list(self) -> list:
        """Convert to [left, right] for JSON."""
        return [self.left, self.right]
    
    @classmethod
    def from_list(cls, data: list) -> 'Score':
        """Create Score from [left, right] list."""
        return cls(left=int(data[0]), right=int(data[1]))
    
    def winner(self) -> Optional[str]:
        """Return 'left' or 'right' if someone won, else None."""
        if self.left >= 5:
            return "left"
        elif self.right >= 5:
            return "right"
        return None
    
    def reset(self) -> None:
        """Reset scores to 0."""
        self.left = 0
        self.right = 0


@dataclass
class GameState:
    """Game state representation with clear semantics."""
    sync: int = 0
    left_paddle: PaddleState = field(default_factory=PaddleState)
    right_paddle: PaddleState = field(default_factory=PaddleState)
    ball: BallState = field(default_factory=BallState)
    score: Score = field(default_factory=Score)
    active: bool = False
    game_over: bool = False
    play_again: Optional[bool] = None
    
    def to_json_response(self) -> dict:
        """Convert game state to JSON format expected by client."""
        return {
            "sync": self.sync,
            "left": self.left_paddle.to_list(),
            "right": self.right_paddle.to_list(),
            "ball": self.ball.to_list(),
            "score": self.score.to_list(),
            "game_over": self.game_over,
            "play_again": self.play_again
        }
    
    def update_from_client(self, client_data: dict, is_left: bool) -> None:
        """Update game state from client data."""
        self.sync = client_data["sync"]
        
        if not self.game_over:
            self.score = Score.from_list(client_data["score"])
        
        if "play_again" in client_data:
            self.play_again = client_data["play_again"]
        
        paddle_data = PaddleState.from_list(client_data["paddle"])
        if is_left:
            self.left_paddle = paddle_data
        else:
            self.right_paddle = paddle_data
        
        if is_left and not self.game_over:
            self.ball = BallState.from_list(client_data["ball"])
    
    def reset_for_new_game(self, screen_width: int, screen_height: int) -> None:
        """Reset state for a new game."""
        self.sync = 0
        self.score.reset()
        self.ball = BallState(position=Vec2(screen_width / 2, screen_height / 2))
        self.game_over = False
        self.play_again = None
        self.active = True


@dataclass
class Game:
    """Represents a complete game between two players with Play Again support."""
    id: int
    left_state: GameState = field(default_factory=GameState)
    right_state: GameState = field(default_factory=GameState)
    left_player: Optional[str] = None
    right_player: Optional[str] = None
    screen_width: int = 640
    screen_height: int = 480
    waiting_for_play_again: bool = False
    rematch_processed: bool = False
    game_lock: threading.Lock = field(default_factory=threading.Lock)
    
    def initialize(self, screen_width: int, screen_height: int) -> None:
        """Initialize game with starting positions."""
        self.screen_width = screen_width
        self.screen_height = screen_height
        center = Vec2(screen_width / 2, screen_height / 2)
        
        self.left_state.ball = BallState(position=Vec2(center.x, center.y))
        self.right_state.ball = BallState(position=Vec2(center.x, center.y))
        
        self.left_state.active = True
        self.right_state.active = True
    
    def get_state(self, is_left: bool) -> GameState:
        """Get the appropriate state for the given player."""
        return self.left_state if is_left else self.right_state
    
    def get_opponent_state(self, is_left: bool) -> GameState:
        """Get the opponent's state."""
        return self.right_state if is_left else self.left_state
    
    def is_active(self) -> bool:
        """Check if game is still active."""
        return self.left_state.active and self.right_state.active
    
    def mark_game_over(self) -> None:
        """Mark game as over but keep connection alive for play again."""
        with self.game_lock:
            if not self.left_state.game_over:
                self.left_state.game_over = True
                self.right_state.game_over = True
                self.waiting_for_play_again = True
                print(f"Game {self.id} marked as over, waiting for play again decisions")
    
    def both_want_rematch(self) -> bool:
        """Check if both players want to play again."""
        return (self.left_state.play_again is True and 
                self.right_state.play_again is True)
    
    def either_declined(self) -> bool:
        """Check if either player declined rematch."""
        return (self.left_state.play_again is False or 
                self.right_state.play_again is False)
    
    def both_decided(self) -> bool:
        """Check if both players have made a decision."""
        return (self.left_state.play_again is not None and 
                self.right_state.play_again is not None)
    
    def reset_for_rematch(self) -> bool:
        """Reset game state for a rematch."""
        with self.game_lock:
            if self.rematch_processed:
                return False
            
            self.rematch_processed = True
            print(f"Resetting game {self.id} for rematch")
            
            self.left_state.reset_for_new_game(self.screen_width, self.screen_height)
            self.right_state.reset_for_new_game(self.screen_width, self.screen_height)
            self.waiting_for_play_again = False
            
            time.sleep(0.1)
            
            self.rematch_processed = False
            
            return True
    
    def end_game(self) -> None:
        """Permanently end the game and close connections."""
        self.left_state.active = False
        self.right_state.active = False


# Global game manager
class GameManager:
    """Manages all active games."""
    
    def __init__(self):
        self.games: Dict[int, Game] = {}
        self.next_game_id = 0
        self.lock = threading.Lock()
    
    def create_game(self) -> int:
        """Create a new game and return its ID."""
        with self.lock:
            game_id = self.next_game_id
            self.games[game_id] = Game(id=game_id)
            self.next_game_id += 1
            return game_id
    
    def get_game(self, game_id: int) -> Optional[Game]:
        """Get a game by ID."""
        return self.games.get(game_id)
    
    def remove_game(self, game_id: int) -> None:
        """Remove a game from the manager."""
        with self.lock:
            if game_id in self.games:
                del self.games[game_id]


# Global instances
game_manager = GameManager()
leaderboard: Dict[str, int] = {}


# Leaderboard utilities
def save_leaderboard() -> None:
    """Write the current in-memory leaderboard to 'leaderboard.json'."""
    with leaderboard_lock:
        sorted_items = sorted(
            leaderboard.items(), key=lambda x: x[1], reverse=True
        )
        with open("leaderboard.json", "w") as leaderboard_file:
            leaderboard_file.write("[{}")
            for player_name, score in sorted_items:
                leaderboard_file.write(
                    f',{{"name":"{player_name}","score":{score}}}\n'
                )
            leaderboard_file.write("]")


def reset_leaderboard() -> None:
    """Reset the in-memory leaderboard and overwrite file."""
    global leaderboard
    leaderboard = {}
    with open("leaderboard.json", "w") as leaderboard_file:
        leaderboard_file.write("[{}]")


def load_leaderboard() -> None:
    """Load leaderboard data from 'leaderboard.json'."""
    global leaderboard
    try:
        with open("leaderboard.json", "r") as leaderboard_file:
            temp_leaderboard = json.load(leaderboard_file)
        leaderboard = {
            item["name"]: item["score"]
            for item in temp_leaderboard[1:]
            if "name" in item and "score" in item
        }
    except (FileNotFoundError, json.JSONDecodeError, IndexError, KeyError):
        leaderboard = {}


# Client thread handler with encryption
def clientThread(
    name: str,
    clientSocket: socket.socket,
    clientAddress: Tuple,
    gameId: int,
    isLeft: bool,
) -> None:
    """Handle all communication with a single client with encryption."""
    SCREEN_HEIGHT = 480
    SCREEN_WIDTH = 640
    
    leaderboard[name] = leaderboard.get(name, 0)
    
    game = game_manager.get_game(gameId)
    if not game:
        print(f"Error: Game {gameId} not found")
        clientSocket.close()
        return
    
    if isLeft:
        game.left_player = name
    else:
        game.right_player = name
    
    game.initialize(SCREEN_WIDTH, SCREEN_HEIGHT)
    
    side_string = "left" if isLeft else "right"
    preliminary_data = {
        "side": side_string,
        "height": SCREEN_HEIGHT,
        "width": SCREEN_WIDTH,
    }
    # Send preliminary data encrypted
    encrypted_prelim = encrypt_message(json.dumps(preliminary_data))
    clientSocket.send(encrypted_prelim)
    
    player_state = game.get_state(isLeft)
    opponent_state = game.get_opponent_state(isLeft)
    
    time.sleep(START_DELAY)

    winner_logged = False
    
    while game.is_active():
        time.sleep(0.01)
        
        try:
            # Receive encrypted data
            encrypted_data = clientSocket.recv(2048)
            if not encrypted_data:
                print(f"No data received; closing connection for {name}")
                break
            
            # Decrypt and parse
            decrypted = decrypt_message(encrypted_data)
            data = json.loads(decrypted)
            
            player_state.update_from_client(data, isLeft)
            
            if not game.waiting_for_play_again:
                if not isLeft:
                    player_state.ball = BallState(
                        position=Vec2(opponent_state.ball.position.x, 
                                     opponent_state.ball.position.y)
                    )
                
                if isLeft:
                    player_state.right_paddle = PaddleState(
                        position=Vec2(opponent_state.right_paddle.position.x,
                                     opponent_state.right_paddle.position.y)
                    )
                else:
                    player_state.left_paddle = PaddleState(
                        position=Vec2(opponent_state.left_paddle.position.x,
                                     opponent_state.left_paddle.position.y)
                    )
                
                if player_state.sync < opponent_state.sync:
                    player_state.sync = opponent_state.sync
                    player_state.score = Score(left=opponent_state.score.left,
                                              right=opponent_state.score.right)
                
                winner = player_state.score.winner()
                if winner and not winner_logged:
                    game.mark_game_over()
                    winner_logged = True
                    print(f"Game {gameId} over. Winner: {winner}")
                    
                    if (isLeft and winner == "left") or (not isLeft and winner == "right"):
                        leaderboard[name] = leaderboard.get(name, 0) + 1
                        save_leaderboard()
            
            elif game.waiting_for_play_again:
                if game.both_decided():
                    if game.both_want_rematch():
                        if game.reset_for_rematch():
                            print(f"Both players want rematch in game {gameId} - resetting")
                            player_state = game.get_state(isLeft)
                            opponent_state = game.get_opponent_state(isLeft)
                        winner_logged = False
                        
                    elif game.either_declined():
                        print(f"Rematch declined in game {gameId}")
                        game.end_game()
                        
                        response = player_state.to_json_response()
                        encrypted_response = encrypt_message(json.dumps(response))
                        clientSocket.send(encrypted_response)
                        break
            
            # Send encrypted response
            response = player_state.to_json_response()
            encrypted_response = encrypt_message(json.dumps(response))
            clientSocket.send(encrypted_response)
                
        except Exception as e:
            print(f"Error in client thread for {name}: {e}")
            break
    
    clientSocket.close()
    print(f"Closed connection for {name}")


# Server setup with token verification
def establishServer() -> None:
    """Create the main TCP server socket and accept client connections."""
    port = 8080
    
    # Start authentication server
    auth_thread = threading.Thread(target=start_auth_server, daemon=True)
    auth_thread.start()
    
    # Start HTTP leaderboard server
    html_thread = threading.Thread(target=startLeaderboardServer, daemon=True)
    html_thread.start()
    
    # Create TCP server
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((SERVER_IP, port))
    server.listen(5)
    print(f"Pong server listening on {SERVER_IP}:{port}")
    
    waiting_player = None
    
    while True:
        clientSocket, clientAddress = server.accept()
        
        try:
            # Receive encrypted token
            encrypted_token = clientSocket.recv(1024)
            token = decrypt_message(encrypted_token)
            
            # Verify token
            username = verify_token(token)
            if not username:
                print(f"Invalid token from {clientAddress}")
                clientSocket.send(encrypt_message("INVALID_TOKEN"))
                clientSocket.close()
                continue
            
            # Send acknowledgment
            clientSocket.send(encrypt_message("TOKEN_OK"))
            
            print(f"{username} Connected. | Address: {clientAddress[0]} Port: {clientAddress[1]}")
            
            if waiting_player is None:
                game_id = game_manager.create_game()
                waiting_player = (username, clientSocket, clientAddress, game_id)
            else:
                left_name, left_sock, left_addr, game_id = waiting_player
                
                left_thread = threading.Thread(
                    target=clientThread,
                    args=(left_name, left_sock, left_addr, game_id, True),
                    daemon=True
                )
                right_thread = threading.Thread(
                    target=clientThread,
                    args=(username, clientSocket, clientAddress, game_id, False),
                    daemon=True
                )
                
                left_thread.start()
                right_thread.start()
                
                print(f"Starting game {game_id} between {left_name} and {username}")
                
                waiting_player = None
                
        except Exception as e:
            print(f"Connection error: {e}")
            clientSocket.close()


# HTTP server for leaderboard
def startLeaderboardServer() -> None:
    """Start HTTP server for leaderboard on port 80."""
    PORT = 80
    Handler = http.server.SimpleHTTPRequestHandler
    
    with socketserver.TCPServer((SERVER_IP, PORT), Handler) as httpd:
        print("HTTP leaderboard server serving at port", PORT)
        httpd.serve_forever()


# Program entry point
if __name__ == "__main__":
    reset_leaderboard()
    establishServer()