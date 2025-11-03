# =================================================================================================
# Contributing Authors:	    Shubhanshu Pokharel, Aaron Lin, Ayham Yousef
# Email Addresses:          <spo283@uky.edu>, <ayli222@uky.edu> , <afyo223@uky.edu>
# Date:                     <3 November 2025>
# Purpose:                  <Client Side for multiplayer Pong Game with Play Again and Cryptography>
# Misc:                     <Not Required.  Anything else you might want to include>
# =================================================================================================

import pygame
import tkinter as tk
import sys
import socket

from assets.code.helperCode import *
import time
import ssl # socket wrapper for encryption 
import hashlib # for hashing SHA256 Passwords
import json # for serializing data to send over socket




# This is the main game loop.  For the most part, you will not need to modify this.  The sections
# where you should add to the code are marked.  Feel free to change any part of this project
# to suit your needs.
def playGame(screenWidth:int, screenHeight:int, playerPaddle:str, client:socket.socket) -> None:
    
    # Pygame inits
    pygame.mixer.pre_init(44100, -16, 2, 2048)
    pygame.init()

    # Constants
    WHITE = (255,255,255)
    clock = pygame.time.Clock()
    scoreFont = pygame.font.Font("./assets/fonts/pong-score.ttf", 32)
    winFont = pygame.font.Font("./assets/fonts/visitor.ttf", 48)
    pointSound = pygame.mixer.Sound("./assets/sounds/point.wav")
    bounceSound = pygame.mixer.Sound("./assets/sounds/bounce.wav")

    # Display objects
    screen = pygame.display.set_mode((screenWidth, screenHeight))
    winMessage = pygame.Rect(0,0,0,0)
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
    gameOver = False # for play again feature
    playAgainSent = False

    while True:
        # Wiping the screen
        screen.fill((0,0,0))

        # Getting keypress events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                #send quit message to server here
                try: 
                    quitMessage = {'action':'quit'} # construct quit message as dictionary
                    client.send(json.dumps(quitMessage).encode('utf-8'))
                except Exception:
                    pass
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DOWN:
                    playerPaddleObj.moving = "down"

                elif event.key == pygame.K_UP:
                    playerPaddleObj.moving = "up"
                # Handle play again keypress
                elif event.key == pygame.K_SPACE and gameOver and not playAgainSent:
                    playAgainMessage = {'action':'play_again', 'response': 'yes'} # construct play again message as dictionary
                    client.send(json.dumps(playAgainMessage).encode('utf-8'))
                    playAgainSent = True
                elif event.key == pygame.K_n and gameOver and not playAgainSent:
                    playAgainMessage = {'action':'play_again', 'response': 'no'} # construct play again message as dictionary
                    client.send(json.dumps(playAgainMessage).encode('utf-8'))
                    playAgainSent = True

            elif event.type == pygame.KEYUP:
                playerPaddleObj.moving = ""

        # =========================================================================================
        # Your code here to send an update to the server on your paddle's information,
        # where the ball is and the current score.
        # Feel free to change when the score is updated to suit your needs/requirements
        if not gameOver:
            clientMessage = {
                'action': 'update',
                'sync': sync,
                'paddle_x': playerPaddleObj.rect.x,
                'paddle_y': playerPaddleObj.rect.y,
                'ball_x': ball.rect.x,
                'ball_y': ball.rect.y,
                'lScore': lScore,
                'rScore': rScore,
                'playerSide': playerPaddle
            }
            # send the message as a JSON string
            jsonMessage = json.dumps(clientMessage)
            client.send(jsonMessage.encode('utf-8'))
            #Receive server update
            recievedData = client.recv(1024).decode('utf-8') # buffer size of 1024 byte
            serverUpdate = json.loads(recievedData) # parse JSON string to dictionary

            #check if Game should restart
            if serverUpdate.get('action') == 'restart':
                gameOver = False
                playAgainSent = False
                lScore = 0
                rScore = 0
                ball.reset(nowGoing="left")
                playerPaddleObj.rect.y = paddleStartPosY
                opponentPaddleObj.rect.y = paddleStartPosY
                continue # skip rest of loop to avoid updating positions before restart
            #update Game state
            opponentPaddleObj.rect.x = serverUpdate['opponentX']
            opponentPaddleObj.rect.y = serverUpdate['opponentY']
            ball.rect.x = serverUpdate['ballX']
            ball.rect.y = serverUpdate['ballY']
            lScore = serverUpdate['lScore']
            rScore = serverUpdate['rScore']

            sync= serverUpdate['sync']
        else: # Game is over
            try:
                client.settimeout(0.1) # set timeout to avoid blocking indefinitely
                recievedData = client.recv(1024).decode('utf-8')
                if recievedData:
                    serverUpdate = json.loads(recievedData)
                    if serverUpdate.get('action') == 'restart':
                        gameOver = False
                        playAgainSent = False
                        lScore = 0
                        rScore = 0
                        ball.reset(nowGoing="left")
                        playerPaddleObj.rect.y = paddleStartPosY
                        opponentPaddleObj.rect.y = paddleStartPosY
                    elif serverUpdate.get('action') == 'endGame':
                        
                        pygame.quit()
                        sys.exit()       
        
        # =========================================================================================

        # Update the player paddle and opponent paddle's location on the screen
        for paddle in [playerPaddleObj, opponentPaddleObj]:
            if paddle.moving == "down":
                if paddle.rect.bottomleft[1] < screenHeight-10:
                    paddle.rect.y += paddle.speed
            elif paddle.moving == "up":
                if paddle.rect.topleft[1] > 10:
                    paddle.rect.y -= paddle.speed

        # If the game is over, display the win message
        if lScore > 4 or rScore > 4:
            winText = "Player 1 Wins! " if lScore > 4 else "Player 2 Wins! "
            textSurface = winFont.render(winText, False, WHITE, (0,0,0))
            textRect = textSurface.get_rect()
            textRect.center = ((screenWidth/2), screenHeight/2)
            winMessage = screen.blit(textSurface, textRect)
        else:

            # ==== Ball Logic =====================================================================
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
            # ==== End Ball Logic =================================================================

        # Drawing the dotted line in the center
        for i in centerLine:
            pygame.draw.rect(screen, WHITE, i)
        
        # Drawing the player's new location
        for paddle in [playerPaddleObj, opponentPaddleObj]:
            pygame.draw.rect(screen, WHITE, paddle)

        pygame.draw.rect(screen, WHITE, topWall)
        pygame.draw.rect(screen, WHITE, bottomWall)
        scoreRect = updateScore(lScore, rScore, screen, WHITE, scoreFont)
        pygame.display.update([topWall, bottomWall, ball, leftPaddle, rightPaddle, scoreRect, winMessage])
        clock.tick(60)
        
        # This number should be synchronized between you and your opponent.  If your number is larger
        # then you are ahead of them in time, if theirs is larger, they are ahead of you, and you need to
        # catch up (use their info)
        sync += 1
        # =========================================================================================
        # Send your server update here at the end of the game loop to sync your game with your
        # opponent's game

        # =========================================================================================




