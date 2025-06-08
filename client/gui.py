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
import tkinter.filedialog
import constants
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
        self.host_id = None  # Initialize host_id

        # Create a Notebook (tabbed interface)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Lobby Chat
        self.lobby_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.lobby_tab, text="Lobby")

        # Configure grid layout for the lobby tab
        self.lobby_tab.grid_rowconfigure(0, weight=1)  # Chat area row
        self.lobby_tab.grid_rowconfigure(1, weight=0)  # Status label row
        self.lobby_tab.grid_columnconfigure(0, weight=1)

        # Chat area for lobby messages
        self.chat_area = scrolledtext.ScrolledText(self.lobby_tab, state='disabled')
        self.chat_area.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Status label
        self.status_label = tk.Label(self.lobby_tab, text="Not in a room", fg="red")
        self.status_label.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

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

        """self.sound_share_var = tk.BooleanVar()
        self.sound_share_checkbox = tk.Checkbutton(self.screen_menu, text="Share Sound", variable=self.sound_share_var)
        self.screen_menu.add_checkbutton(label="Share Sound", variable=self.sound_share_var)"""


        # Flashing red label for screen sharing status
        self.sharing_label = tk.Label(self.lobby_tab, text="●", fg="red", font=("Arial", 14, "bold"))  # Small red dot
        self.sharing_label.place(relx=0.95, rely=0.95, anchor="se")  # Position at the bottom-right corner
        self.sharing_label.place_forget()  # Hide initially

        # Update menu states initially
        self.update_menu_states()

        # Handle window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    def refresh_members(self):
        """Refresh the list of members in the room."""
        if not self.connected_room_code:
            #clear the members frame if not in a room
            for widget in self.members_frame.winfo_children():
                widget.destroy()
            return

        # Clear the existing member labels and buttons
        """for widget in self.members_frame.winfo_children():
            widget.destroy()"""

        # Request the room status from the server
        self.client.send(Protocol("ROOM_STATUS", self.userinfo, {}).to_str().encode('utf-8'))

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

        #share_sound = self.sound_share_var.get()

        self.client.send(Protocol("START_SCREEN_SHARE", self.userinfo, {}).to_str().encode('utf-8'))
        #self.is_sharing_screen = True
        #self.client.send(Protocol("START_SCREEN_SHARE", username, {}).to_str().encode('utf-8'))
        #threading.Thread(target=self.capture_and_send_screen, daemon=True).start()

        # Show the flashing red label
        self.sharing_label.place(relx=0.95, rely=0.95, anchor="se")
        self.flash_sharing_label()

    def stop_screen_share(self):
        """Stop screen sharing."""
        self.refresh_members()
        if not self.is_sharing_screen and self.host_id != self.member_id:
            messagebox.showinfo("Info", "Screen sharing is not active.")
            return

        self.is_sharing_screen = False
        self.client.send(Protocol("STOP_SCREEN_SHARE", self.userinfo, {}).to_str().encode('utf-8'))
        self.client_udp.sendto(Protocol("STOP_SHARE", self.userinfo, {}).to_str().encode('utf-8'), self.server_udp_addr)
        self.sharing_label.place_forget()  # Hide the flashing red label

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

    def capture_and_send_share_screen(self):
        frame_id = 0
        while self.is_sharing_screen:
            frame_id += 1
            capture_and_send_screen(frame_id, self.client_udp, self.server_udp_addr, self.userinfo)
            # Add a small delay to avoid overloading the network
            threading.Event().wait(0.05)  # Wait for 0.5 seconds
        self.client_udp.sendto(Protocol("STOP_SHARE", self.userinfo, {}).to_str().encode('utf-8'), self.server_udp_addr)
    
    
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
    
    

    def update_members_list(self, host, members):
        """Update the list of members in the Room Members tab."""
        # Clear the existing member labels and buttons
        print(members)
        for widget in self.members_frame.winfo_children():
            widget.destroy()
        self.host_id = host["id"]
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
            print(f"Host ID: {self.host_id}, Member ID: {self.member_id}, Member: {member}")
            if self.host_id == self.member_id and member["id"] != self.member_id:
                kick_button = tk.Button(member_frame, text="Kick", command=lambda n=member_name, m=member_id: self.kick_member(n, m))
                kick_button.pack(side=tk.RIGHT, padx=5)

                make_host_button = tk.Button(member_frame, text="Make Host", command=lambda n=member_name, m=member_id: self.make_host(n, m))
                make_host_button.pack(side=tk.RIGHT, padx=5)
    def kick_member(self,member_name: str, member_id: str):
        """Kick a member from the room."""
        if not self.connected_room_code:
            messagebox.showinfo("Info", "You are not in a room.")
            return
        sure = messagebox.askyesno("Kick Member", f"Are you sure you sure you want to kick {member_id} - {member_name} from the room?")
        if sure:
            self.client.send(Protocol("KICK_MEMBER", self.userinfo, {"member_id": member_id}).to_str().encode('utf-8'))

    def make_host(self, member_name: str, member_id: str):
        """Make a member the host of the room."""
        if not self.connected_room_code:
            messagebox.showinfo("Info", "You are not in a room.")
            return
        sure = messagebox.askyesno("Make Host", f"Are you sure you want to make {member_id} - {member_name} the host?\nThis will transfer host privileges to them.\nYou will no longer be the host.\nIt's irreversible!")
        if sure:
            self.client.send(Protocol("MAKE_HOST", self.userinfo, {"member_id": member_id}).to_str().encode('utf-8'))

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

        self.main_frame = tk.Frame(root)

        self.main_frame = tk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        self.main_frame.grid_rowconfigure(0, weight=1)  # Chat area row
        self.main_frame.grid_rowconfigure(1, weight=0)  # Entry field row
        self.main_frame.grid_columnconfigure(0, weight=1)  # Chat area column
        self.main_frame.grid_columnconfigure(1, weight=0)  # Send File button column
        # Chat area
        self.chat_area = scrolledtext.ScrolledText(self.main_frame, state='disabled')
        self.chat_area.grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")

        # Message entry field
        self.entry_field = tk.Entry(self.main_frame)
        self.entry_field.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        #self.entry_field.pack(padx=10, pady=10, fill=tk.X)
        self.entry_field.bind("<Return>", self.send_message)

        

        original_send_file_icon = Image.open(r"D:\or\cyberProject\client\upload_icon.png")  # Replace with your icon file path
        resized_send_file_icon = original_send_file_icon.resize((25, 25), Image.Resampling.LANCZOS)
        self.send_file_icon = ImageTk.PhotoImage(resized_send_file_icon)
        # Send file button
        
        self.send_file_button = tk.Button(
            self.main_frame,
            image=self.send_file_icon,
            command=self.send_file,
            borderwidth=0,  # Optional: Remove button border
            highlightthickness=0  # Optional: Remove button highlight
        )
        self.send_file_button.grid(row=1, column=1, padx=(5, 10), pady=10, sticky="e")  # Add spacing with padx

        original_send_icon = Image.open(r"D:\or\cyberProject\client\send_icon.png")  # Replace with your icon file path
        resized_send_icon = original_send_icon.resize((25, 25), Image.Resampling.LANCZOS)
        self.send_icon = ImageTk.PhotoImage(resized_send_icon)
        # Send message button
        self.send_message_button = tk.Button(
            self.main_frame,
            image=self.send_icon,
            command=self.send_message,
            borderwidth=0,  # Optional: Remove button border
            highlightthickness=0  # Optional: Remove button highlight
        )
        self.send_message_button.grid(row=1, column=2, padx=(5, 10), pady=10, sticky="e")  # Add spacing with padx

        original_download_icon = Image.open(r"D:\or\cyberProject\client\download_icon.png")  # Replace with your icon file path
        resized_download_icon = original_download_icon.resize((25, 25), Image.Resampling.LANCZOS)  # Resize to 20x20 pixels
        self.download_icon = ImageTk.PhotoImage(resized_download_icon)

        # Download Chat History button (with icon)
        self.download_history_button = tk.Button(
            self.chat_area,
            image=self.download_icon,
            command=self.download_chat_history,
            borderwidth=0,  # Remove button border
            highlightthickness=0,  # Remove button highlight
            bg=self.chat_area["bg"],  # Match the button background to the chat area
            activebackground=self.chat_area["bg"]  # Match the active background to the chat area
        )
        self.download_history_button.place(relx=1.0, rely=0.0, anchor="ne", x=-5, y=5)  # Top-right corner inside chat area

        # Handle window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    def set_in_chat(self, in_chat):
        self.in_chat = in_chat
    def set_connected_room_code(self, room_code):
        self.connected_room_code = room_code
    def download_chat_history(self):
        """Save the chat history to a file."""
        # diffolt name is chat_history.txt
        file_path = tkinter.filedialog.asksaveasfilename(
            title="Save Chat History",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
              initialfile="chat_history.txt"  # Default file name
        )
        if not file_path:
            return  # User canceled the save dialog

        try:
            # Get the chat history from the chat area
            chat_history = self.chat_area.get("1.0", tk.END).strip()
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(chat_history)
            messagebox.showinfo("Success", f"Chat history saved to {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save chat history: {e}")
            
    def send_message(self, event=None):
        message = self.entry_field.get()
        if message:
            send_message(self.client, message, self.userinfo, self.connected_room_code)
            self.entry_field.delete(0, tk.END)
    
    def send_file(self):
        """Open file dialog and send selected file."""
        if not self.connected_room_code:
            messagebox.showinfo("Info", "You must be in a room to send files.")
            return
            
        file_path = tkinter.filedialog.askopenfilename(
            title="Select file to send",
            filetypes=[("All files", "*.*")]
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'rb') as file:
                if os.path.getsize(file_path) > constants.MAX_FILE_SIZE:  # 10 MB max file size
                    messagebox.showerror("Error", "File size exceeds the maximum limit of 10 MB.")
                    return
                if len(os.path.basename(file_path)) > constants.MAX_FILE_NAME_LENGTH:  # 255 characters max for file names
                    messagebox.showerror("Error", "File name is too long. Maximum length is 255 characters.")
                if not os.path.isfile(file_path):
                    messagebox.showerror("Error", "Selected path is not a valid file.")
                    return
                # Read file data
                file_data = file.read()
                file_name = os.path.basename(file_path)
                
                # Split file into chunks if needed
                chunk_size = 1024 * 50  # 50KB chunks
                total_chunks = (len(file_data) // chunk_size) + 1
                
                # Send file metadata first
                self.client.send(Protocol(
                    "FILE_METADATA", 
                    self.userinfo, 
                    {
                        "file_name": file_name,
                        "file_size": len(file_data),
                        "total_chunks": total_chunks
                    }
                ).to_str().encode('utf-8'))
                
                # Send file chunks
                for chunk_id in range(total_chunks):
                    chunk = file_data[chunk_id * chunk_size : (chunk_id + 1) * chunk_size]
                    self.client.send(Protocol(
                        "FILE_CHUNK",
                        self.userinfo,
                        {
                            "file_name": file_name,
                            "chunk_id": chunk_id,
                            "chunk_data": base64.b64encode(chunk).decode('utf-8')
                        }
                    ).to_str().encode('utf-8'))
                    
                self.display_message(f"{self.userinfo["username"]}: sent the file '{file_name}'")
                self.add_file_link_to_chat(file_name, file_path)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send file: {e}")  

    def display_message(self, message):
        """Display a message in the chat area."""
        self.chat_area.config(state='normal')
        self.chat_area.insert(tk.END, message + "\n")
        self.chat_area.config(state='disabled')
        self.chat_area.yview(tk.END)
    
    def add_file_link_to_chat(self, file_name, file_path):
        """Add a clickable link to the chat for the received file."""
        self.chat_area.config(state='normal')
        self.chat_area.insert(tk.END, f"File received: {file_name}\n")
        self.chat_area.insert(tk.END, f"Click here to open: {file_path}\n", ("link",))
        self.chat_area.tag_config("link", foreground="blue", underline=True)
        self.chat_area.tag_bind("link", "<Button-1>", lambda e: os.startfile(file_path))
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