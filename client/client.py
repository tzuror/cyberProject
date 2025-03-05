import socket
import threading
import logging
import queue
import os
import sys
child_dir = os.path.dirname(__file__)
parent_dir = os.path.abspath(os.path.join(child_dir, '..'))
sys.path.append(parent_dir)
from protocol import Protocol
import tkinter as tk
from tkinter import ttk  # Import the ttk module
from tkinter import scrolledtext, messagebox, simpledialog
import re
import pyautogui
import io
from PIL import Image, ImageTk
import base64
# Server configuration
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 12345
BUFFER_SIZE = 1000000  # 1 MBs

# Logging configurationa
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=r'C:\Users\ort\Documents\cyberProject\client.log',  # Log to a file
    filemode='a'  # Append mode
)

connected_room_code = None
connected_room_password = None
username = None

lock = threading.Lock()
message_queue = queue.Queue()  # Thread-safe queue for incoming messages
CONNECTION_TIMEOUT = 10  # Timeout in seconds
IN_CHAT = False

USER_NAME = None
EMAIL = None

username = {"username": USER_NAME, "email": EMAIL}

class LobbyWindow:
    def __init__(self, root, client):
        self.root = root
        self.client = client
        self.root.title("Lobby")
        self.root.geometry("500x400")

        # Create a Notebook (tabbed interface)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Lobby Chat
        self.lobby_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.lobby_tab, text="Lobby")

        # Chat area for lobby messages
        self.chat_area = scrolledtext.ScrolledText(self.lobby_tab, state='disabled')
        self.chat_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Status label
        self.status_label = tk.Label(self.lobby_tab, text="Not in a room", fg="red")
        self.status_label.pack(pady=10)

        # Tab 2: User Profile
        self.profile_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.profile_tab, text="Profile")

        # User info in the profile tab
        self.user_info_frame = tk.Frame(self.profile_tab)
        self.user_info_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Username label
        self.username_label = tk.Label(self.user_info_frame, text=f"Username: {USER_NAME}", anchor="w")
        self.username_label.pack(fill=tk.X, pady=5)

        # Email label
        self.email_label = tk.Label(self.user_info_frame, text=f"Email: {EMAIL}", anchor="w")
        self.email_label.pack(fill=tk.X, pady=5)

        # Menu bar
        self.menu_bar = tk.Menu(root)
        self.root.config(menu=self.menu_bar)

        # Room menu
        self.room_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Room", menu=self.room_menu)
        self.room_menu.add_command(label="Create Room", command=self.create_room)
        self.room_menu.add_command(label="Join Room", command=self.join_room)
        self.room_menu.add_command(label="Leave Room", command=self.leave_room)
        self.room_menu.add_command(label="Close Room", command=self.close_room)
        self.room_menu.add_command(label="Check Room Status", command=self.check_room_status)

        # Chat menu
        self.chat_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Chat", menu=self.chat_menu)
        self.chat_menu.add_command(label="Enter Chat", command=self.enter_chat)
        self.chat_menu.add_command(label="Exit Chat", command=self.exit_chat)

        
        # Tab 3: Share Screen
        self.screen_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.screen_tab, text="Share Screen")

        # Canvas to display the shared screen
        self.screen_canvas = tk.Canvas(self.screen_tab, bg="black")
        self.screen_canvas.pack(fill=tk.BOTH, expand=True)

        # Add a new menu for screen sharing
        self.screen_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Screen Share", menu=self.screen_menu)
        self.screen_menu.add_command(label="Start Screen Share", command=self.start_screen_share)
        self.screen_menu.add_command(label="Stop Screen Share", command=self.stop_screen_share)

        # Flag to track screen sharing state
        self.is_sharing_screen = False


        # Flashing red label for screen sharing status
        self.sharing_label = tk.Label(self.lobby_tab, text="Sharing Screen", fg="red")
        self.sharing_label.pack(pady=10)
        self.sharing_label.pack_forget()  # Hide initially
        # Update menu states initially
        self.update_menu_states()

        # Handle window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def start_screen_share(self):
        """Start screen sharing."""
        if not connected_room_code:
            messagebox.showinfo("Info", "You must be in a room to share your screen.")
            return
        if self.is_sharing_screen:
            messagebox.showinfo("Info", "Screen sharing is already active.")
            return

        self.is_sharing_screen = True
        self.client.send(Protocol("START_SCREEN_SHARE", username, {}).to_str().encode('utf-8'))
        threading.Thread(target=self.capture_and_send_screen, daemon=True).start()

        # Show the flashing red label
        self.sharing_label.pack(pady=10)
        self.flash_sharing_label()

    def stop_screen_share(self):
        """Stop screen sharing."""
        if not self.is_sharing_screen:
            messagebox.showinfo("Info", "Screen sharing is not active.")
            return

        self.is_sharing_screen = False
        self.client.send(Protocol("STOP_SCREEN_SHARE", username, {}).to_str().encode('utf-8'))

        self.sharing_label.pack_forget()  # Hide the flashing red label

    def flash_sharing_label(self):
        """Flash the sharing label red."""
        if self.is_sharing_screen:
            current_color = self.sharing_label.cget("fg")
            new_color = "red" if current_color == "white" else "white"
            self.sharing_label.config(fg=new_color)
            self.root.after(500, self.flash_sharing_label)  # Flash every 500ms


    def capture_and_send_screen(self):
        """Capture the screen and send it to the server."""
        while self.is_sharing_screen:
            print("Sharing screen")
            try:
                # Capture the screen
                screenshot = pyautogui.screenshot()

                # Resize the screenshot
                try:
                    # For Pillow >= 10.0.0
                    resampling_filter = Image.Resampling.LANCZOS
                except AttributeError:
                    # For Pillow < 10.0.0
                    resampling_filter = Image.ANTIALIAS

                screenshot = screenshot.resize((800, 600), resampling_filter)  # Resize to 800x600

                # Convert the screenshot to bytes
                img_byte_arr = io.BytesIO()
                screenshot.save(img_byte_arr, format='JPEG', quality=50)  # Lower quality
                img_byte_arr = img_byte_arr.getvalue()

                # Encode the image data as Base64
                img_base64 = base64.b64encode(img_byte_arr).decode('utf-8')

                # Send the screen data to the server
                self.client.sendall(Protocol("SCREEN_DATA", username, {"image_data": img_base64}).to_str().encode('utf-8'))

                # Add a small delay to avoid overloading the network
                threading.Event().wait(0.5)  # Wait for 0.5 seconds
            except Exception as e:
                logging.error(f"Error capturing or sending screen: {e}")
                break

    def handle_message(self, message, lobby_window, chat_window, chat_root):
        # ... (existing code)

        # Handle screen data from other users
        if message.command == "SCREEN_DATA":
            self.display_screen(message.data["image_data"])

    def display_screen(self, image_data):
        """Display the received screen data in the Share Screen tab."""
        try:
            # Check if image_data is a Base64-encoded string
            if isinstance(image_data, str):
                # Decode the Base64 string to bytes
                image_bytes = base64.b64decode(image_data)
            else:
                # Assume image_data is already bytes
                image_bytes = image_data

            # Convert the image data to a PIL image
            image = Image.open(io.BytesIO(image_bytes))

            # Resize the image to fit the canvas
            canvas_width = self.screen_canvas.winfo_width()
            canvas_height = self.screen_canvas.winfo_height()

            if canvas_width > 0 and canvas_height > 0:
                # Use Resampling.LANCZOS instead of ANTIALIAS
                image = image.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)
            else:
                logging.warning("Canvas dimensions are invalid. Using original image size.")

            # Display the image on the canvas
            photo = ImageTk.PhotoImage(image)
            self.screen_canvas.create_image(0, 0, anchor=tk.NW, image=photo)
            self.screen_canvas.image = photo  # Keep a reference to avoid garbage collection
        except Exception as e:
            logging.error(f"Error displaying screen: {e}")
            raise e


    def update_menu_states(self):
        """Update the enabled/disabled state of menu options based on the current state."""
        if connected_room_code and connected_room_password:
            self.room_menu.entryconfig("Create Room", state=tk.DISABLED)
            self.room_menu.entryconfig("Join Room", state=tk.DISABLED)
            self.room_menu.entryconfig("Leave Room", state=tk.NORMAL)
            self.room_menu.entryconfig("Close Room", state=tk.NORMAL)
            self.room_menu.entryconfig("Check Room Status", state=tk.NORMAL)
            self.status_label.config(text=f"In room: {connected_room_code}\nPassword: {connected_room_password}", fg="green")
        else:
            self.room_menu.entryconfig("Create Room", state=tk.NORMAL)
            self.room_menu.entryconfig("Join Room", state=tk.NORMAL)
            self.room_menu.entryconfig("Leave Room", state=tk.DISABLED)
            self.room_menu.entryconfig("Close Room", state=tk.DISABLED)
            self.room_menu.entryconfig("Check Room Status", state=tk.DISABLED)
            self.status_label.config(text="Not in a room", fg="red")

        if IN_CHAT:
            self.chat_menu.entryconfig("Enter Chat", state=tk.DISABLED)
            self.chat_menu.entryconfig("Exit Chat", state=tk.NORMAL)
        else:
            self.chat_menu.entryconfig("Enter Chat", state=tk.NORMAL if connected_room_code else tk.DISABLED)
            self.chat_menu.entryconfig("Exit Chat", state=tk.DISABLED)

    def create_room(self):
        global username
        if connected_room_code:
            messagebox.showinfo("Info", "You are already in a room.")
            return
        #username = simpledialog.askstring("Username", "Enter your username:", parent=self.root)
        if username:
            self.client.send(Protocol("CREATE_ROOM", username, {}).to_str().encode('utf-8'))

    def join_room(self):
        global username
        if connected_room_code:
            messagebox.showinfo("Info", "You are already in a room.")
            return
        #username = simpledialog.askstring("Username", "Enter your username:", parent=self.root)
        if username:
            room_code = simpledialog.askstring("Room Code", "Enter room code:", parent=self.root)
            while room_code == None:
                room_code = simpledialog.askstring("Room Code", "Enter room code:", parent=self.root)
            room_pwd = simpledialog.askstring("Room Password", "Enter room password:", parent=self.root)
            while room_pwd == None:
                room_pwd = simpledialog.askstring("Room Password", "Enter room password:", parent=self.root)

            if room_code and room_pwd:
                self.client.send(Protocol("JOIN_ROOM", username, {"room_code": room_code, "room_pwd": room_pwd}).to_str().encode('utf-8'))

    def leave_room(self):
        if not connected_room_code:
            messagebox.showinfo("Info", "You are not in a room.")
            return
        self.client.send(Protocol("LEAVE_ROOM", username, {}).to_str().encode('utf-8'))

    def close_room(self):
        if not connected_room_code:
            messagebox.showinfo("Info", "You are not in a room.")
            return
        self.client.send(Protocol("CLOSE_ROOM", username, {}).to_str().encode('utf-8'))

    def check_room_status(self):
        if not connected_room_code:
            messagebox.showinfo("Info", "You are not in a room.")
            return
        self.client.send(Protocol("ROOM_STATUS", username, {}).to_str().encode('utf-8'))

    def enter_chat(self):
        if not connected_room_code:
            messagebox.showinfo("Info", "You are not in a room.")
            return
        if IN_CHAT:
            messagebox.showinfo("Info", "You are already in the chat.")
            return
        self.client.send(Protocol("ENTER_CHAT", username, {}).to_str().encode('utf-8'))

    def exit_chat(self):
        if not IN_CHAT:
            messagebox.showinfo("Info", "You are not in the chat.")
            return
        self.client.send(Protocol("LEAVE_CHAT", username, {}).to_str().encode('utf-8'))

    def display_message(self, message):
        """Display a message in the lobby chat area."""
        self.chat_area.config(state='normal')
        self.chat_area.insert(tk.END, message + "\n")
        self.chat_area.config(state='disabled')
        self.chat_area.yview(tk.END)

    def on_close(self):
        """Handle window close event."""
        if connected_room_code:
            self.leave_room()
        self.client.send(Protocol("DISCONNECT", username, {}).to_str().encode('utf-8'))
        self.root.destroy()

