# messenger.py
"""
Multi-threaded messaging application with GUI.
Features proper thread isolation, connection recovery, and offline message queuing.
"""

import threading
import queue
import logging
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import time
from enum import Enum
from typing import Optional

from ds_messenger import DirectMessenger
from database import MessageDatabase
from config import Config

# logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('messenger.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """connection states for status display."""
    CONNECTED = "Connected"
    DISCONNECTED = "Disconnected"
    RECONNECTING = "Reconnecting..."
    OFFLINE = "Offline (messages queued)"


class MessengerApp:
    """
    Main application class with multi-threaded architecture.

    Thread responsibilities:
    - Main thread: GUI operations only
    - Network thread: handles sending messages
    - Polling thread: retrieves new messages from server
    """

    def __init__(self):
        # config and database
        self.config = Config()
        self.db = MessageDatabase(self.config.db_path)

        # thread synchronization
        self.incoming_queue = queue.Queue()  # network -> gui
        self.outgoing_queue = queue.Queue()  # gui -> network
        self.stop_event = threading.Event()

        # threads
        self.network_thread: Optional[threading.Thread] = None
        self.polling_thread: Optional[threading.Thread] = None

        # connection state
        self.messenger: Optional[DirectMessenger] = None
        self.connection_state = ConnectionState.DISCONNECTED
        self.retry_count = 0
        self.backoff_time = 1

        # user state
        self.user_id: Optional[int] = None
        self.username: Optional[str] = None
        self.password: Optional[str] = None
        self.current_recipient: Optional[str] = None

        # gui setup
        self.root = tk.Tk()
        self.root.title("Messenger")
        self.root.geometry("800x600")
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)

        self._create_gui()
        self._load_last_session()

    def _create_gui(self):
        """build the gui layout."""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # left panel - contacts
        left_frame = ttk.Frame(main_frame, width=200)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        ttk.Label(left_frame, text="Contacts",
                  font=('Arial', 12, 'bold')).pack(pady=(0, 5))

        self.contacts_tree = ttk.Treeview(
            left_frame, selectmode='browse', show='tree', height=20
        )
        self.contacts_tree.pack(fill=tk.BOTH, expand=True)
        self.contacts_tree.bind('<<TreeviewSelect>>', self._on_contact_select)

        ttk.Button(left_frame, text="Add Contact",
                   command=self._add_contact).pack(pady=5, fill=tk.X)

        # right panel - messages
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # message display
        self.messages_text = tk.Text(right_frame, wrap=tk.WORD, state='disabled')
        self.messages_text.tag_configure('sent', justify='right', foreground='blue')
        self.messages_text.tag_configure('received', justify='left', foreground='green')
        self.messages_text.tag_configure('queued', justify='right', foreground='orange')
        self.messages_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # input area
        input_frame = ttk.Frame(right_frame)
        input_frame.pack(fill=tk.X)

        self.message_input = tk.Text(input_frame, height=3)
        self.message_input.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.message_input.bind('<Return>', self._on_enter)

        ttk.Button(input_frame, text="Send",
                   command=self._send_message).pack(side=tk.RIGHT, padx=(10, 0))

        # status bar
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_label = ttk.Label(status_frame, text="Disconnected")
        self.status_label.pack(side=tk.LEFT, padx=5)

        self.queue_label = ttk.Label(status_frame, text="")
        self.queue_label.pack(side=tk.RIGHT, padx=5)

        # menu
        self._create_menu()

    def _create_menu(self):
        """create the menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=self.shutdown)

        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Server Settings",
                                  command=self._show_settings)

    def _load_last_session(self):
        """try to restore last session."""
        # for now just show settings if no saved session
        # could extend to save/load last username
        self._show_settings()

    def _show_settings(self):
        """show server settings dialog."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Server Settings")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.geometry("300x250")

        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Server:").pack(pady=5)
        server_entry = ttk.Entry(frame, width=30)
        server_entry.insert(0, self.config.server)
        server_entry.pack(pady=5)

        ttk.Label(frame, text="Username:").pack(pady=5)
        username_entry = ttk.Entry(frame, width=30)
        if self.username:
            username_entry.insert(0, self.username)
        username_entry.pack(pady=5)

        ttk.Label(frame, text="Password:").pack(pady=5)
        password_entry = ttk.Entry(frame, show="*", width=30)
        if self.password:
            password_entry.insert(0, self.password)
        password_entry.pack(pady=5)

        status_label = ttk.Label(frame, text="")
        status_label.pack(pady=5)

        def on_connect():
            server = server_entry.get().strip()
            username = username_entry.get().strip()
            password = password_entry.get().strip()

            if not username or not password:
                messagebox.showerror("Error", "Username and password required")
                return

            status_label.config(text="Connecting...")
            dialog.update()

            # save settings
            self.config.set('server', server)
            self.username = username
            self.password = password

            # get or create user in db
            self.user_id = self.db.get_or_create_user(
                username, password, server
            )

            # try to connect
            if self._connect():
                dialog.destroy()
                self._refresh_contacts()
                self._start_threads()
            else:
                status_label.config(text="Connection failed - working offline")
                dialog.destroy()
                self._refresh_contacts()

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=15)

        ttk.Button(btn_frame, text="Connect",
                   command=on_connect).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel",
                   command=dialog.destroy).pack(side=tk.LEFT, padx=5)

        # center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - dialog.winfo_width()) // 2
        y = (dialog.winfo_screenheight() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

    def _connect(self) -> bool:
        """establish connection to server."""
        try:
            self.messenger = DirectMessenger(
                self.config.server,
                self.username,
                self.password
            )

            if self.messenger.connect():
                self._update_connection_state(ConnectionState.CONNECTED)
                self.retry_count = 0
                logger.info(f"Connected to server as {self.username}")
                return True

            self._update_connection_state(ConnectionState.DISCONNECTED)
            return False

        except Exception as e:
            logger.error(f"Connection error: {e}")
            self._update_connection_state(ConnectionState.DISCONNECTED)
            return False

    def _update_connection_state(self, state: ConnectionState):
        """update connection state and ui."""
        self.connection_state = state

        def update():
            color = "green" if state == ConnectionState.CONNECTED else "red"
            self.status_label.config(text=state.value, foreground=color)

        self.root.after(0, update)

    def _start_threads(self):
        """start background threads."""
        if not self.network_thread or not self.network_thread.is_alive():
            self.network_thread = threading.Thread(
                target=self._network_worker, daemon=True
            )
            self.network_thread.start()

        if not self.polling_thread or not self.polling_thread.is_alive():
            self.polling_thread = threading.Thread(
                target=self._poll_messages, daemon=True
            )
            self.polling_thread.start()

        # start gui queue processor
        self._process_incoming_queue()

    def _network_worker(self):
        """background thread for sending messages."""
        logger.info("Network worker started")

        while not self.stop_event.is_set():
            try:
                # check outgoing queue
                try:
                    msg_data = self.outgoing_queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                recipient = msg_data['recipient']
                content = msg_data['content']
                timestamp = msg_data['timestamp']
                is_retry = msg_data.get('is_retry', False)
                pending_id = msg_data.get('pending_id')

                # try to send
                if self.connection_state == ConnectionState.CONNECTED:
                    if self.messenger and self.messenger.send(content, recipient):
                        # success - save to db
                        self.db.add_message(
                            self.user_id, self.username,
                            recipient, content, timestamp
                        )
                        if pending_id:
                            self.db.mark_pending_sent(pending_id)

                        self.incoming_queue.put({
                            'type': 'sent_success',
                            'recipient': recipient
                        })
                        logger.info(f"Sent message to {recipient}")
                    else:
                        # send failed - queue for retry
                        self._handle_send_failure(msg_data)
                else:
                    # offline - queue the message
                    if not is_retry:
                        self.db.add_pending_message(
                            self.user_id, recipient, content, timestamp
                        )
                        logger.info(f"Queued offline message to {recipient}")

            except Exception as e:
                logger.error(f"Network worker error: {e}")

    def _handle_send_failure(self, msg_data):
        """handle failed message send."""
        if not msg_data.get('is_retry'):
            self.db.add_pending_message(
                self.user_id,
                msg_data['recipient'],
                msg_data['content'],
                msg_data['timestamp']
            )

        self._update_connection_state(ConnectionState.DISCONNECTED)
        self._try_reconnect()

    def _try_reconnect(self):
        """attempt to reconnect with exponential backoff."""
        if self.retry_count >= self.config.max_retries:
            self._update_connection_state(ConnectionState.OFFLINE)
            return

        self._update_connection_state(ConnectionState.RECONNECTING)

        backoff = min(self.backoff_time * (2 ** self.retry_count), 60)
        time.sleep(backoff)

        self.retry_count += 1
        logger.info(f"Reconnection attempt {self.retry_count}")

        if self._connect():
            self._flush_pending_messages()

    def _flush_pending_messages(self):
        """send queued messages after reconnection."""
        pending = self.db.get_pending_messages(self.user_id)

        for msg in pending:
            self.outgoing_queue.put({
                'recipient': msg['recipient'],
                'content': msg['content'],
                'timestamp': msg['timestamp'],
                'is_retry': True,
                'pending_id': msg['pending_id']
            })

        logger.info(f"Flushing {len(pending)} pending messages")

    def _poll_messages(self):
        """background thread for polling new messages."""
        logger.info("Polling thread started")

        while not self.stop_event.is_set():
            try:
                if (self.connection_state == ConnectionState.CONNECTED
                        and self.messenger):
                    new_messages = self.messenger.retrieve_new()

                    for msg in new_messages:
                        # extract message data
                        if hasattr(msg, 'message'):
                            content = msg.message
                            sender = msg.recipient  # 'recipient' field contains sender for received msgs
                            timestamp = msg.timestamp
                        else:
                            content = msg.get('message')
                            sender = msg.get('from')
                            timestamp = msg.get('timestamp')

                        if content and sender:
                            # save to db
                            self.db.add_message(
                                self.user_id, sender,
                                self.username, content,
                                float(timestamp) if timestamp else time.time()
                            )

                            # notify gui
                            self.incoming_queue.put({
                                'type': 'new_message',
                                'sender': sender,
                                'content': content
                            })

                time.sleep(self.config.poll_interval)

            except Exception as e:
                logger.error(f"Polling error: {e}")
                if self.connection_state == ConnectionState.CONNECTED:
                    self._update_connection_state(ConnectionState.DISCONNECTED)
                    self._try_reconnect()
                time.sleep(5)

    def _process_incoming_queue(self):
        """process messages from background threads (runs in main thread)."""
        try:
            while True:
                msg = self.incoming_queue.get_nowait()

                if msg['type'] == 'new_message':
                    self._refresh_contacts()
                    if self.current_recipient == msg['sender']:
                        self._display_messages()

                elif msg['type'] == 'sent_success':
                    if self.current_recipient == msg['recipient']:
                        self._display_messages()

        except queue.Empty:
            pass

        # update pending count
        if self.user_id:
            pending = self.db.get_pending_messages(self.user_id)
            if pending:
                self.queue_label.config(text=f"{len(pending)} queued")
            else:
                self.queue_label.config(text="")

        # schedule next check
        if not self.stop_event.is_set():
            self.root.after(100, self._process_incoming_queue)

    def _on_contact_select(self, event=None):
        """handle contact selection."""
        selection = self.contacts_tree.selection()
        if selection:
            self.current_recipient = self.contacts_tree.item(selection[0])['text']
            self._display_messages()

    def _display_messages(self):
        """display messages for selected contact."""
        if not self.current_recipient or not self.user_id:
            return

        self.messages_text.config(state='normal')
        self.messages_text.delete(1.0, tk.END)

        messages = self.db.get_messages(self.user_id, self.current_recipient)

        for msg in messages:
            sender = msg['sender']
            content = msg['content']

            if sender == self.username:
                self.messages_text.insert(tk.END, "You: ", 'sent')
                self.messages_text.insert(tk.END, f"{content}\n")
            else:
                self.messages_text.insert(tk.END, f"{sender}: ", 'received')
                self.messages_text.insert(tk.END, f"{content}\n")

        self.messages_text.config(state='disabled')
        self.messages_text.see(tk.END)

    def _send_message(self):
        """queue a message for sending."""
        if not self.current_recipient:
            messagebox.showwarning("Warning", "Select a recipient first")
            return

        content = self.message_input.get(1.0, tk.END).strip()
        if not content:
            return

        msg_data = {
            'recipient': self.current_recipient,
            'content': content,
            'timestamp': time.time()
        }

        self.outgoing_queue.put(msg_data)
        self.message_input.delete(1.0, tk.END)

        # show message immediately (optimistic ui)
        self.messages_text.config(state='normal')
        tag = 'sent' if self.connection_state == ConnectionState.CONNECTED else 'queued'
        self.messages_text.insert(tk.END, "You: ", tag)
        self.messages_text.insert(tk.END, f"{content}\n")
        self.messages_text.config(state='disabled')
        self.messages_text.see(tk.END)

    def _on_enter(self, event):
        """handle enter key."""
        if not event.state & 0x1:  # shift not pressed
            self._send_message()
            return 'break'
        return None

    def _add_contact(self):
        """add a new contact."""
        username = simpledialog.askstring(
            "Add Contact", "Enter username:", parent=self.root
        )
        if username and username.strip() and self.user_id:
            self.db.add_contact(self.user_id, username.strip())
            self._refresh_contacts()

    def _refresh_contacts(self):
        """refresh contacts list from database."""
        if not self.user_id:
            return

        self.contacts_tree.delete(*self.contacts_tree.get_children())
        contacts = self.db.get_contacts(self.user_id)

        for contact in contacts:
            self.contacts_tree.insert('', 'end', text=contact)

    def shutdown(self):
        """graceful shutdown."""
        logger.info("Shutting down...")

        # signal threads to stop
        self.stop_event.set()

        # wait for threads
        if self.network_thread and self.network_thread.is_alive():
            self.network_thread.join(timeout=2)
        if self.polling_thread and self.polling_thread.is_alive():
            self.polling_thread.join(timeout=2)

        # close network connection
        if self.messenger:
            self.messenger.close()

        logger.info("Shutdown complete")
        self.root.destroy()

    def run(self):
        """start the application."""
        self.root.mainloop()


def main():
    """entry point."""
    app = MessengerApp()
    app.run()


if __name__ == "__main__":
    main()
