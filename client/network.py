import socket
import logging
import threading
import queue
import os
import sys
from tkinter import messagebox
child_dir = os.path.dirname(__file__)
parent_dir = os.path.abspath(os.path.join(child_dir, '..'))
sys.path.append(parent_dir)
from protocol import Protocol
import constants
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=r'C:\Users\ort\Documents\cyberProject\client_network.log',  # Log to a file
    filemode='a'  # Append mode
)
client_udp_msg = logging.getLogger('client_udp_msg')
client_udp_msg.setLevel(logging.INFO)
client_udp_handler = logging.FileHandler(r'C:\Users\ort\Documents\cyberProject\client_udp_msg.log')
client_udp_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
client_udp_msg.addHandler(client_udp_handler)


def connect_to_server(userinfo):
    try:
        client_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_tcp.connect((constants.SERVER_HOST, constants.SERVER_PORT))


        udp_port_msg = Protocol.from_str(client_tcp.recv(1024).decode('utf-8'))
        if udp_port_msg.command == "UDP_PORT":
            udp_server_port = udp_port_msg.data["udp_port"]
            server_udp_addr = (constants.SERVER_HOST, udp_server_port) 
            client_tcp.send(Protocol("GOT_UDP_PORT", userinfo, {}).to_str().encode('utf-8'))
            print(f"Received server's UDP port: {udp_port_msg}")

            ack_msg = Protocol.from_str(client_tcp.recv(1024).decode('utf-8'))
            if ack_msg.command == "ACK":

                client_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                client_udp.bind(('0.0.0.0', 0)) # Bind to any available port
                client_udp_port = client_udp.getsockname()[1]  # Get the assigned port
                print(f"UDP socket is ready on port {client_udp_port}")
                client_tcp.send(Protocol("UDP_PORT", userinfo, {"udp_port": client_udp_port}).to_str().encode('utf-8'))
                got_udp_port_msg = Protocol.from_str(client_tcp.recv(1024).decode('utf-8'))
                if got_udp_port_msg.command == "GOT_UDP_PORT":
                    client_tcp.send(Protocol("ACK", userinfo, {}).to_str().encode('utf-8'))
                logging.info("Connected to the server.")
                return client_tcp, client_udp, server_udp_addr
            else:
                raise Exception(f"Expected ACK message, but received: {ack_msg}")
        else:
            raise Exception(f"Expected UDP_PORT message, but received: {udp_port_msg}")
    except Exception as e:
        logging.error(f"Failed to connect to the server: {e}")
        messagebox.showerror("Error", f"Failed to connect to the server: {e}")
        return None

def listen_for_messages(client, message_queue):
    """Listen for incoming messages from the server and add them to the queue."""
    while True:
        try:
            data = b""
            while True:
                part = client.recv(constants.BUFFER_SIZE)
                data += part
                if len(part) < constants.BUFFER_SIZE:
                    break
            message = Protocol.from_str(data.decode('utf-8'))
            message_queue.put(message)
        except Exception as e:
            logging.error(f"Error receiving message: {e}")
            break

def listen_for_udp_messages(client_udp, server_udp_addr, message_queue):
    """Listen for incoming UDP messages from the server."""
    buffer = {}
    current_frame_id = 0
    while True:
        try:
            chunk, addr = client_udp.recvfrom(2*constants.PACKET_SIZE)
            if addr == server_udp_addr:
                if Protocol.is_str_valid(chunk.decode('utf-8')):
                    packet = Protocol.from_str(chunk.decode('utf-8'))
                    if packet.command == "SCREEN_DATA_CHUNK":
                        if packet.data["frame_id"] == current_frame_id:
                            client_udp_msg.info(f"Received chunk {packet.data['chunk_id']} / {packet.data['total_chunks']} of frame {packet.data['frame_id']}")
                            buffer[packet.data["chunk_id"]] = packet.data["chunk"]

                            if len(buffer) == packet.data["total_chunks"]:
                                image_data = "".join(buffer.values())
                                message_queue.put(Protocol("SCREEN_DATA", packet.sender, {"image_data": image_data}))
                                client_udp_msg.info(f"frame {current_frame_id} finished")
                                buffer.clear()
                        elif packet.data["frame_id"] > current_frame_id:
                            buffer.clear()
                            current_frame_id = packet.data["frame_id"]
                            buffer[packet.data["chunk_id"]] = packet.data["chunk"]
                            logging.info(f"Received frame {current_frame_id} from {packet.sender} ")
                        elif packet.data["frame_id"] < current_frame_id:
                            continue
        except Exception as e:
            logging.error(f"Error receiving UDP message: {e}")
            break

def send_message(client, message, userinfo, connected_room_code):
    """Send a chat message to the server."""
    if connected_room_code:
        client.send(Protocol("SEND_CHAT_MESSAGE", userinfo, {"message": message}).to_str().encode('utf-8'))
    else:
        messagebox.showinfo("Info", "You are not in a room.")
