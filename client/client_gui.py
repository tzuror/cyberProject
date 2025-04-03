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
class LobbyWindow:
    def __init__(self, root, userinfo, client, client_udp, server_udp_addr, connected_room_code, connected_room_password, IN_CHAT ):
        self.root = root
        self.client = client
        self.userinfo = userinfo
        self.client_udp = client_udp
        self.server_udp_addr = server_udp_addr
        self.connected_room_code = connected_room_code
        self.connected_room_password = connected_room_password
        self.IN_CHAT = IN_CHAT
        self.username = userinfo["username"]
        self.email = userinfo["email"]
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
        """if not self.is_sharing_screen:
            messagebox.showinfo("Info", "Screen sharing is not active.")
            return

        self.is_sharing_screen = False"""
        self.client.send(Protocol("STOP_SCREEN_SHARE", self.userinfo, {}).to_str().encode('utf-8'))

        #self.sharing_label.pack_forget()  # Hide the flashing red label

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
            threading.Thread(target=self.capture_and_send_screen, daemon=True).start()
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
    def split_and_send_screen(self, frame_id, img_bytes):
        global server_udp_addr, client_udp
        total_chunks = (len(img_bytes) // PACKET_SIZE) + 1
        for chunk_id in range(total_chunks):
            chunk = img_bytes[chunk_id * PACKET_SIZE : (chunk_id + 1) * PACKET_SIZE]
            packet = Protocol("SCREEN_DATA_CHUNK", self.userinfo, {"frame_id": frame_id, "total_chunks": total_chunks, "chunk_id": chunk_id, "chunk": chunk}).to_str().encode('utf-8')
            client_udp.sendto(packet, server_udp_addr)

        



    def capture_and_send_screen(self):
        """Capture the screen and send it to the server."""
        frame_id = 0
        while self.is_sharing_screen:
            print("Sharing screen")
            try:
                frame_id += 1
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

                # Capture sound if sound sharing is enabled
                
                # Send the screen data (and sound data if applicable) to the server
                """self.client.sendall(Protocol("SCREEN_DATA", username, {
                    "image_data": img_base64,
                }).to_str().encode('utf-8'))
                """
                self.split_and_send_screen(frame_id, img_base64)
                # Send the screen data to the server
                #self.client.sendall(Protocol("SCREEN_DATA", username, {"image_data": img_base64}).to_str().encode('utf-8'))

                # Add a small delay to avoid overloading the network
                threading.Event().wait(0.04)  # Wait for 0.5 seconds
            except Exception as e:
                logging.error(f"Error capturing or sending screen: {e}")
                raise(e)
                break

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

        if self.IN_CHAT:
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
        if self.IN_CHAT:
            messagebox.showinfo("Info", "You are already in the chat.")
            return
        self.client.send(Protocol("ENTER_CHAT", self.userinfo, {}).to_str().encode('utf-8'))

    def exit_chat(self):
        if not self.IN_CHAT:
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
        self.root.destroy()

class ChatWindow:
    def __init__(self, root, userinfo, client):
        self.root = root
        self.client = client
        self.userinfo = userinfo
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
        if self.IN_CHAT:
            self.client.send(Protocol("LEAVE_CHAT", self.userinfo, {}).to_str().encode('utf-8'))
        self.root.withdraw()  # Hide the chat window instead of destroying it
