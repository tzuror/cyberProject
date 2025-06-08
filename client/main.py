import tkinter as tk
import threading
import queue
from network import connect_to_server, listen_for_messages, listen_for_udp_messages, send_message
from gui import LobbyWindow, ChatWindow, get_user_info
from screen_share import capture_and_send_screen, split_and_send_screen
import logging
from tkinter import messagebox
import constants
import base64
import socket
import tkinter.filedialog

logging.basicConfig(
    level= logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=r'client.log',  # Log to a file
    filemode='w'  # ]replace mode
)
current_file = None  # For tracking incoming file transfers
client_msg = logging.getLogger('client_msg')
client_msg.setLevel(logging.INFO)
client_handler = logging.FileHandler(r'client_msg.log', mode='w')
client_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
client_msg.addHandler(client_handler)
lock = threading.Lock()
shutdown_flag = threading.Event()
message_queue = queue.Queue()  # Thread-safe queue for incoming messages
def main():
    #global USER_NAME, EMAIL, userinfo, client_tcp, client_udp, server_udp_addr
    root = tk.Tk()
    
    userinfo = get_user_info(root)
    
    client_tcp, client_udp, server_udp_addr, member_id = connect_to_server(userinfo=userinfo)
    if client_tcp:
        # Create the lobby window
        lobby_window = LobbyWindow(root,userinfo=userinfo,client=client_tcp, client_udp=client_udp, server_udp_addr=server_udp_addr, member_id=member_id, shutdown_flag=shutdown_flag)

        # Create the chat window (initially hidden)
        chat_root = tk.Toplevel(root)
        chat_root.withdraw()  # Hide the chat window initially
        chat_window = ChatWindow(chat_root,userinfo=userinfo, client= client_tcp)

        # Start the message listener thread
        threading.Thread(target=listen_for_udp_messages,args=(client_udp, server_udp_addr, message_queue), daemon=True).start()
        threading.Thread(target=listen_for_messages, args=(client_tcp, message_queue, shutdown_flag), daemon=True).start()
        

        # Process messages in the main thread
        def process_messages():
            try:        
                while True:
                    message = message_queue.get_nowait()
                    handle_message(message, lobby_window, chat_window, chat_root)
            except queue.Empty:
                pass
            root.after(100, process_messages)  # Check for new messages every 100ms

        def handle_message(message, lobby_window: LobbyWindow, chat_window: ChatWindow, chat_root):
            global connected_room_code, connected_room_password, in_chat
            if message.command == "CHAT_MESSAGE":
                chat_window.display_message(f"{message.sender}: {message.data['message']}")
            elif message.command == "SCREEN_DATA":  # Handle screen sharing data
                try:
                    lobby_window.display_screen(message.data["image_data"])
                    
                except Exception as e:
                    client_msg.error(f"Error displaying screen data: {e}")
            elif message.command == "SOUND_DATA":
                lobby_window.play_sound(message.data["sound_data"])
            elif message.command == "SCREEN_SHARE_APPROVED":
                lobby_window.display_message("Screen sharing approved.")
                lobby_window.start_screen_share_after_approval()
            elif message.command == "SCREEN_SHARE_STOPPED":
                message = "Screen sharing stopped."
                try:
                    print(message)
                    print(message.data)
                    lobby_window.display_message(message.data['message'])
                    messagebox.showinfo("Info", message.data["message"])
                    message += "\n" + message.data["message"]
                except Exception as e:
                    print(e)
                    pass
                lobby_window.display_message(message)
                with lock:
                    lobby_window.sharing_label.place_forget()
                    lobby_window.is_sharing_screen = False
            elif message.command == "USER_STOPPED_SCREEN_SHARE":
                lobby_window.display_message(f"{message.data['username']} stopped screen sharing.")
                if "message" in message.data:
                    lobby_window.display_message(message.data["message"])
            elif message.command == "USER_JOINED":
                lobby_window.display_message(f"{message.data['username']} joined the room.")
            elif message.command == "ROOM_CREATED":
                with lock:
                    connected_room_code = message.data["room_code"]
                    lobby_window.set_connected_room_code(connected_room_code)
                    chat_window.set_connected_room_code(connected_room_code)
                    connected_room_password = message.data["room_pwd"]
                    lobby_window.set_connected_room_password(connected_room_password)
                lobby_window.update_menu_states()
                client_msg.info(f"created room with code: {connected_room_code} and password: {connected_room_password}")
                lobby_window.display_message(f"Room created with code: {connected_room_code} \nPassword: {connected_room_password}")    
            elif message.command == "ROOM_JOINED":
                with lock:
                    connected_room_code = message.data["room_code"]
                    lobby_window.set_connected_room_code(connected_room_code)
                    chat_window.set_connected_room_code(connected_room_code)
                    connected_room_password = message.data["room_pwd"]
                    lobby_window.set_connected_room_password(connected_room_password)

                lobby_window.update_menu_states()
                client_msg.info(f"Joined room with code: {connected_room_code} and password: {connected_room_password}")
                lobby_window.display_message(f"Joined room with code: {connected_room_code} \nPassword: {connected_room_password}")
            elif message.command == "ROOM_NOT_FOUND":
                lobby_window.display_message("Room not found.")
            elif message.command == "LEFT_ROOM" or message.command == "KICKED_FROM_ROOM":
                with lock:
                    connected_room_code = None
                    lobby_window.set_connected_room_code(connected_room_code)
                    chat_window.set_connected_room_code(connected_room_code)
                    connected_room_password = None
                    lobby_window.set_connected_room_password(connected_room_password)
                    in_chat = False
                    lobby_window.set_in_chat(in_chat)
                    chat_window.set_in_chat(in_chat)
                lobby_window.update_menu_states()
                chat_root.withdraw()  # Hide the chat window
                if message.command == "KICKED_FROM_ROOM":
                    lobby_window.display_message("You have been kicked from the room.")
                    messagebox.showinfo("Info", "You have been kicked from the room by the host.")
                    
                    with lock:
                        lobby_window.is_sharing_screen = False
                        lobby_window.sharing_label.place_forget()
                else:
                    lobby_window.display_message("You have left the room.")
            elif message.command == "ROOM_CLOSED":
                with lock:
                    connected_room_code = None
                    lobby_window.set_connected_room_code(connected_room_code)
                    connected_room_password = None
                    lobby_window.set_connected_room_password(connected_room_password)
                    in_chat = False
                    lobby_window.set_in_chat(in_chat)
                    chat_window.set_in_chat(in_chat)
                lobby_window.update_menu_states()
                chat_root.withdraw()
                lobby_window.display_message("The room has been closed by the host.")
            elif message.command == "USER_LEFT":
                lobby_window.display_message(f"{message.data['username']} has left the room.")
            elif message.command == "USER_KICKED":
                lobby_window.display_message(f"{message.data['username']} has been kicked from the room.")
                if message.data.get("message"):
                    lobby_window.display_message(f"Reason: {message.data['message']}")
            elif message.command == "NEW_HOST":
                lobby_window.display_message(f"{message.data['username']} - {message.data["host_id"]} is the new host.")
                if message.data["host_id"] == member_id:
                    messagebox.showinfo("New Host", "You are now the host of the room.")
                lobby_window.host_id = message.data["host_id"]
            elif message.command == "ERROR":
                messagebox.showinfo("Error", message.data["message"])
                lobby_window.display_message(f"Error: {message.data['message']}")
            elif message.command == "INCORRECT_PASSWORD":
                lobby_window.display_message("Incorrect password.")    
            elif message.command == "ENTERED_CHAT":
                with lock:
                    in_chat = True
                    lobby_window.set_in_chat(in_chat)
                    chat_window.set_in_chat(in_chat)
                lobby_window.update_menu_states()
                chat_root.deiconify()  # Show the chat window
            elif message.command == "LEFT_CHAT":
                with lock:
                    in_chat = False
                    lobby_window.set_in_chat(in_chat)
                lobby_window.update_menu_states()
                chat_root.withdraw()  # Hide the chat window
            elif message.command == "ROOM_STATUS":
                status = message.data["status"]
                host = message.data["host"]
                members = message.data["members"]
                #members_str = "\n".join(members)
                #lobby_window.display_message(f"Room Status: {status}")
                #lobby_window.display_message(f"Host: {host}")
                #lobby_window.display_message(f"Members: {members_str}")
                lobby_window.update_members_list(host, members)
            elif message.command == "FILE_METADATA":
                # Show notification about incoming file
                lobby_window.display_message(f"Receiving file: {message.data['file_name']} ({message.data['file_size']} bytes)")
                
                # Store file metadata for reconstruction
                global current_file
                current_file = {
                    'name': message.data['file_name'],
                    'size': message.data['file_size'],
                    'total_chunks': message.data['total_chunks'],
                    'received_chunks': 0,
                    'data': []
                }

            elif message.command == "FILE_CHUNK":
                if current_file and current_file['name'] == message.data['file_name']:
                    # Add chunk to file data
                    current_file['data'].append(base64.b64decode(message.data['chunk_data']))
                    current_file['received_chunks'] += 1
                    
                    # Check if all chunks received
                    if current_file['received_chunks'] == current_file['total_chunks']:
                        # Save the complete file
                        chat_window.display_message(f"{message.sender}: sent a file '{current_file['name']}'' ")
                        # Ask user if he wants to recive the file in a tkinter window 
                        accept_file = messagebox.askyesno(
                            f"File Transfer",
                            f"FILE SENT IN CHAT!\n{message.sender} sent the file '{current_file['name']}', \nDo you want to recive the file  ({current_file['size']} bytes)?"
                        )

                        if accept_file:
                            file_path = tkinter.filedialog.asksaveasfilename(
                                initialfile=current_file['name'],
                                title="Save received file"
                            )
                            
                            if file_path:
                                try:
                                    with open(file_path, 'wb') as file:
                                        for chunk in current_file['data']:
                                            file.write(chunk)
                                    lobby_window.display_message(f"File saved: {current_file['name']}")
                                    #chat_window.display_message(f"File saved: {current_file['name']}")
                                    # add a link to the file in the chat window
                                    chat_window.add_file_link_to_chat(current_file['name'], file_path)
                                except Exception as e:
                                    logging.error(f"Error saving file: {e}")
                                    chat_window.display_message(f"server: Error saving file")
                            else:
                                chat_window.display_message(f"server: File transfer cancelled: {current_file['name']}")  
                        # Reset current file
                        else:
                            lobby_window.display_message(f"File '{current_file['name']}' was declined.")
                        current_file = None
            
        root.after(1, process_messages)  # Start processing messages
        root.mainloop()

if __name__ == "__main__":
    main()