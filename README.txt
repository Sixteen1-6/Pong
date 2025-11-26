Contact Info
============

Group Members & Email Addresses:

    Shubhanshu Pokharel, spo283@uky.edu 
    Aaron Lin, ayli222@uky.edu 
    Ayham Yousef, afyo223@uky.edu

Versioning
==========

Github Link: https://github.com/Sixteen1-6/Pong

General Info
============

This is a multiplayer Pong game with secure authentication and encrypted 
communication. The game features user registration/login, real-time gameplay 
between two players, a play-again feature for rematches, and a web-based 
leaderboard that tracks wins.

The project uses three servers running simultaneously:
- Game Server (Port 8080) - Handles gameplay synchronization
- Authentication Server (Port 8081) - Handles login/registration
- HTTP Leaderboard Server (Port 80) - Serves leaderboard webpage

Install Instructions
====================

1. Install required Python libraries:

   pip3 install -r requirements.txt

   This installs pygame and cryptography packages.

2. Ensure Python 3.8 or higher is installed on your system.

How to Run
==========

SERVER SETUP:
-------------

1. Start the server by running:

   python3 pongServer_auth.py

   Note: Running on port 80 requires administrator privileges:
   - Linux/macOS: sudo python3 pongServer_auth.py
   - Windows: Run terminal as Administrator

2. The server will start three components automatically:
   - Authentication server on port 8081
   - Game server on port 8080
   - HTTP leaderboard server on port 80

3. You should see output confirming all three servers are running.

CLIENT SETUP:
-------------

1. Run the client on each player's machine:

   python3 pongClient_auth.py

2. First-time users must register:
   - Select "Register" from the authentication screen
   - Enter a unique alphanumeric username
   - Enter a password (minimum 4 characters)
   - Click "Register"

3. Returning users login:
   - Enter your username and password
   - Click "Login"

4. Wait for another player to connect (first player waits for second player)

GAMEPLAY:
---------

1. Once two players connect, the game begins automatically.

2. Controls:
   - Use W/S keys or Up/Down arrow keys to move your paddle
   - First player to 5 points wins

3. After game ends:
   - Both players choose "Yes" or "No" for rematch
   - If both choose "Yes", a new game starts immediately
   - If either chooses "No", connection closes

4. View leaderboard:
   - Open web browser to: http://<server-ip>/index.html
   - Or view raw data: http://<server-ip>/leaderboard.json

File Structure
==============

pongServer_auth.py    - Main game server with authentication
pongClient_auth.py    - Game client with authentication UI
auth_server.py        - Handles user authentication requests
user_db.py           - User database management with password hashing
token_manager.py     - Session token generation and verification
encryption.py        - Message encryption/decryption utilities
requirements.txt     - Python package dependencies
index.html          - Leaderboard webpage
users.json          - User database (auto-generated)
leaderboard.json    - Leaderboard data (auto-generated)



Known Bugs

No known bugs

Additional Notes
================

- The server must be started before any clients connect

