import os
import sys
child_dir = os.path.dirname(__file__)
parent_dir = os.path.abspath(os.path.join(child_dir, '..'))
sys.path.append(parent_dir)
from protocol import Protocol
import tkinter as tk
from tkinter import ttk  # Import the ttk module
from tkinter import scrolledtext, messagebox, simpledialog
PACKET_SIZE = 1024
import pyautogui
from PIL import Image, ImageTk
import io
import base64
import logging
import threading
from network import send_message
from screen_share import capture_and_send_screen
import re
class LobbyWindow:
    def __init__(self, root, userinfo, client, client_udp, server_udp_addr, member_id, shutdown_flag, connected_room_code= None, connected_room_password= None, in_chat= False):
        self.root = root
        self.client = client
        self.userinfo = userinfo
        self.client_udp = client_udp
        self.server_udp_addr = server_udp_addr
        self.member_id = member_id
        self.connected_room_code = connected_room_code
        self.connected_room_password = connected_room_password
        self.in_chat = in_chat
        self.username = userinfo["username"]
        self.email = userinfo["email"]
        self.root.title("Lobby")
        self.root.geometry("500x400")
        self.shutdown_flag = shutdown_flag

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
        self.username_label = tk.Label(self.user_info_frame, text=f"Username: {self.username}", anchor="w")
        self.username_label.pack(fill=tk.X, pady=5)

        # Email label
        self.email_label = tk.Label(self.user_info_frame, text=f"Email: {self.email}", anchor="w")
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

        self.screen_canvas.bind("<Configure>", self.on_canvas_resize)
        self.last_screen_image = None

        self.room_members_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.room_members_tab, text="Room Members")

        self.refresh_button = tk.Button(self.room_members_tab, text="Refresh", command=self.refresh_members)
        self.refresh_button.pack(pady=10)

        # Frame to hold member labels and kick buttons
        self.members_frame = tk.Frame(self.room_members_tab)
        self.members_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Update room members initially
        self.refresh_members()

        # Add a new menu for screen sharing
        self.screen_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Screen Share", menu=self.screen_menu)
        self.screen_menu.add_command(label="Start Screen Share", command=self.start_screen_share)
        self.screen_menu.add_command(label="Stop Screen Share", command=self.stop_screen_share)

        # Flag to track screen sharing state
        self.is_sharing_screen = False

        self.sound_share_var = tk.BooleanVar()
        self.sound_share_checkbox = tk.Checkbutton(self.screen_menu, text="Share Sound", variable=self.sound_share_var)
        self.screen_menu.add_checkbutton(label="Share Sound", variable=self.sound_share_var)


        # Flashing red label for screen sharing status
        self.sharing_label = tk.Label(self.lobby_tab, text="Sharing Screen", fg="red")
        self.sharing_label.pack(pady=10)
        self.sharing_label.pack_forget()  # Hide initially

        # Update menu states initially
        self.update_menu_states()

        # Handle window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    def refresh_members(self):
        """Refresh the list of members in the room."""
        if not self.connected_room_code:
            return

        # Clear the existing member labels and buttons
        """for widget in self.members_frame.winfo_children():
            widget.destroy()"""

        # Request the room status from the server
       # self.client.send(Protocol("ROOM_STATUS", self.userinfo, {}).to_str().encode('utf-8'))

    def set_connected_room_code(self, room_code):
        self.connected_room_code = room_code
        self.update_menu_states()
    def set_connected_room_password(self, room_pwd):
        self.connected_room_password = room_pwd
        self.update_menu_states()
    def set_in_chat(self, in_chat):
        self.in_chat = in_chat
        self.update_menu_states()
    def set_username(self, username):
        self.username = username
        self.update_menu_states()

    def on_canvas_resize(self, event):
        """Handle canvas resizing."""
        if self.last_screen_image:
            # Redisplay the last image with the new canvas size
            self.display_screen(self.last_screen_image)

    def start_screen_share(self):
        """Start screen sharing."""
        if not self.connected_room_code:
            messagebox.showinfo("Info", "You must be in a room to share your screen.")
            return
        if self.is_sharing_screen:
            messagebox.showinfo("Info", "Screen sharing is already active.")
            return

        share_sound = self.sound_share_var.get()

        self.client.send(Protocol("START_SCREEN_SHARE", self.userinfo, {}).to_str().encode('utf-8'))
        #self.is_sharing_screen = True
        #self.client.send(Protocol("START_SCREEN_SHARE", username, {}).to_str().encode('utf-8'))
        #threading.Thread(target=self.capture_and_send_screen, daemon=True).start()

        # Show the flashing red label
        self.sharing_label.pack(pady=10)
        self.flash_sharing_label()

    def stop_screen_share(self):
        """Stop screen sharing."""
        if not self.is_sharing_screen:
            messagebox.showinfo("Info", "Screen sharing is not active.")
            return

        self.is_sharing_screen = False
        self.client.send(Protocol("STOP_SCREEN_SHARE", self.userinfo, {}).to_str().encode('utf-8'))

        self.sharing_label.pack_forget()  # Hide the flashing red label

    def flash_sharing_label(self):
        """Flash the sharing label red."""
        if self.is_sharing_screen:
            current_color = self.sharing_label.cget("fg")
            new_color = "red" if current_color == "white" else "white"
            self.sharing_label.config(fg=new_color)
            self.root.after(500, self.flash_sharing_label)  # Flash every 500ms
    
    def start_screen_share_after_approval(self):
        """Start screen sharing after receiving approval from the server."""
        if not self.is_sharing_screen:
            self.is_sharing_screen = True
            threading.Thread(target=self.capture_and_send_share_screen, daemon=True).start()
            #threading.Thread(target=self.capture_and_send_sound, daemon=True).start()

    def capture_and_send_sound(self):
        """Capture sound data."""
        while self.is_sharing_screen:
            if self.sound_share_var.get():
                # Implement sound capture logic here
                # This could involve using a library like pyaudio to capture audio from the microphone
                # Return the captured sound data as bytes or Base64-encoded string
                sound_data = "Sound data"
                self.client.sendall(Protocol("SOUND_DATA", self.userinfo, {"sound_data": sound_data}).to_str().encode('utf-8'))
            threading.Event().wait(1)

        # Implement sound capture logic here
        # This could involve using a library like pyaudio to capture audio from the microphone
        # Return the captured sound data as bytes or Base64-encoded string
    def capture_and_send_share_screen(self):
        frame_id = 0
        while self.is_sharing_screen:
            frame_id += 1
            capture_and_send_screen(frame_id, self.client_udp, self.server_udp_addr, self.userinfo)
            # Add a small delay to avoid overloading the network
            threading.Event().wait(0.02)  # Wait for 0.5 seconds
        self.client_udp.sendto(Protocol("STOP_SHARE", self.userinfo, {}).to_str().encode('utf-8'), self.server_udp_addr)
    

    def handle_message(self, message, lobby_window, chat_window, chat_root):
        # ... (existing code)

        # Handle screen data from other users
        if message.command == "SCREEN_DATA":
            self.display_screen(message.data["image_data"])
    
    def display_screen(self, image_data):
        """Display the received screen data in the Share Screen tab."""
        try:
            # Store the last image for potential resizing
            self.last_screen_image = image_data

            # Check if image_data is a Base64-encoded string
            if isinstance(image_data, str):
                # Decode the Base64 string to bytes
                image_bytes = base64.b64decode(image_data)
            else:
                # Assume image_data is already bytes
                image_bytes = image_data

            # Convert the image data to a PIL image
            image = Image.open(io.BytesIO(image_bytes))

            # Get the current canvas dimensions
            canvas_width = self.screen_canvas.winfo_width()
            canvas_height = self.screen_canvas.winfo_height()

            # Clear previous content
            self.screen_canvas.delete("all")

            # If canvas dimensions are valid
            if canvas_width > 0 and canvas_height > 0:
                # Calculate the aspect ratio of the image and the canvas
                image_ratio = image.width / image.height
                canvas_ratio = canvas_width / canvas_height

                # Resize the image to fit the canvas while maintaining aspect ratio
                if canvas_ratio > image_ratio:
                    # Canvas is wider than the image
                    new_height = canvas_height
                    new_width = int(image_ratio * new_height)
                else:
                    # Canvas is taller than the image
                    new_width = canvas_width
                    new_height = int(new_width / image_ratio)

                # Resize the image
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

                # Create PhotoImage
                photo = ImageTk.PhotoImage(image)

                # Calculate position to center the image
                x = (canvas_width - new_width) // 2
                y = (canvas_height - new_height) // 2

                # Display the centered image
                self.screen_canvas.create_image(x, y, anchor=tk.NW, image=photo)
                self.screen_canvas.image = photo  # Keep a reference to avoid garbage collection
        except Exception as e:
            logging.error(f"Error displaying screen: {e}")
    
    
    def play_sound(self, sound_data):
        """Play the received sound data."""
        # Implement sound playback logic here
        # This could involve using a library like pyaudio to play the sound
        print("Playing sound data")
        pass

    def update_members_list(self, host, members):
        """Update the list of members in the Room Members tab."""
        # Clear the existing member labels and buttons
        print(members)
        for widget in self.members_frame.winfo_children():
            widget.destroy()
        host_id = host["id"]
        host_name = host["name"]
        host_email = host["email"]
        # Display the host
        host_label = tk.Label(self.members_frame, text=f"Host: \nid: {host_id} - {host_name} - {host_email}", anchor="w")
        host_label.pack(fill=tk.X, pady=5)

        members_label = tk.Label(self.members_frame, text=f"Members:\n", anchor="w")
        members_label.pack(fill=tk.X, pady=5)
        # Display each member with a "Kick" button
        for member in members:
            member_frame = tk.Frame(self.members_frame)
            member_frame.pack(fill=tk.X, pady=2)
            member_id = member["id"]
            member_name = member["name"]
            member_email = member["email"]
            member_label = tk.Label(member_frame, text=f"id: {member_id} - {member_name} - {member_email}", anchor="w")
            member_label.pack(side=tk.LEFT, padx=5)

            if host["id"] == self.member_id and member["id"] != self.member_id:
                kick_button = tk.Button(member_frame, text="Kick", command=lambda m=member_id: self.kick_member(m))
                kick_button.pack(side=tk.RIGHT, padx=5)
    def kick_member(self, member_id: str):
        """Kick a member from the room."""
        if not self.connected_room_code:
            messagebox.showinfo("Info", "You are not in a room.")
            return

        self.client.send(Protocol("KICK_MEMBER", self.userinfo, {"username": member_id}).to_str().encode('utf-8'))


    def update_menu_states(self):
        """Update the enabled/disabled state of menu options based on the current state."""
        if self.connected_room_code and self.connected_room_password:
            self.room_menu.entryconfig("Create Room", state=tk.DISABLED)
            self.room_menu.entryconfig("Join Room", state=tk.DISABLED)
            self.room_menu.entryconfig("Leave Room", state=tk.NORMAL)
            self.room_menu.entryconfig("Close Room", state=tk.NORMAL)
            self.room_menu.entryconfig("Check Room Status", state=tk.NORMAL)
            self.status_label.config(text=f"In room: {self.connected_room_code}\nPassword: {self.connected_room_password}", fg="green")
        else:
            self.room_menu.entryconfig("Create Room", state=tk.NORMAL)
            self.room_menu.entryconfig("Join Room", state=tk.NORMAL)
            self.room_menu.entryconfig("Leave Room", state=tk.DISABLED)
            self.room_menu.entryconfig("Close Room", state=tk.DISABLED)
            self.room_menu.entryconfig("Check Room Status", state=tk.DISABLED)
            self.status_label.config(text="Not in a room", fg="red")

        if self.in_chat:
            self.chat_menu.entryconfig("Enter Chat", state=tk.DISABLED)
            self.chat_menu.entryconfig("Exit Chat", state=tk.NORMAL)
        else:
            self.chat_menu.entryconfig("Enter Chat", state=tk.NORMAL if self.connected_room_code else tk.DISABLED)
            self.chat_menu.entryconfig("Exit Chat", state=tk.DISABLED)

    def create_room(self):
        if self.connected_room_code:
            messagebox.showinfo("Info", "You are already in a room.")
            return
        #username = simpledialog.askstring("Username", "Enter your username:", parent=self.root)
        if self.userinfo:
            self.client.send(Protocol("CREATE_ROOM", self.userinfo, {}).to_str().encode('utf-8'))

    def join_room(self):
        if self.connected_room_code:
            messagebox.showinfo("Info", "You are already in a room.")
            return
        #username = simpledialog.askstring("Username", "Enter your username:", parent=self.root)
        if self.userinfo:
            room_code = simpledialog.askstring("Room Code", "Enter room code:", parent=self.root)
            while room_code == None:
                room_code = simpledialog.askstring("Room Code", "Enter room code:", parent=self.root)
            room_pwd = simpledialog.askstring("Room Password", "Enter room password:", parent=self.root)
            while room_pwd == None:
                room_pwd = simpledialog.askstring("Room Password", "Enter room password:", parent=self.root)

            if room_code and room_pwd:
                self.client.send(Protocol("JOIN_ROOM", self.userinfo, {"room_code": room_code, "room_pwd": room_pwd}).to_str().encode('utf-8'))

    def leave_room(self):
        if self.is_sharing_screen:
            self.stop_screen_share()
        if not self.connected_room_code:
            messagebox.showinfo("Info", "You are not in a room.")
            return
        self.client.send(Protocol("LEAVE_ROOM", self.userinfo, {}).to_str().encode('utf-8'))

    def close_room(self):
        if not self.connected_room_code:
            messagebox.showinfo("Info", "You are not in a room.")
            return
        self.client.send(Protocol("CLOSE_ROOM", self.userinfo, {}).to_str().encode('utf-8'))

    def check_room_status(self):
        if not self.connected_room_code:
            messagebox.showinfo("Info", "You are not in a room.")
            return
        self.client.send(Protocol("ROOM_STATUS", self.userinfo, {}).to_str().encode('utf-8'))

    def enter_chat(self):
        if not self.connected_room_code:
            messagebox.showinfo("Info", "You are not in a room.")
            return
        if self.in_chat:
            messagebox.showinfo("Info", "You are already in the chat.")
            return
        self.client.send(Protocol("ENTER_CHAT", self.userinfo, {}).to_str().encode('utf-8'))

    def exit_chat(self):
        if not self.in_chat:
            messagebox.showinfo("Info", "You are not in the chat.")
            return
        self.client.send(Protocol("LEAVE_CHAT", self.userinfo, {}).to_str().encode('utf-8'))

    def display_message(self, message):
        """Display a message in the lobby chat area."""
        self.chat_area.config(state='normal')
        self.chat_area.insert(tk.END, message + "\n")
        self.chat_area.config(state='disabled')
        self.chat_area.yview(tk.END)

    def on_close(self):
        """Handle window close event."""
        if self.connected_room_code:
            self.leave_room()
        self.client.send(Protocol("DISCONNECT", self.userinfo, {}).to_str().encode('utf-8'))
        self.shutdown_flag.set()
        self.root.destroy()

