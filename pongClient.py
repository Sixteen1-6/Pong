# =================================================================================================
# Contributing Authors:     Shubhanshu Pokharel, Aaron Lin, Ayham Yousef
# Email Addresses:          spo283@uky.edu, ayli222@uky.edu, afyo223@uky.edu
# Date:                     11/17/2025
# Purpose:                  To implement the client and game logic with Play Again feature
# Misc:                     N/A
# =================================================================================================

import pygame
import tkinter as tk
import sys
import socket
import json
import os
import time

from assets.code.helperCode import *

def playGame(screenWidth:int, screenHeight:int, playerPaddle:str, client:socket.socket) -> None:
    """Main game loop with Play Again functionality."""
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
    playAgainDecision = None  # None = no decision, True = yes, False = no
    playAgainYesButton = pygame.Rect(screenWidth/2 - 150, screenHeight/2 + 60, 120, 50)
    playAgainNoButton = pygame.Rect(screenWidth/2 + 30, screenHeight/2 + 60, 120, 50)

    while True:
        # Wiping the screen
        screen.fill((0,0,0))

        # Getting keypress events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if not gameOver:  # Only allow movement during active game
                    if event.key == pygame.K_DOWN or event.key == pygame.K_s:
                        playerPaddleObj.moving = "down"
                    elif event.key == pygame.K_UP or event.key == pygame.K_w:
                        playerPaddleObj.moving = "up"
            elif event.type == pygame.KEYUP:
                playerPaddleObj.moving = ""
            elif event.type == pygame.MOUSEBUTTONDOWN and gameOver:
                # Handle Play Again button clicks
                mouse_pos = pygame.mouse.get_pos()
                if playAgainYesButton.collidepoint(mouse_pos) and playAgainDecision is None:
                    playAgainDecision = True
                    print("Player chose to play again")
                elif playAgainNoButton.collidepoint(mouse_pos) and playAgainDecision is None:
                    playAgainDecision = False
                    print("Player chose not to play again")

        # Update the player paddle's location on the screen (only during active game)
        if not gameOver:
            if playerPaddleObj.moving == "down":
                if playerPaddleObj.rect.bottomleft[1] < screenHeight-10:
                    playerPaddleObj.rect.y += playerPaddleObj.speed
            elif playerPaddleObj.moving == "up":
                if playerPaddleObj.rect.topleft[1] > 10:
                    playerPaddleObj.rect.y -= playerPaddleObj.speed

        # Game logic (only when game is active)
        if not gameOver and ballCounter >= 1:
            ball.updatePos()

            # If the ball makes it past the edge of the screen, update score, etc.
            if ball.rect.x > screenWidth:
                lScore += 1
                pointSound.play()
                ball.reset(nowGoing="left")
            elif ball.rect.x < 0:
                rScore += 1
                pointSound.play()
                ball.reset(nowGoing="right")
                
            # If the ball hits a paddle
            if ball.rect.colliderect(playerPaddleObj.rect):
                bounceSound.play()
                ball.hitPaddle(playerPaddleObj.rect.center[1])
            elif ball.rect.colliderect(opponentPaddleObj.rect):
                bounceSound.play()
                ball.hitPaddle(opponentPaddleObj.rect.center[1])
                
            # If the ball hits a wall
            if ball.rect.colliderect(topWall) or ball.rect.colliderect(bottomWall):
                bounceSound.play()
                ball.hitWall()
            
            pygame.draw.rect(screen, WHITE, ball)

        # Drawing the dotted line in the center
        for i in centerLine:
            pygame.draw.rect(screen, WHITE, i)
        
        # Drawing the paddles
        for paddle in [playerPaddleObj, opponentPaddleObj]:
            pygame.draw.rect(screen, WHITE, paddle)

        pygame.draw.rect(screen, WHITE, topWall)
        pygame.draw.rect(screen, WHITE, bottomWall)
        scoreRect = updateScore(lScore, rScore, screen, WHITE, scoreFont)

        # Display game over screen with Play Again option
        if gameOver:
            winText = "Player 1 Wins!" if lScore > rScore else "Player 2 Wins!"
            textSurface = winFont.render(winText, False, WHITE, (0,0,0))
            textRect = textSurface.get_rect()
            textRect.center = ((screenWidth/2), screenHeight/2 - 40)
            screen.blit(textSurface, textRect)
            
            # Display "Play Again?" text
            playAgainText = buttonFont.render("Play Again?", False, WHITE, (0,0,0))
            playAgainRect = playAgainText.get_rect()
            playAgainRect.center = ((screenWidth/2), screenHeight/2 + 10)
            screen.blit(playAgainText, playAgainRect)
            
            # Draw Yes button
            yesColor = WHITE if playAgainDecision != True else (0, 255, 0)
            pygame.draw.rect(screen, yesColor, playAgainYesButton, 2)
            yesText = buttonFont.render("YES", False, yesColor, (0,0,0))
            yesTextRect = yesText.get_rect()
            yesTextRect.center = playAgainYesButton.center
            screen.blit(yesText, yesTextRect)
            
            # Draw No button
            noColor = WHITE if playAgainDecision != False else (255, 0, 0)
            pygame.draw.rect(screen, noColor, playAgainNoButton, 2)
            noText = buttonFont.render("NO", False, noColor, (0,0,0))
            noTextRect = noText.get_rect()
            noTextRect.center = playAgainNoButton.center
            screen.blit(noText, noTextRect)
            
            # Show waiting message if player has decided
            if playAgainDecision is not None:
                waitingText = buttonFont.render("Waiting for opponent...", False, GRAY, (0,0,0))
                waitingRect = waitingText.get_rect()
                waitingRect.center = ((screenWidth/2), screenHeight/2 + 130)
                screen.blit(waitingText, waitingRect)

        pygame.display.update()
        clock.tick(60)

        # Server-Client Dialog
        data = {
            'sync': sync,
            'paddle': [playerPaddleObj.rect.x, playerPaddleObj.rect.y],
            'ball': [ball.rect.x, ball.rect.y],
            'score': [lScore, rScore],
        }
        
        # Add play again decision if game is over
        if gameOver and playAgainDecision is not None:
            data['play_again'] = playAgainDecision
        
        jsonData = json.dumps(data)
        client.send(jsonData.encode())

        # Receive game state from server
        try:
            received = client.recv(1024)
            if not received:
                print("Connection closed by server")
                break
                
            data = received.decode()
            jsonData = json.loads(data)

            # Check if game is over from server
            serverGameOver = jsonData.get('game_over', False)
            
            # Check if server says game is no longer over (rematch accepted)
            if gameOver and not serverGameOver:
                # Server reset the game - rematch accepted!
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
            
            # Check if game just ended
            if serverGameOver and not gameOver:
                gameOver = True
                print("Game Over!")
            
            # Handle play again responses when game is over
            if gameOver:
                opponentDecision = jsonData.get('play_again', None)
                
                # If opponent declined or we declined, end session
                if opponentDecision is False or playAgainDecision is False:
                    if playAgainDecision is False:
                        print("You declined rematch")
                    else:
                        print("Opponent declined rematch")
                    time.sleep(2)
                    break

            # Normal game state updates
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


