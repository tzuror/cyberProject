import socket
import threading
import logging
import os
import sys
child_dir = os.path.dirname(__file__)
parent_dir = os.path.abspath(os.path.join(child_dir, '..'))
sys.path.append(parent_dir)
from protocol import Protocol
import tkinter as tk
from tkinter import scrolledtext
from server_objects import MEMBER, ROOM
import random

# Server configuration
HOST = '0.0.0.0'
PORT = 12345
BUFFER_SIZE = 100000 

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=r'C:\Users\ort\Documents\cyberProject\server.log',  # Log to a file
    filemode='a'  # Append mode
)
lock = threading.Lock()

# Store rooms and clients
rooms = {}  # type: dict[int, ROOM]
clients = set()

# Additional logger for chat messages
chat_logger = logging.getLogger('chat_logger')
chat_logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(r'C:\Users\ort\Documents\cyberProject\chat_messages.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
chat_logger.addHandler(file_handler)

# Additional logger for all traffic (requests & responses)
traffic_logger = logging.getLogger('traffic_logger')
traffic_logger.setLevel(logging.INFO)
traffic_handler = logging.FileHandler(r'C:\Users\ort\Documents\cyberProject\server_traffic.log')
traffic_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
traffic_logger.addHandler(traffic_handler)

def genarate_room_pwd():
    while True:
        password = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=7))
        if password not in rooms.keys():
            return password

def send(receiver, message):
    receiver.send(message)
    traffic_logger.info(f"SENT to {receiver.getpeername()}: {message.decode('utf-8')}")


def send_chat_message(room_code, message, sender="server", toSender=True):
    if room_code in rooms.keys():
        for member in rooms[room_code].get_chat_members():
            if sender == "server" or toSender or member != sender:
                member.send(message.to_str().encode('utf-8'))
                traffic_logger.info(f"SENT to {member.get_address()}: {message.to_str()}")
    else:
        logging.error(f"Room {room_code} not found.")


def broadcast_message(room_code, message):
    if room_code in rooms.keys():
        for member in rooms[room_code].get_members():
            member.send(message.to_str().encode('utf-8'))
            traffic_logger.info(f"SENT to {member.get_address()}: {message.to_str()}")
    else:
        logging.error(f"Room {room_code} not found.")


