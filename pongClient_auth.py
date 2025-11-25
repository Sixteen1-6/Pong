# =================================================================================================
# Contributing Authors:     Shubhanshu Pokharel, Aaron Lin, Ayham Yousef
# Email Addresses:          spo283@uky.edu, ayli222@uky.edu, afyo223@uky.edu
# Date:                     3 November 2025
# Purpose:                  Client with authentication and encryption
# Misc:                    
# =================================================================================================

import pygame
import tkinter as tk
import sys
import socket
import json
import os
import time

from assets.code.helperCode import *
from encryption import encrypt_message, decrypt_message

# Global variables for authenticated session
current_token = None
current_username = None

def authenticate(username: str, password: str, action: str, server_ip: str) -> tuple[bool, str, str]:
    """
    Authenticate with the auth server.
    Returns (success, message, token)
    """
    try:
        auth_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        auth_socket.connect((server_ip, 8081))
        
        request = {
            "action": action,
            "username": username,
            "password": password
        }
        
        encrypted_request = encrypt_message(json.dumps(request))
        auth_socket.send(encrypted_request)
        
        encrypted_response = auth_socket.recv(2048)
        response_str = decrypt_message(encrypted_response)
        response = json.loads(response_str)
        
        auth_socket.close()
        
        if response["success"]:
            token = response.get("token", "")
            return True, response["message"], token
        else:
            return False, response["message"], ""
            
    except Exception as e:
        return False, f"Connection error: {str(e)}", ""

def loginScreen(ip: str, port: str, errorLabel: tk.Label, loginWindow: tk.Tk, mainWindow: tk.Tk) -> None:
    """Show login screen."""
    def attemptLogin():
        username = usernameEntry.get()
        password = passwordEntry.get()
        
        if not username or not password:
            errorLabel.config(text="Please fill in all fields")
            return
        
        errorLabel.config(text="Authenticating...")
        errorLabel.update()
        
        success, message, token = authenticate(username, password, "login", ip)
        
        if success:
            global current_token, current_username
            current_token = token
            current_username = username
            loginWindow.destroy()
            
            # Join game directly instead of showing main window
            statusLabel = tk.Label(mainWindow, text="Connecting to game...", fg="green")
            joinServer(ip, port, statusLabel, mainWindow)
        else:
            errorLabel.config(text=message)
    
    # Login UI
    tk.Label(loginWindow, text="Login", font=("Arial", 16)).grid(row=0, column=0, columnspan=2, pady=10)
    
    tk.Label(loginWindow, text="Username:").grid(row=1, column=0, sticky="W", padx=8)
    usernameEntry = tk.Entry(loginWindow)
    usernameEntry.grid(row=1, column=1)
    
    tk.Label(loginWindow, text="Password:").grid(row=2, column=0, sticky="W", padx=8)
    passwordEntry = tk.Entry(loginWindow, show="*")
    passwordEntry.grid(row=2, column=1)
    
    loginButton = tk.Button(loginWindow, text="Login", command=attemptLogin)
    loginButton.grid(row=3, column=0, columnspan=2, pady=10)
    
    errorLabel.grid(row=4, column=0, columnspan=2)

def registerScreen(ip: str, errorLabel: tk.Label, registerWindow: tk.Tk, mainWindow: tk.Tk) -> None:
    """Show registration screen."""
    def attemptRegister():
        username = usernameEntry.get()
        password = passwordEntry.get()
        confirm = confirmEntry.get()
        
        if not username or not password or not confirm:
            errorLabel.config(text="Please fill in all fields")
            return
        
        if password != confirm:
            errorLabel.config(text="Passwords do not match")
            return
        
        errorLabel.config(text="Registering...")
        errorLabel.update()
        
        success, message, _ = authenticate(username, password, "register", ip)
        
        if success:
            errorLabel.config(text=f"{message} - Please login")
            time.sleep(2)
            registerWindow.destroy()
            showAuthChoice(mainWindow, ip)
        else:
            errorLabel.config(text=message)
    
    # Registration UI
    tk.Label(registerWindow, text="Register", font=("Arial", 16)).grid(row=0, column=0, columnspan=2, pady=10)
    
    tk.Label(registerWindow, text="Username:").grid(row=1, column=0, sticky="W", padx=8)
    usernameEntry = tk.Entry(registerWindow)
    usernameEntry.grid(row=1, column=1)
    
    tk.Label(registerWindow, text="Password:").grid(row=2, column=0, sticky="W", padx=8)
    passwordEntry = tk.Entry(registerWindow, show="*")
    passwordEntry.grid(row=2, column=1)
    
    tk.Label(registerWindow, text="Confirm:").grid(row=3, column=0, sticky="W", padx=8)
    confirmEntry = tk.Entry(registerWindow, show="*")
    confirmEntry.grid(row=3, column=1)
    
    registerButton = tk.Button(registerWindow, text="Register", command=attemptRegister)
    registerButton.grid(row=4, column=0, columnspan=2, pady=10)
    
    errorLabel.grid(row=5, column=0, columnspan=2)