class ChatWindow:
    def __init__(self, root, client):
        self.root = root
        self.client = client
        self.root.title("Chat")
        self.root.geometry("600x400")

        # Chat area
        self.chat_area = scrolledtext.ScrolledText(root, state='disabled')
        self.chat_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Message entry field
        self.entry_field = tk.Entry(root)
        self.entry_field.pack(padx=10, pady=10, fill=tk.X)
        self.entry_field.bind("<Return>", self.send_message)

        # Handle window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def send_message(self, event=None):
        message = self.entry_field.get()
        if message:
            send_message(self.client, message)
            self.entry_field.delete(0, tk.END)

    def display_message(self, message):
        """Display a message in the chat area."""
        self.chat_area.config(state='normal')
        self.chat_area.insert(tk.END, message + "\n")
        self.chat_area.config(state='disabled')
        self.chat_area.yview(tk.END)

    def on_close(self):
        """Handle window close event."""
        if IN_CHAT:
            self.client.send(Protocol("LEAVE_CHAT", username, {}).to_str().encode('utf-8'))
        self.root.withdraw()  # Hide the chat window instead of destroying it

def connect_to_server():
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((SERVER_HOST, SERVER_PORT))
        logging.info("Connected to the server.")
        return client
    except Exception as e:
        logging.error(f"Failed to connect to the server: {e}")
        messagebox.showerror("Error", f"Failed to connect to the server: {e}")
        return None