def handle_client(client_socket, client_address):
    logging.info(f"New connection from {client_address}")

    client = MEMBER(client_socket, client_address, None)
    while True:
        try:
            data = b""
            while True:
                part = client_socket.recv(BUFFER_SIZE)
                data += part
                if len(part) < BUFFER_SIZE:
                    break
            message = Protocol.from_str(data.decode('utf-8'))
            if not message:
                break
            traffic_logger.info(f"RECEIVED from {client_address}: {message.to_str()}")
            command = message.command
            if command == "DISCONNECT":
                break
            if command == "CREATE_ROOM":

                room_code = str(next(i for i in range(1, len(rooms) + 2) if str(i) not in rooms.keys()))
                room_pwd = genarate_room_pwd()
                client.set_name(message.sender["username"])
                client.set_email(message.sender["email"])
                client.set_room_code(room_code)
                room_code = room_code
                with lock:
                    rooms[room_code] = ROOM(room_code, client, "open", room_pwd)
                rooms[room_code].add_member(client)
                clients.add(client)
                send(client_socket, Protocol("ROOM_CREATED", "server", {"room_code": room_code, "room_pwd": room_pwd}).to_str().encode('utf-8'))
                logging.info(f"Room created with code: {room_code}")
            elif command == "JOIN_ROOM":
                room_code = message.data["room_code"]
                room_pwd = message.data["room_pwd"]
                client.set_name(message.sender["username"])#rooms[room_code].get_host() != None
                client.set_email(message.sender["email"])
                if room_code in rooms.keys() and rooms[room_code].get_status() == "open" and rooms[room_code].get_code() == str(room_code) and rooms[room_code].get_host() != None:
                    if room_pwd == rooms[room_code].get_pwd():
                        print("room found")
                        rooms[str(room_code)].add_member(client)
                        client.set_room_code(room_code)
                        clients.add(client)
                        send(client_socket, Protocol("ROOM_JOINED", "server", {"room_code": room_code, "room_pwd": room_pwd}).to_str().encode('utf-8'))
                        broadcast_message(room_code, Protocol("USER_JOINED", "server", {"username": message.sender['username']}))
                        logging.info(f"Client joined room: {room_code}")
                    else:
                        send(client_socket, Protocol("INCORRECT_PASSWORD", "server", {"message": "Incorrect room password."}).to_str().encode('utf-8'))
                else:
                    send(client_socket, Protocol("ROOM_NOT_FOUND", "server", {}).to_str().encode('utf-8'))
                    logging.error(f"Room not found or closed: {room_code}")
            elif command == "ENTER_CHAT":
                if client.get_room_code != None:
                    room_code = client.get_room_code()
                    if room_code in rooms.keys():
                        rooms[room_code].add_chat_member(client)
                        send(client_socket, Protocol("ENTERED_CHAT", "server", {}).to_str().encode('utf-8'))
                        send_chat_message(room_code, Protocol("CHAT_MESSAGE", "server", {"message": f"{message.sender['username']} has entered the chat."}))
                    else:
                        send(client_socket, Protocol("ERROR", "server", {"message": "Room not found."}).to_str().encode('utf-8'))
                else:
                    send(client_socket, Protocol("ERROR", "server", {"message": "You must be in a room to chat."}).to_str().encode('utf-8'))
            elif command == "LEAVE_CHAT":
                if client.get_room_code() != None:
                    room_code = client.get_room_code()
                    if room_code in rooms.keys():
                        rooms[room_code].remove_chat_member(client)
                        send(client_socket, Protocol("LEFT_CHAT", "server", {}).to_str().encode('utf-8'))
                        send_chat_message(room_code, Protocol("CHAT_MESSAGE", "server", {"message": f"{message.sender['username']} has left the chat."}))
                    else:
                        send(client_socket, Protocol("ERROR", "server", {"message": "Room not found."}).to_str().encode('utf-8'))
                else:
                    send(client_socket, Protocol("ERROR", "server", {"message": "You must be in a room to chat."}).to_str().encode('utf-8'))
            elif command == "SEND_CHAT_MESSAGE":
                room_code = client.get_room_code()
                if room_code != None:
                    if client in rooms[room_code].get_chat_members():
                        room_code = client.get_room_code()
                        if len(rooms[room_code].get_chat_members()) > 1:
                            send_chat_message(room_code, Protocol("CHAT_MESSAGE", message.sender["username"], {"message": message.data["message"]}), client)
                            chat_logger.info(f"{message.sender}: {message.data['message']}")
                        else:
                            send(client_socket, Protocol("ERROR", "server", {"message": "Both users must be in the room to chat."}).to_str().encode('utf-8'))
                    else:
                        send(client_socket, Protocol("ERROR", "server", {"message": "You must be in the chat to send messages."}).to_str().encode('utf-8'))
                else:
                    send(client_socket, Protocol("ERROR", "server", {"message": "You must be in a room to chat."}).to_str().encode('utf-8'))
            elif command == "LEAVE_ROOM":
                room_code = client.get_room_code()
                if room_code in rooms.keys():
                    print(12)
                    if rooms[room_code].get_host().get_socket() == client_socket:
                        print(22)
                        rooms[room_code].set_host(None)
                        rooms[room_code].remove_member(client)
                        client.set_room_code(None)
                        broadcast_message(room_code, Protocol("USER_LEFT", "server", {"username": message.sender}))
                        if len(rooms[room_code].get_members()) > 0:
                            print(32)
                            new_host = list(rooms[room_code].get_members())[0]
                            rooms[room_code].set_host(new_host)
                            broadcast_message(room_code, Protocol("NEW_HOST", "server", {"username": str(new_host)}))
                    elif client in rooms[room_code].get_members():
                        print(42)
                        rooms[room_code].remove_member(client)
                        client.set_room_code(None)
                        broadcast_message(room_code, Protocol("USER_LEFT", "server", {"username": message.sender}))
                    if rooms[room_code].get_host() is None and len(rooms[room_code].get_members()) == 0:
                        print(52)
                        del rooms[room_code]
                        rooms.pop(room_code, None)
                    send(client_socket, Protocol("LEFT_ROOM", "server", {}).to_str().encode('utf-8'))
                    logging.info(f"Client {client_address} left room: {room_code}")
            elif command == "ROOM_STATUS":
                room_code = client.get_room_code()
                if room_code in rooms.keys():
                    host_username = str(rooms[room_code].get_host()) if rooms[room_code].get_host() else None
                    room_members = ",\n".join(list(map(str, rooms[room_code].get_members())))
                    status = rooms[room_code].get_status()
                    send(client_socket, Protocol("ROOM_STATUS", "server", {
                        "status": status,
                        "host": host_username,
                        "members": room_members
                    }).to_str().encode('utf-8'))
                else:
                    send(client_socket, Protocol("ERROR", "server", {"message": "Room not found."}).to_str().encode('utf-8'))
            elif command == "CLOSE_ROOM":
                room_code = client.get_room_code()
                if room_code in rooms.keys() and rooms[room_code].get_host() == client:
                    
                    broadcast_message(room_code, Protocol("ROOM_CLOSED", "server", {}))
                    rooms[room_code].set_status("closed")
                    for member in rooms[room_code].get_members():
                        member.set_room_code(None)
                    logging.info(f"Room {room_code} closed by host.")
                    del rooms[room_code]
                else:
                    send(client_socket, Protocol("ERROR", "server", {"message": "Only the host can close the room."}).to_str().encode('utf-8'))
            elif command == "START_SCREEN_SHARE":
                room_code = client.get_room_code()
                if room_code in rooms.keys():
                    if(rooms[room_code].get_sharing() == None):
                        rooms[room_code].set_sharing(client)
                        broadcast_message(room_code, Protocol("USER_STARTED_SCREEN_SHARE", "server", {"username": message.sender["username"]}))
                        logging.info(f"{message.sender['username']} started screen sharing in room {room_code}")
                    else:
                        send(client_socket, Protocol("ERROR", "server", {"message": "Screen sharing is already in progress."}).to_str().encode('utf-8'))
                        logging.error(f"{message.sender['username']} tried to start screen sharing in room {room_code} but screen sharing is already in progress.")
                else:
                    send(client_socket, Protocol("ERROR", "server", {"message": "Room not found."}).to_str().encode('utf-8'))
                    logging.error(f"{message.sender['username']} tried to start screen sharing in room {room_code} but the room was not found.")
            elif command == "STOP_SCREEN_SHARE":
                room_code = client.get_room_code()
                if room_code in rooms.keys():
                    if rooms[room_code].get_sharing() == client:
                        rooms[room_code].set_sharing(None)
                        broadcast_message(room_code, Protocol("USER_STOPPED_SCREEN_SHARE", "server", {"username": message.sender["username"]}))
                        logging.info(f"{message.sender['username']} stopped screen sharing in room {room_code}")
                    else:
                        send(client_socket, Protocol("ERROR", "server", {"message": "You are not sharing your screen."}).to_str().encode('utf-8'))
                        logging.error(f"{message.sender['username']} tried to stop screen sharing in room {room_code} but they are not sharing their screen.")
                else:
                    send(client_socket, Protocol("ERROR", "server", {"message": "Room not found."}).to_str().encode('utf-8'))
                    logging.error(f"{message.sender['username']} tried to stop screen sharing in room {room_code} but the room was not found.")
            elif command == "SCREEN_DATA":
                print("1")
                room_code = client.get_room_code()
                if room_code in rooms.keys():
                    print("2")
                    if rooms[room_code].get_sharing() == client:
                        print("3")

                    # Broadcast the screen data to all clients in the room
                        for member in rooms[room_code].get_members():
                            print("4")
                            with lock:
                                member.send(Protocol("SCREEN_DATA", message.sender["username"], {"image_data": message.data["image_data"]}).to_str().encode('utf-8'))
                                traffic_logger.info(f"SENT to {member.get_address()}: SCREEN_DATA")
                    else:
                        send(client_socket, Protocol("ERROR", "server", {"message": "You are not sharing your screen."}).to_str().encode('utf-8'))
                        logging.error(f"{message.sender['username']} tried to send screen data in room {room_code} but they are not sharing their screen.")
                else:
                    send(client_socket, Protocol("ERROR", "server", {"message": "Room not found."}).to_str().encode('utf-8'))
                    logging.error(f"{message.sender['username']} tried to send screen data in room {room_code} but the room was not found.")
            else:
                send(client_socket, Protocol("ERROR", "server", {"message": "Invalid command."}).to_str().encode('utf-8'))
                logging.error(f"Invalid command: {command}")
        except Exception as e:
            logging.error(f"Error handling client: {e}")
            break

    try:        
        room_code = client.get_room_code()
        if client in clients:
            if room_code in rooms.keys() and room_code != None:
                if rooms[room_code].get_host() == client:
                    rooms[room_code].set_host(None)
                    rooms[room_code].remove_member(client)
                    broadcast_message(room_code, Protocol("USER_LEFT", "server", {"username": message.sender}))
                elif client in rooms[room_code].get_members():
                    rooms[room_code].remove_member(client)
                    broadcast_message(room_code, Protocol("USER_LEFT", "server", {"username": message.sender}))
                if rooms[room_code].get_host() is None and len(rooms[room_code].get_members()) == 0:
                    print("room deleted")
                    del rooms[room_code]
                    rooms.pop(room_code, None)
                elif rooms[room_code].get_host() is None and len(rooms[room_code].get_members()) > 0:
                    new_host = list(rooms[room_code].get_members())[0]
                    rooms[room_code].set_host(new_host)
                    broadcast_message(room_code, Protocol("NEW_HOST", "server", {"username": str(new_host)}).to_str().encode('utf-8'))
            clients.remove(client)
            del client
        logging.info(f"Client {client_address} disconnected")
    except Exception as e:
        logging.error(f"Error handling client disconnection: {e}")
    finally:
        client_socket.close()
        


