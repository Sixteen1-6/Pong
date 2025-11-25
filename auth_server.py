# =================================================================================================
# Contributing Authors:     Shubhanshu Pokharel, Aaron Lin, Ayham Yousef
# Email Addresses:          spo283@uky.edu, ayli222@uky.edu, afyo223@uky.edu
# Date:                     11/25/2025
# Purpose:                  Authentication server for login/registration with encrypted communication
# Misc:                     Runs on port 8081, handles multiple clients using threading
# =================================================================================================


import socket
import json
import threading
from user_db import register_user, verify_user
from token_manager import generate_token
from encryption import encrypt_message, decrypt_message

AUTH_PORT = 8081


# Author:       Shubhanshu Pokharel, Aaron Lin, Ayham Yousef
# Purpose:      Handle authentication requests from clients (login/registration)
# Pre:          client_socket (socket.socket) - connected client socket, 
#               client_address - client's address tuple
# Post:         Processes authentication request, sends encrypted response, closes socket
def handle_auth_client(client_socket: socket.socket, client_address):
    """Handle authentication requests from clients."""
    try:
        # Receive encrypted authentication request
        encrypted_data = client_socket.recv(2048)
        data = decrypt_message(encrypted_data)
        request = json.loads(data)
        
        action = request.get("action")
        username = request.get("username")
        password = request.get("password")
        
        if action == "register":
            success, message = register_user(username, password)
            response = {
                "success": success,
                "message": message
            }
        elif action == "login":
            success, message = verify_user(username, password)
            if success:
                token = generate_token(username)
                response = {
                    "success": True,
                    "message": message,
                    "token": token,
                    "username": username
                }
            else:
                response = {
                    "success": False,
                    "message": message
                }
        else:
            response = {
                "success": False,
                "message": "Invalid action"
            }
        
        # Send encrypted response
        encrypted_response = encrypt_message(json.dumps(response))
        client_socket.send(encrypted_response)
        
    except Exception as e:
        print(f"Auth error: {e}")
        error_response = encrypt_message(json.dumps({
            "success": False,
            "message": "Authentication error"
        }))
        try:
            client_socket.send(error_response)
        except:
            pass
    finally:
        client_socket.close()


# Author:       Shubhanshu Pokharel, Aaron Lin, Ayham Yousef
# Purpose:      Start and run the authentication server
# Pre:          AUTH_PORT available, required modules imported
# Post:         Server listening on AUTH_PORT, spawns threads for each client connection
def start_auth_server():
    """Start the authentication server."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", AUTH_PORT))
    server.listen(5)
    print(f"Authentication server listening on port {AUTH_PORT}")
    
    while True:
        client_socket, client_address = server.accept()
        thread = threading.Thread(
            target=handle_auth_client,
            args=(client_socket, client_address),
            daemon=True
        )
        thread.start()

if __name__ == "__main__":
    start_auth_server()