# This is where you will connect to the server to get the info required to call the game loop.  Mainly
# the screen width, height and player paddle (either "left" or "right")
# If you want to hard code the screen's dimensions into the code, that's fine, but you will need to know
# which client is which
def joinServer(ip:str, port:str, errorLabel:tk.Label, app:tk.Tk) -> None:
    # Purpose:      This method is fired when the join button is clicked
    # Arguments:
    # ip            A string holding the IP address of the server
    # port          A string holding the port the server is using
    # errorLabel    A tk label widget, modify it's text to display messages to the user (example below)
    # app           The tk window object, needed to kill the window
    
    # Create a socket and connect to the server
    # You don't have to use SOCK_STREAM, use what you think is best
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Get the required information from your server (screen width, height & player paddle, "left or "right)


    # If you have messages you'd like to show the user use the errorLabel widget like so
    errorLabel.config(text=f"Some update text. You input: IP: {ip}, Port: {port}")
    # You may or may not need to call this, depending on how many times you update the label
    errorLabel.update()     

    # Close this window and start the game with the info passed to you from the server
    #app.withdraw()     # Hides the window (we'll kill it later)
    #playGame(screenWidth, screenHeight, ("left"|"right"), client)  # User will be either left or right paddle
    #app.quit()         # Kills the window


# This displays the opening screen, you don't need to edit this (but may if you like)
def startScreen():
    app = tk.Tk()
    app.title("Server Info")

    image = tk.PhotoImage(file="./assets/images/logo.png")

    titleLabel = tk.Label(image=image)
    titleLabel.grid(column=0, row=0, columnspan=2)

    ipLabel = tk.Label(text="Server IP:")
    ipLabel.grid(column=0, row=1, sticky="W", padx=8)

    ipEntry = tk.Entry(app)
    ipEntry.grid(column=1, row=1)

    portLabel = tk.Label(text="Server Port:")
    portLabel.grid(column=0, row=2, sticky="W", padx=8)

    portEntry = tk.Entry(app)
    portEntry.grid(column=1, row=2)

    errorLabel = tk.Label(text="")
    errorLabel.grid(column=0, row=4, columnspan=2)

    joinButton = tk.Button(text="Join", command=lambda: joinServer(ipEntry.get(), portEntry.get(), errorLabel, app))
    joinButton.grid(column=0, row=3, columnspan=2)

    app.mainloop()

if __name__ == "__main__":
    #startScreen()
    
    # Uncomment the line below if you want to play the game without a server to see how it should work
    # the startScreen() function should call playGame with the arguments given to it by the server this is
    # here for demo purposes only
    playGame(640, 480,"left",socket.socket(socket.AF_INET, socket.SOCK_STREAM))