def listen_for_messages(client):
    """Listen for incoming messages from the server and add them to the queue."""
    while True:
        try:
            data = b""
            while True:
                part = client.recv(BUFFER_SIZE)
                data += part
                if len(part) < BUFFER_SIZE:
                    break
            message = Protocol.from_str(data.decode('utf-8'))
            message_queue.put(message)
        except Exception as e:
            logging.error(f"Error receiving message: {e}")
            break

def send_message(client, message):
    if connected_room_code:
        client.send(Protocol("SEND_CHAT_MESSAGE", username, {"message": message}).to_str().encode('utf-8'))
    else:
        messagebox.showinfo("Info", "You are not in a room.")
def get_user_info(root):
    global USER_NAME, EMAIL, username
    while True:
        USER_NAME = simpledialog.askstring("Username", "Enter your username:", parent=root)
        val = True
        if not USER_NAME:
            messagebox.showerror("Error", "Username is required.")
            val = False
            continue
        if len(USER_NAME) > 20:
            messagebox.showerror("Error", "Username is too long.")
        if len(USER_NAME) < 2:
            messagebox.showerror("Error", "Username is too short.")
        if val:
            break
    while True:
        EMAIL = simpledialog.askstring("Email", "Enter your email:", parent=root)
        val = True
        if not EMAIL:
            messagebox.showerror("Error", "Email is required.")
            val = False
            continue
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, EMAIL):
            messagebox.showerror("Error", "Invalid email format.")
            
        elif len(EMAIL) > 50:
            messagebox.showerror("Error", "Email is too long.")
        elif len(EMAIL) < 5:
            messagebox.showerror("Error", "Email is too short.")
        if val:
            break
    username = {"username": USER_NAME, "email": EMAIL}
    return username