def start_server():
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((HOST, PORT))
        server.listen(5)
        logging.info(f"Server listening on {HOST}:{PORT}")

        while True:
            client_socket, client_address = server.accept()
            threading.Thread(target=handle_client, args=(client_socket, client_address)).start()
    except Exception as e:
        logging.error(f"Server error: {e}")
    finally:
        server.close()
        logging.info("Server closed.")


class ServerControlGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Server Control")
        self.root.geometry("800x600")

        # Connected Clients
        self.clients_label = tk.Label(root, text="Connected Clients", font=("Arial", 14))
        self.clients_label.pack(pady=10)
        self.clients_text = scrolledtext.ScrolledText(root, state='disabled', height=10)
        self.clients_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Open Rooms
        self.rooms_label = tk.Label(root, text="Open Rooms", font=("Arial", 14))
        self.rooms_label.pack(pady=10)
        self.rooms_text = scrolledtext.ScrolledText(root, state='disabled', height=10)
        self.rooms_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Active Chats
        self.chats_label = tk.Label(root, text="Active Chats", font=("Arial", 14))
        self.chats_label.pack(pady=10)
        self.chats_text = scrolledtext.ScrolledText(root, state='disabled', height=10)
        self.chats_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Start the server in a separate thread
        threading.Thread(target=start_server, daemon=True).start()

        # Update the GUI periodically
        self.update_gui()

    def update_gui(self):
        """Update the GUI with the latest information about clients, rooms, and chats."""
        # Clear the text areas
        self.clients_text.config(state='normal')
        self.clients_text.delete(1.0, tk.END)
        self.rooms_text.config(state='normal')
        self.rooms_text.delete(1.0, tk.END)
        self.chats_text.config(state='normal')
        self.chats_text.delete(1.0, tk.END)

        # Display connected clients
        self.clients_text.insert(tk.END, "Connected Clients:\n")
        for client in clients:
            self.clients_text.insert(tk.END, f"{client}\n")

        # Display open rooms
        self.rooms_text.insert(tk.END, "Open Rooms:\n")
        for room_code, room in rooms.items():
            self.rooms_text.insert(tk.END, f"Room Code: {room_code}\n")
            self.rooms_text.insert(tk.END, f"Password: {room.get_pwd()}\n")
            self.rooms_text.insert(tk.END, f"Status: {room.get_status()}\n")
            self.rooms_text.insert(tk.END, f"Host: {room.get_host()}\n")
            self.rooms_text.insert(tk.END, f"Members: {', '.join(map(str, room.get_members()))}\n")
            self.rooms_text.insert(tk.END, "\n")

        # Display active chats
        self.chats_text.insert(tk.END, "Active Chats:\n")
        for room_code, room in rooms.items():
            if room.get_chat_members():
                self.chats_text.insert(tk.END, f"Room Code: {room_code}\n")
                self.chats_text.insert(tk.END, f"Members in Chat: {', '.join(map(str, room.get_chat_members()))}\n")
                self.chats_text.insert(tk.END, "\n")

        # Disable editing
        self.clients_text.config(state='disabled')
        self.rooms_text.config(state='disabled')
        self.chats_text.config(state='disabled')

        # Schedule the next update
        self.root.after(1000, self.update_gui)


if __name__ == "__main__":
    

    # Initialize and run the GUI
    root = tk.Tk()
    gui = ServerControlGUI(root)
    root.mainloop()
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()