class ChatWindow:
    def __init__(self, root, userinfo, client, in_chat= False, connected_room_code= None):
        self.root = root
        self.client = client
        self.userinfo = userinfo
        self.in_chat = in_chat
        self.connected_room_code = connected_room_code
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
    def set_in_chat(self, in_chat):
        self.in_chat = in_chat
    def set_connected_room_code(self, room_code):
        self.connected_room_code = room_code

    def send_message(self, event=None):
        message = self.entry_field.get()
        if message:
            send_message(self.client, message, self.userinfo, self.connected_room_code)
            self.entry_field.delete(0, tk.END)

    def display_message(self, message):
        """Display a message in the chat area."""
        self.chat_area.config(state='normal')
        self.chat_area.insert(tk.END, message + "\n")
        self.chat_area.config(state='disabled')
        self.chat_area.yview(tk.END)

    def on_close(self):
        """Handle window close event."""
        if self.in_chat:
            self.client.send(Protocol("LEAVE_CHAT", self.userinfo, {}).to_str().encode('utf-8'))
        self.root.withdraw()  # Hide the chat window instead of destroying it

def get_user_info(root):
    while True:
        user_name = simpledialog.askstring("Username", "Enter your username:", parent=root)
        val = True
        if not user_name:
            messagebox.showerror("Error", "Username is required.")
            val = False
            continue
        if len(user_name) > 20:
            messagebox.showerror("Error", "Username is too long.")
        if len(user_name) < 2:
            messagebox.showerror("Error", "Username is too short.")
        if val:
            break
    while True:
        email = simpledialog.askstring("Email", "Enter your email:", parent=root)
        val = True
        if not email:
            messagebox.showerror("Error", "Email is required.") 
            val = False
            continue
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            messagebox.showerror("Error", "Invalid email format.")
        elif len(email) > 50:
            messagebox.showerror("Error", "Email is too long.")
        elif len(email) < 5:
            messagebox.showerror("Error", "Email is too short.")
        if val:
            break
    userinfo = {"username": user_name, "email": email}
    return userinfo