def showAuthChoice(mainWindow: tk.Tk, ip: str, port: str) -> None:
    """Show choice between login and register."""
    authWindow = tk.Toplevel(mainWindow)
    authWindow.title("Authentication")
    
    errorLabel = tk.Label(authWindow, text="", fg="red")
    
    def showLogin():
        authWindow.withdraw()
        loginWindow = tk.Toplevel(mainWindow)
        loginWindow.title("Login")
        loginErrorLabel = tk.Label(loginWindow, text="", fg="red")
        loginScreen(ip, port, loginErrorLabel, loginWindow, mainWindow)  # Pass ip and port
    
    def showRegister():
        authWindow.withdraw()
        registerWindow = tk.Toplevel(mainWindow)
        registerWindow.title("Register")
        registerErrorLabel = tk.Label(registerWindow, text="", fg="red")
        registerScreen(ip, registerErrorLabel, registerWindow, mainWindow)
    
    tk.Label(authWindow, text="Welcome to Pong!", font=("Arial", 16)).pack(pady=20)
    
    tk.Button(authWindow, text="Login", width=20, command=showLogin).pack(pady=5)
    tk.Button(authWindow, text="Register", width=20, command=showRegister).pack(pady=5)
    
    errorLabel.pack(pady=10)


def playGame(screenWidth:int, screenHeight:int, playerPaddle:str, client:socket.socket) -> None:
    """Main game loop with encryption."""
    # Pygame inits
    pygame.mixer.pre_init(44100, -16, 2, 2048)
    pygame.init()

    # Constants
    WHITE = (255,255,255)
    GRAY = (128,128,128)
    clock = pygame.time.Clock()
    scoreFont = pygame.font.Font("./assets/fonts/pong-score.ttf", 32)
    winFont = pygame.font.Font("./assets/fonts/visitor.ttf", 48)
    buttonFont = pygame.font.Font("./assets/fonts/visitor.ttf", 32)
    pointSound = pygame.mixer.Sound("./assets/sounds/point.wav")
    bounceSound = pygame.mixer.Sound("./assets/sounds/bounce.wav")

    # Display objects
    screen = pygame.display.set_mode((screenWidth, screenHeight))
    topWall = pygame.Rect(-10,0,screenWidth+20, 10)
    bottomWall = pygame.Rect(-10, screenHeight-10, screenWidth+20, 10)
    centerLine = []
    for i in range(0, screenHeight, 10):
        centerLine.append(pygame.Rect((screenWidth/2)-5,i,5,5))

    # Paddle properties and init
    paddleHeight = 50
    paddleWidth = 10
    paddleStartPosY = (screenHeight/2)-(paddleHeight/2)
    leftPaddle = Paddle(pygame.Rect(10,paddleStartPosY, paddleWidth, paddleHeight))
    rightPaddle = Paddle(pygame.Rect(screenWidth-20, paddleStartPosY, paddleWidth, paddleHeight))

    ball = Ball(pygame.Rect(screenWidth/2, screenHeight/2, 5, 5), -5, 0)

    if playerPaddle == "left":
        opponentPaddleObj = rightPaddle
        playerPaddleObj = leftPaddle
    else:
        opponentPaddleObj = leftPaddle
        playerPaddleObj = rightPaddle

    lScore = 0
    rScore = 0
    sync = 0
    ballCounter = 0
    
    # Play Again state
    gameOver = False
    playAgainDecision = None
    playAgainYesButton = pygame.Rect(screenWidth/2 - 150, screenHeight/2 + 60, 120, 50)
    playAgainNoButton = pygame.Rect(screenWidth/2 + 30, screenHeight/2 + 60, 120, 50)

    while True:
        screen.fill((0,0,0))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if not gameOver:
                    if event.key == pygame.K_DOWN or event.key == pygame.K_s:
                        playerPaddleObj.moving = "down"
                    elif event.key == pygame.K_UP or event.key == pygame.K_w:
                        playerPaddleObj.moving = "up"
            elif event.type == pygame.KEYUP:
                playerPaddleObj.moving = ""
            elif event.type == pygame.MOUSEBUTTONDOWN and gameOver:
                mouse_pos = pygame.mouse.get_pos()
                if playAgainYesButton.collidepoint(mouse_pos) and playAgainDecision is None:
                    playAgainDecision = True
                    print("Player chose to play again")
                elif playAgainNoButton.collidepoint(mouse_pos) and playAgainDecision is None:
                    playAgainDecision = False
                    print("Player chose not to play again")

        if not gameOver:
            if playerPaddleObj.moving == "down":
                if playerPaddleObj.rect.bottomleft[1] < screenHeight-10:
                    playerPaddleObj.rect.y += playerPaddleObj.speed
            elif playerPaddleObj.moving == "up":
                if playerPaddleObj.rect.topleft[1] > 10:
                    playerPaddleObj.rect.y -= playerPaddleObj.speed

        if not gameOver and ballCounter >= 1:
            ball.updatePos()

            if ball.rect.x > screenWidth:
                lScore += 1
                pointSound.play()
                ball.reset(nowGoing="left")
            elif ball.rect.x < 0:
                rScore += 1
                pointSound.play()
                ball.reset(nowGoing="right")
                
            if ball.rect.colliderect(playerPaddleObj.rect):
                bounceSound.play()
                ball.hitPaddle(playerPaddleObj.rect.center[1])
            elif ball.rect.colliderect(opponentPaddleObj.rect):
                bounceSound.play()
                ball.hitPaddle(opponentPaddleObj.rect.center[1])
                
            if ball.rect.colliderect(topWall) or ball.rect.colliderect(bottomWall):
                bounceSound.play()
                ball.hitWall()
            
            pygame.draw.rect(screen, WHITE, ball)

        for i in centerLine:
            pygame.draw.rect(screen, WHITE, i)
        
        for paddle in [playerPaddleObj, opponentPaddleObj]:
            pygame.draw.rect(screen, WHITE, paddle)

        pygame.draw.rect(screen, WHITE, topWall)
        pygame.draw.rect(screen, WHITE, bottomWall)
        scoreRect = updateScore(lScore, rScore, screen, WHITE, scoreFont)

        if gameOver:
            winText = "Player 1 Wins!" if lScore > rScore else "Player 2 Wins!"
            textSurface = winFont.render(winText, False, WHITE, (0,0,0))
            textRect = textSurface.get_rect()
            textRect.center = ((screenWidth/2), screenHeight/2 - 40)
            screen.blit(textSurface, textRect)
            
            playAgainText = buttonFont.render("Play Again?", False, WHITE, (0,0,0))
            playAgainRect = playAgainText.get_rect()
            playAgainRect.center = ((screenWidth/2), screenHeight/2 + 10)
            screen.blit(playAgainText, playAgainRect)
            
            yesColor = WHITE if playAgainDecision != True else (0, 255, 0)
            pygame.draw.rect(screen, yesColor, playAgainYesButton, 2)
            yesText = buttonFont.render("YES", False, yesColor, (0,0,0))
            yesTextRect = yesText.get_rect()
            yesTextRect.center = playAgainYesButton.center
            screen.blit(yesText, yesTextRect)
            
            noColor = WHITE if playAgainDecision != False else (255, 0, 0)
            pygame.draw.rect(screen, noColor, playAgainNoButton, 2)
            noText = buttonFont.render("NO", False, noColor, (0,0,0))
            noTextRect = noText.get_rect()
            noTextRect.center = playAgainNoButton.center
            screen.blit(noText, noTextRect)
            
            if playAgainDecision is not None:
                waitingText = buttonFont.render("Waiting for opponent...", False, GRAY, (0,0,0))
                waitingRect = waitingText.get_rect()
                waitingRect.center = ((screenWidth/2), screenHeight/2 + 130)
                screen.blit(waitingText, waitingRect)

        pygame.display.update()
        clock.tick(60)

        # Server-Client Dialog with encryption
        data = {
            'sync': sync,
            'paddle': [playerPaddleObj.rect.x, playerPaddleObj.rect.y],
            'ball': [ball.rect.x, ball.rect.y],
            'score': [lScore, rScore],
        }
        
        if gameOver and playAgainDecision is not None:
            data['play_again'] = playAgainDecision
        
        jsonData = json.dumps(data)
        encrypted_data = encrypt_message(jsonData)
        client.send(encrypted_data)

        try:
            encrypted_received = client.recv(2048)
            if not encrypted_received:
                print("Connection closed by server")
                break
            
            received = decrypt_message(encrypted_received)
            jsonData = json.loads(received)

            serverGameOver = jsonData.get('game_over', False)
            
            if gameOver and not serverGameOver:
                print("Rematch accepted! Starting new game...")
                lScore = 0
                rScore = 0
                sync = 0
                ballCounter = 0
                gameOver = False
                playAgainDecision = None
                ball.reset(nowGoing="left")
                playerPaddleObj.rect.y = paddleStartPosY
                opponentPaddleObj.rect.y = paddleStartPosY
                continue
            
            if serverGameOver and not gameOver:
                gameOver = True
                print("Game Over!")
            
            if gameOver:
                opponentDecision = jsonData.get('play_again', None)
                
                if opponentDecision is False or playAgainDecision is False:
                    if playAgainDecision is False:
                        print("You declined rematch")
                    else:
                        print("Opponent declined rematch")
                    time.sleep(2)
                    break

            if not gameOver:
                if sync != jsonData['sync']:
                    if playerPaddle == "left":
                        playerPaddleObj.rect.x = jsonData['left'][0]
                        playerPaddleObj.rect.y = jsonData['left'][1]
                    else:
                        playerPaddleObj.rect.x = jsonData['right'][0]
                        playerPaddleObj.rect.y = jsonData['right'][1]

                ball.rect.x = jsonData['ball'][0]
                ball.rect.y = jsonData['ball'][1]

                lScore = jsonData['score'][0]
                rScore = jsonData['score'][1]

                if playerPaddle == "left":
                    opponentPaddleObj.rect.x = jsonData['right'][0]
                    opponentPaddleObj.rect.y = jsonData['right'][1]
                else:
                    opponentPaddleObj.rect.x = jsonData['left'][0]
                    opponentPaddleObj.rect.y = jsonData['left'][1]

                sync = jsonData['sync'] + 1

            if ballCounter < 1:
                time.sleep(1)
                ballCounter += 1
                
        except Exception as e:
            print(f"Error receiving data: {e}")
            break

    pygame.quit()