def main():
    global USER_NAME, EMAIL, username
    root = tk.Tk()
    
    username = get_user_info(root)
    client = connect_to_server()
    if client:
        # Create the lobby window
        lobby_window = LobbyWindow(root, client)

        # Create the chat window (initially hidden)
        chat_root = tk.Toplevel(root)
        chat_root.withdraw()  # Hide the chat window initially
        chat_window = ChatWindow(chat_root, client)

        # Start the message listener thread
        threading.Thread(target=listen_for_messages, args=(client,), daemon=True).start()

        # Process messages in the main thread
        def process_messages():
            try:
                while True:
                    message = message_queue.get_nowait()
                    handle_message(message, lobby_window, chat_window, chat_root)
            except queue.Empty:
                pass
            root.after(100, process_messages)  # Check for new messages every 100ms

        def handle_message(message, lobby_window, chat_window, chat_root):
            global connected_room_code, connected_room_password, IN_CHAT
            if message.command == "CHAT_MESSAGE":
                chat_window.display_message(f"{message.sender}: {message.data['message']}")
            elif message.command == "USER_JOINED":
                lobby_window.display_message(f"{message.data['username']} joined the room.")
            elif message.command == "ROOM_CREATED":
                with lock:
                    connected_room_code = message.data["room_code"]
                    connected_room_password = message.data["room_pwd"]
                lobby_window.update_menu_states()
                logging.info(f"created room with code: {connected_room_code} and password: {connected_room_password}")
                lobby_window.display_message(f"Room created with code: {connected_room_code} \nPassword: {connected_room_password}")    
            elif message.command == "ROOM_JOINED":
                with lock:
                    connected_room_code = message.data["room_code"]
                    connected_room_password = message.data["room_pwd"]

                lobby_window.update_menu_states()
                logging.info(f"Joined room with code: {connected_room_code} and password: {connected_room_password}")
                lobby_window.display_message(f"Joined room with code: {connected_room_code} \nPassword: {connected_room_password}")
            elif message.command == "ROOM_NOT_FOUND":
                lobby_window.display_message("Room not found.")
            elif message.command == "LEFT_ROOM":
                with lock:
                    connected_room_code = None
                    IN_CHAT = False
                lobby_window.update_menu_states()
                chat_root.withdraw()  # Hide the chat window
                lobby_window.display_message("You have left the room.")
            elif message.command == "ROOM_CLOSED":
                with lock:
                    connected_room_code = None
                    IN_CHAT = False
                lobby_window.update_menu_states()
                chat_root.withdraw()
                lobby_window.display_message("The room has been closed by the host.")
            elif message.command == "USER_LEFT":
                lobby_window.display_message(f"{message.data['username']} has left the room.")
            elif message.command == "NEW_HOST":
                lobby_window.display_message(f"{message.data['username']} is the new host.")
            elif message.command == "ERROR":
                messagebox.showinfo("Error", message.data["message"])
                lobby_window.display_message(f"Error: {message.data['message']}")
            elif message.command == "INCORRECT_PASSWORD":
                lobby_window.display_message("Incorrect password.")    
            elif message.command == "ENTERED_CHAT":
                with lock:
                    IN_CHAT = True
                lobby_window.update_menu_states()
                chat_root.deiconify()  # Show the chat window
            elif message.command == "LEFT_CHAT":
                with lock:
                    IN_CHAT = False
                lobby_window.update_menu_states()
                chat_root.withdraw()  # Hide the chat window
            elif message.command == "ROOM_STATUS":
                status = message.data["status"]
                host = message.data["host"]
                members = message.data["members"]
                lobby_window.display_message(f"Room Status: {status}")
                lobby_window.display_message(f"Host: {host}")
                lobby_window.display_message(f"Members: {members}")
            elif message.command == "SCREEN_DATA":  # Handle screen sharing data
                lobby_window.display_screen(message.data["image_data"])

        root.after(1, process_messages)  # Start processing messages
        root.mainloop()

if __name__ == "__main__":
    main()