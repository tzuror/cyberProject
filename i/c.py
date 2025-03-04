import socket
import threading
import logging
from protocol import Protocol

# Server configuration
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 12345

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=r'C:\Users\ort\Documents\cyberProject\client.log',  # Log to a file
    filemode='a'  # Append mode
)

connected_room_code = None
username = None

lock = threading.Lock()
room_connected_event = threading.Event()
room_disconnected_event = threading.Event()
status_arrived_event = threading.Event()
chat_oppened_event = threading.Event()
chat_closed_event = threading.Event()
CONNECTION_TIMEOUT = 10  # Timeout in seconds
IN_CHAT = False
def connect_to_server():
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((SERVER_HOST, SERVER_PORT))
        logging.info("Connected to the server.")
        return client
    except Exception as e:
        logging.error(f"Failed to connect to the server: {e}")
        return None

def listen_for_messages(client):
    global connected_room_code
    while True:
        try:
            message = Protocol.from_str(client.recv(1024).decode('utf-8'))
            if message.command == "CHAT_MESSAGE":
                print(f"{message.sender}: {message.data['message']}")
            elif message.command == "USER_JOINED":
                print(f"{message.data['username']} joined the room.")
            elif message.command == "ROOM_CREATED":
                with lock:
                    connected_room_code = message.data["room_code"]
                logging.info(f"Room created with code: {connected_room_code}")
                print(f"Room created with code: {connected_room_code}")
                room_connected_event.set()  # Signal that the room is created
            elif message.command == "ROOM_JOINED":
                with lock:
                    connected_room_code = message.data["room_code"]
                logging.info(f"Joined room with code: {connected_room_code}")
                print(f"Joined room with code: {connected_room_code}")
                room_connected_event.set()  # Signal that the room is created
            elif message.command == "ROOM_NOT_FOUND":
                print("Room not found.")
                room_connected_event.set()
            elif message.command == "LEFT_ROOM":
                with lock:
                    connected_room_code = None
                print("You have left the room.")
                room_disconnected_event.set()
            elif message.command == "USER_LEFT":
                print(f"{message.data['username']} has left the room.")
            elif message.command == "ERROR":
                print(f"Error: {message.data['message']}")
                room_connected_event.set()
                room_disconnected_event.set()
            elif message.command == "ROOM_STATUS":
                print(f"Room status: {message.data['status']}")
                print(f"Host: {message.data['host']}")
                print(f"MEMBERS: \n{message.data['members']}")
                status_arrived_event.set()
            elif message.command == "ROOM_CLOSED":
                print("The room has been closed by the host.")
                with lock:
                    connected_room_code = None
                room_disconnected_event.set()
            elif message.command == "ENTERED_CHAT":
                print("You have entered the chat.")
                chat_oppened_event.set()
            elif message.command == "LEFT_CHAT":
                print("You have left the chat.")
                chat_closed_event.set()

        except Exception as e:
            logging.error(f"Error receiving message: {e}")
            break

def create_room(client):
    global username
    username = input("Enter your username: ")
    if not username:
        print("Username cannot be empty.")
        return
    client.send(Protocol("CREATE_ROOM", username, {}).to_str().encode('utf-8'))

def join_room(client, room_code):
    global username
    username = input("Enter your username: ")
    if not username:
        print("Username cannot be empty.")
        return
    if not room_code:
        print("Room code cannot be empty.")
        return
    client.send(Protocol("JOIN_ROOM", username, {"room_code": room_code}).to_str().encode('utf-8'))

def send_message(client, message):
    if connected_room_code:
        client.send(Protocol("SEND_CHAT_MESSAGE", username, {"message": message}).to_str().encode('utf-8'))
    else:
        print("You are not in a room.")

def leave_room(client):
    if connected_room_code:
        client.send(Protocol("LEAVE_ROOM", username, {}).to_str().encode('utf-8'))
        if not room_disconnected_event.wait(timeout=CONNECTION_TIMEOUT):
            print("Error: Server did not respond in time. Please check your connection or try again.")
            room_disconnected_event.clear()
        room_disconnected_event.clear()
        return True
    else:
        print("You are not in a room.")
        return False

def check_room_status(client):
    if connected_room_code:
        client.send(Protocol("ROOM_STATUS", username, {}).to_str().encode('utf-8'))
        if not status_arrived_event.wait(timeout=CONNECTION_TIMEOUT):
            print("Error: Server did not respond in time. Please check your connection or try again.")
            status_arrived_event.clear()
        status_arrived_event.clear()
        return True
    else:
        print("You are not in a room.")
        return False

def close_room(client):
    if connected_room_code:
        client.send(Protocol("CLOSE_ROOM", username, {}).to_str().encode('utf-8'))
        if not room_disconnected_event.wait(timeout=CONNECTION_TIMEOUT):
            print("Error: Server did not respond in time. Please check your connection or try again.")
            room_disconnected_event.clear()
        room_disconnected_event.clear()
    else:
        print("You are not in a room.")

def show_chat_menu(client):
    global IN_CHAT
    while connected_room_code:
        action = input("Enter action (chat/status/close/leave): ").strip().lower()
        if action == "chat":
            print("Enter message (or type 'exit' to leave chat):")
            client.send(Protocol("ENTER_CHAT", username, {}).to_str().encode('utf-8'))
            if not chat_oppened_event.wait(timeout=CONNECTION_TIMEOUT):
                print("Error: Server did not respond in time. Please check your connection or try again.")
                chat_oppened_event.clear()
                continue
            chat_oppened_event.clear()
            IN_CHAT = True
            while connected_room_code:
                message = input().strip()
                if message.lower() == 'exit':
                    client.send(Protocol("LEAVE_CHAT", username, {}).to_str().encode('utf-8'))
                    IN_CHAT = False
                    if not chat_closed_event.wait(timeout=CONNECTION_TIMEOUT):
                        print("Error: Server did not respond in time. Please check your connection or try again.")
                        chat_closed_event.clear()
                        continue
                    break
                elif message:
                    send_message(client, message)
        elif action == "status":
            check_room_status(client)
        elif action == "close":
            if close_room(client):
                break
        elif action == "leave":
            if leave_room(client):
                break
        else:
            print("Invalid action. Please enter 'chat', 'status', 'close', or 'leave'.")

def main():
    client = connect_to_server()
    if client:
        threading.Thread(target=listen_for_messages, args=(client,)).start()

        while True:
            global connected_room_code
            if connected_room_code is None:
                action = input("Enter action (create/join): ").strip().lower()
                if action == "create":
                    create_room(client)
                    # Wait for the room to be created with a timeout
                    if not room_connected_event.wait(timeout=CONNECTION_TIMEOUT):
                        print("Error: Server did not respond in time. Please check your connection or try again.")
                        room_connected_event.clear()  # Reset the event
                        continue  # Go back to the main menu
                    room_connected_event.clear()  # Reset the event
                elif action == "join":
                    room_code = input("Enter room code: ").strip()
                    if not room_code:
                        print("Room code cannot be empty.")
                        continue
                    join_room(client, room_code)
                    # Wait for the room to be joined with a timeout
                    if not room_connected_event.wait(timeout=CONNECTION_TIMEOUT):
                        print("Error: Server did not respond in time. Please check your connection or try again.")
                        room_connected_event.clear()  # Reset the event
                        continue  # Go back to the main menu
                    room_connected_event.clear()  # Reset the event
                else:
                    print("Invalid action. Please enter 'create' or 'join'.")
            else:
                show_chat_menu(client)

if __name__ == "__main__":
    main()  