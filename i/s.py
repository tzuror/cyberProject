import socket
import threading
import logging
from protocol import Protocol

# Server configuration
HOST = '0.0.0.0'
PORT = 12345

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=r'C:\Users\ort\Documents\cyberProject\server.log',  # Log to a file
    filemode='a'  # Append mode
)
lock = threading.Lock()

class MEMBER:
    def __init__(self, socket, address, name, room_code = None):
        self.socket = socket
        self.address = address
        self.name = name
        self.room_code = room_code
    def get_room_code(self):
        return self.room_code
    def get_socket(self):
        return self.socket
    def get_address(self):
        return self.address
    def get_name(self):
        return self.name
    def set_name(self, name):
        self.name = name
    def set_room_code(self, room_code):
        self.room_code = room_code
    def send(self, data):
        self.socket.send(data)
    def __str__(self):
        # get the address of the client the name and the port

        return f"{self.name} - {self.socket.getpeername()}"
    


        
class ROOM:
    def __init__(self, code, host: MEMBER, status: str):
        self.__ROOMCODE = code
        self.MEMBERS = set()
        self.CHAT_MEMBERS = set()
        self.__host = host
        self.__status = status
    def add_member(self, member: MEMBER):
        self.MEMBERS.add(member)
    def remove_member(self, member: MEMBER):
        self.MEMBERS.remove(member)
    def get_members(self):
        return self.MEMBERS
    def get_host(self) -> MEMBER:
        return self.__host
    def set_host(self, host: MEMBER):
        self.__host = host
    def get_status(self):
        return self.__status
    def set_status(self, status):
        self.__status = status
    def get_code(self):
        return self.__ROOMCODE
    def add_chat_member(self, member: MEMBER):
        self.CHAT_MEMBERS.add(member)
    def remove_chat_member(self, member: MEMBER):
        self.CHAT_MEMBERS.remove(member)
    def get_chat_members(self):
        return self.CHAT_MEMBERS
    

# Store rooms and clients
"rooms = {int: ROOM}"
rooms = {}  # type: dict[int, ROOM]
clients = set()