def joinServer(ip:str, port:str, errorLabel:tk.Label, app:tk.Tk) -> None:
    """Connect to server with token authentication."""
    global current_token, current_username
    
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((ip, int(port)))
        
        # Send encrypted token
        encrypted_token = encrypt_message(current_token)
        client.send(encrypted_token)
        
        # Receive acknowledgment
        encrypted_ack = client.recv(1024)
        ack = decrypt_message(encrypted_ack)
        
        if ack != "TOKEN_OK":
            errorLabel.config(text="Authentication failed")
            client.close()
            return

        errorLabel.config(text="Waiting for other player...")
        errorLabel.update()

        # Receive preliminary data (encrypted)
        encrypted_received = client.recv(2048)
        received = decrypt_message(encrypted_received)
        jsonData = json.loads(received)

        side = jsonData['side']
        screenHeight = jsonData['height']
        screenWidth = jsonData['width']

        app.withdraw()
        playGame(screenWidth, screenHeight, side, client)
        app.quit()
        
    except Exception as e:
        errorLabel.config(text=f"Unable to connect to server: {str(e)}")
        errorLabel.update()

def startScreen() -> None:
    """Create the starting screen with authentication."""
    app = tk.Tk()
    app.title("Server Info")

    script_directory = os.path.dirname(__file__)
    relative_image_path = os.path.join("assets", "images", "logo.png")
    image_path = os.path.join(script_directory, relative_image_path)

    image = tk.PhotoImage(file=image_path)

    titleLabel = tk.Label(app, image=image)
    titleLabel.grid(column=0, row=0, columnspan=2)

    ipLabel = tk.Label(app, text="Server IP:")
    ipLabel.grid(column=0, row=1, sticky="W", padx=8)

    ipEntry = tk.Entry(app)
    ipEntry.grid(column=1, row=1)

    portLabel = tk.Label(app, text="Server Port:")
    portLabel.grid(column=0, row=2, sticky="W", padx=8)

    portEntry = tk.Entry(app)
    portEntry.insert(0, "8080")
    portEntry.grid(column=1, row=2)

    errorLabel = tk.Label(app, text="", fg="red")
    errorLabel.grid(column=0, row=4, columnspan=2)

    
    def continueToAuth():
        server_ip = ipEntry.get()
        server_port = portEntry.get()
        if not server_ip:
            errorLabel.config(text="Please enter server IP")
            return
        
        # Hide this window and show auth
        app.withdraw()
        showAuthChoice(app, server_ip, server_port)  # Pass both IP and port

    continueButton = tk.Button(app, text="Continue to Login", command=continueToAuth)
    continueButton.grid(column=0, row=3, columnspan=2)

    app.mainloop()

if __name__ == "__main__":
    startScreen()