def joinServer(name:str, ip:str, port:str, errorLabel:tk.Label, app:tk.Tk) -> None:
    """Connect to server and start the game."""
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((ip, int(port)))
        client.send(name.encode())

        errorLabel.config(text="Waiting for other player...")
        errorLabel.update()

        # Receive preliminary data from server
        received = client.recv(1024)
        data = received.decode()
        jsonData = json.loads(data)

        side = jsonData['side']
        screenHeight = jsonData['height']
        screenWidth = jsonData['width']

        # Close this window and start the game
        app.withdraw()
        playGame(screenWidth, screenHeight, side, client)
        app.quit()
        
    except Exception as e:
        errorLabel.config(text=f"Unable to connect to server: {str(e)}")
        errorLabel.update()


def startScreen() -> None:
    """Create the starting screen for the client."""
    app = tk.Tk()
    app.title("Server Info")

    script_directory = os.path.dirname(__file__)
    relative_image_path = os.path.join("assets", "images", "logo.png")
    image_path = os.path.join(script_directory, relative_image_path)

    image = tk.PhotoImage(file=image_path)

    titleLabel = tk.Label(image=image)
    titleLabel.grid(column=0, row=0, columnspan=2)

    nameLabel = tk.Label(text="Name:")
    nameLabel.grid(column=0, row=1, sticky="W", padx=8)

    nameEntry = tk.Entry(app)
    nameEntry.grid(column=1, row=1)

    ipLabel = tk.Label(text="Server IP:")
    ipLabel.grid(column=0, row=2, sticky="W", padx=8)

    ipEntry = tk.Entry(app)
    ipEntry.grid(column=1, row=2)

    portLabel = tk.Label(text="Server Port:")
    portLabel.grid(column=0, row=3, sticky="W", padx=8)

    portEntry = tk.Entry(app)
    portEntry.grid(column=1, row=3)

    errorLabel = tk.Label(text="")
    errorLabel.grid(column=0, row=5, columnspan=2)

    joinButton = tk.Button(text="Join", command=lambda: joinServer(nameEntry.get(), ipEntry.get(), portEntry.get(), errorLabel, app))
    joinButton.grid(column=0, row=4, columnspan=2)

    app.mainloop()


if __name__ == "__main__":
    startScreen()