# Additional logger for chat messages
chat_logger = logging.getLogger('chat_logger')
chat_logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('chat_messages.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
chat_logger.addHandler(file_handler)

def send_chat_message(room_code, message, sender = "server", toSender = False):
    if room_code in rooms.keys():
        for member in rooms[room_code].get_chat_members():
            if sender == "server" or toSender or member != sender:
                member.send(message.to_str().encode('utf-8'))
    else:
        logging.error(f"Room {room_code} not found.")
        
def broadcast_message(room_code, message):
    if room_code in rooms.keys():
        for member in rooms[room_code].get_members():
            member.send(message.to_str().encode('utf-8'))
    else:
        logging.error(f"Room {room_code} not found.")

def handle_client(client_socket, client_address):
    logging.info(f"New connection from {client_address}")

    client = MEMBER(client_socket, client_address, None)
    while True:
        try:
            message = Protocol.from_str(client_socket.recv(1024).decode('utf-8'))
            if not message:
                break
            command = message.command
            if command == "DISCONNECT":
                break
            if command == "CREATE_ROOM":
                room_code = str(len(rooms) + 1)
                client.set_name(message.sender)
                client.set_room_code(room_code)
                room_code = room_code
                with lock:
                    rooms[room_code] = ROOM(room_code, client, "open")
                rooms[room_code].add_member(client)
                clients.add(client)
                client_socket.send(Protocol("ROOM_CREATED", "server", {"room_code": room_code}).to_str().encode('utf-8'))
                logging.info(f"Room created with code: {room_code}")
                """rooms[room_code] = {"host": client_socket, "guest": None, "status": "open"}
                clients[client_socket] = room_code
                client_socket.send(Protocol("ROOM_CREATED", "server", {"room_code": room_code}).to_str().encode('utf-8'))
                logging.info(f"Room created with code: {room_code}")"""
            elif command == "JOIN_ROOM":
                room_code = message.data["room_code"]
                print(room_code)
                client.set_name(message.sender)
                print(f"{room_code in rooms.keys()} and {rooms[room_code].get_status() == 'open'} and {rooms[room_code].get_code() == str(room_code)} and {rooms[room_code].get_host() != None}")
                if room_code in rooms.keys() and rooms[room_code].get_status() == "open" and rooms[room_code].get_code() == str(room_code) and rooms[room_code].get_host() != None:
                    print("room found")
                    rooms[str(room_code)].add_member(client)
                    client.set_room_code(room_code)
                    clients.add(client)
                    client_socket.send(Protocol("ROOM_JOINED", "server", {"room_code": room_code}).to_str().encode('utf-8'))
                    """rooms[room_code]["guest"] = client_socket
                    clients[client_socket] = room_code
                    client_socket.send(Protocol("ROOM_JOINED", "server", {"room_code": room_code}).to_str().encode('utf-8'))"""
                    broadcast_message(room_code, Protocol("USER_JOINED", "server", {"username": message.sender}))
                    logging.info(f"Client joined room: {room_code}")
                else:
                    client_socket.send(Protocol("ROOM_NOT_FOUND", "server", {}).to_str().encode('utf-8'))
                    logging.error(f"Room not found or closed: {room_code}")
            elif command == "ENTER_CHAT":
                if client.get_room_code != None:
                    room_code = client.get_room_code()
                    if room_code in rooms.keys():
                        rooms[room_code].add_chat_member(client)
                        client_socket.send(Protocol("ENTERED_CHAT", "server", {}).to_str().encode('utf-8'))
                        send_chat_message(room_code, Protocol("CHAT_MESSAGE", "server", {"message": f"{message.sender} has entered the chat."}))
                    else:
                        client_socket.send(Protocol("ERROR", "server", {"message": "Room not found."}).to_str().encode('utf-8'))
                else:
                    client_socket.send(Protocol("ERROR", "server", {"message": "You must be in a room to chat."}).to_str().encode('utf-8'))
            elif command == "LEAVE_CHAT":
                if client.get_room_code() != None:
                    room_code = client.get_room_code()
                    if room_code in rooms.keys():
                        rooms[room_code].remove_chat_member(client)

                        client_socket.send(Protocol("LEFT_CHAT", "server", {}).to_str().encode('utf-8'))
                        send_chat_message(room_code, Protocol("CHAT_MESSAGE", "server", {"message": f"{message.sender} has left the chat."}))
                    else:
                        client_socket.send(Protocol("ERROR", "server", {"message": "Room not found."}).to_str().encode('utf-8'))
                else:
                    client_socket.send(Protocol("ERROR", "server", {"message": "You must be in a room to chat."}).to_str().encode('utf-8'))
            elif command == "SEND_CHAT_MESSAGE":
                room_code = client.get_room_code()
                if room_code != None:
                    if client in rooms[room_code].get_chat_members():
                        room_code = client.get_room_code()
                        if len(rooms[room_code].get_chat_members()) > 1:
                            send_chat_message(room_code, Protocol("CHAT_MESSAGE", message.sender, {"message": message.data["message"]}), client)
                            # Log the chat message
                            chat_logger.info(f"{message.sender}: {message.data['message']}")
                        else:
                            client_socket.send(Protocol("ERROR", "server", {"message": "Both users must be in the room to chat."}).to_str().encode('utf-8'))
                    else:
                        client_socket.send(Protocol("ERROR", "server", {"message": "You must be in the chat to send messages."}).to_str().encode('utf-8'))
                else:
                    client_socket.send(Protocol("ERROR", "server", {"message": "You must be in a room to chat."}).to_str().encode('utf-8'))
            elif command == "LEAVE_ROOM":
                room_code = client.get_room_code()
                if room_code in rooms.keys():
                    if rooms[room_code].get_host().get_socket() == client_socket:
                        rooms[room_code].set_host(None)
                        rooms[room_code].remove_member(client)
                        client.set_room_code(None)
                        broadcast_message(room_code, Protocol("USER_LEFT", "server", {"username": message.sender}))
                    elif client in rooms[room_code].get_members():
                        rooms[room_code].remove_member(client)
                        client.set_room_code(None)
                        broadcast_message(room_code, Protocol("USER_LEFT", "server", {"username": message.sender}))
                    """elif rooms[room_code] == client_socket:
                        rooms[room_code]["guest"] = None
                        broadcast_message(room_code, Protocol("USER_LEFT", "server", {"username": message.sender}))"""
                    if rooms[room_code].get_host() is None and rooms[room_code].get_members() == []:
                        del rooms[room_code]
                    client_socket.send(Protocol("LEFT_ROOM", "server", {}).to_str().encode('utf-8'))
                    logging.info(f"Client {client_address} left room: {room_code}")
            elif command == "ROOM_STATUS":
                room_code = client.get_room_code()
                if room_code in rooms.keys():

                    host_username = str(rooms[room_code].get_host()) if rooms[room_code].get_host() else None
                    room_members = ",\n".join(list(map(str, rooms[room_code].get_members())))
                    status = rooms[room_code].get_status()
                    client_socket.send(Protocol("ROOM_STATUS", "server", {
                        "status": status,
                        "host": host_username,
                        "members": room_members
                    }).to_str().encode('utf-8'))
                else:
                    client_socket.send(Protocol("ERROR", "server", {"message": "Room not found."}).to_str().encode('utf-8'))
            elif command == "CLOSE_ROOM":
                room_code = client.get_room_code()
                if room_code in rooms.keys() and rooms[room_code].get_host() == client:
                    rooms[room_code].set_status("closed")
                    for member in rooms[room_code].get_members():
                        member.set_room_code(None)
                   
                    broadcast_message(room_code, Protocol("ROOM_CLOSED", "server", {}))
                    client_socket.send(Protocol("ROOM_CLOSED", "server", {}).to_str().encode('utf-8'))
                    logging.info(f"Room {room_code} closed by host.")
                    del rooms[room_code]
                else:
                    client_socket.send(Protocol("ERROR", "server", {"message": "Only the host can close the room."}).to_str().encode('utf-8'))
        except Exception as e:
            logging.error(f"Error handling client: {e}")
            raise(e)
            break

    # Clean up on client disconnect
    if client in clients:
        room_code = client.get_room_code()
        clients.remove(client)
        if room_code in rooms.keys() and room_code !=None :
            if rooms[room_code].get_host() == client:
                rooms[room_code].set_host(None)
                rooms[room_code].remove_member(client)
                broadcast_message(room_code, Protocol("USER_LEFT", "server", {"username": message.sender}))
            elif client in rooms[room_code].get_members():
                rooms[room_code].remove_member(client)
                broadcast_message(room_code, Protocol("USER_LEFT", "server", {"username": message.sender}))
            if rooms[room_code]["host"] is None and rooms[room_code]["guest"] is None:
                del rooms[room_code]
        del client
        logging.info(f"Client {client_address} disconnected")

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

if __name__ == "__main__":
    start_server()