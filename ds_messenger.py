# ds_messenger.py
"""Module for direct messaging in the messaging system.
Provides classes for representing and sending/receiving direct messages."""

import socket
from typing import List
from ds_protocol import DirectMessagingProtocol


class DirectMessage:
    """Represents a direct message with recipient, content, and timestamp."""
    # pylint: disable=too-few-public-methods

    def __init__(self):
        self.recipient = None  # user of the recipient
        self.message = None    # content of the message
        self.timestamp = None  # when the message was sent/received

    def is_valid(self) -> bool:
        """Check if the message has all required fields."""
        return self.message is not None


class DirectMessenger:
    """Handles direct messaging operations
    including connection, authentication,
    and message sending/retrieving."""
    # pylint: disable=too-many-instance-attributes

    def __init__(self, dsuserver=None, username=None, password=None):
        self.token = None          # auth token
        self.dsuserver = dsuserver or "127.0.0.1"
        self.username = username
        self.password = password
        self.port = 3001          # port for server connection
        # Connection components
        self.socket = None
        self.send_stream = None
        self.recv_stream = None

    def connect(self) -> bool:
        """Establish connection to the server and also authenticate"""
        try:
            # create new socket connection
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.dsuserver, self.port))

            # treat as files (so its easier)
            self.send_stream = self.socket.makefile('w')
            self.recv_stream = self.socket.makefile('r')

            # authenticate with the server
            if self.username and self.password:
                join_msg = DirectMessagingProtocol.create_join(
                    self.username, self.password)
                self.send_stream.write(join_msg + '\r\n')
                self.send_stream.flush()

                response = DirectMessagingProtocol.parse_response(
                    self.recv_stream.readline())
                if response and response.type == 'ok':
                    self.token = response.token
                    return True
            return False
        except ConnectionError as e:
            print(f"Connection error: {e}")
            self.close()
            return False
        except socket.error as e:
            print(f"Socket error: {e}")
            self.close()
            return False
        except Exception as e:  # pylint: disable=broad-except
            print(f"Unexpected error: {e}")
            self.close()
            return False

    def send(self, message: str, recipient: str) -> bool:
        """Send a direct message to another user"""
        if not self.token:
            if not self.connect():
                return False

        try:
            # create and send the direct message
            dm_msg = DirectMessagingProtocol.create_direct_message(
                self.token, message, recipient)
            self.send_stream.write(dm_msg + '\r\n')
            self.send_stream.flush()

            # get then parse the response
            response = DirectMessagingProtocol.parse_response(
                self.recv_stream.readline())
            return response and response.type == 'ok'

        except ConnectionError as e:
            print(f"Connection error while sending message: {e}")
            return False
        except socket.error as e:
            print(f"Socket error while sending message: {e}")
            return False
        except Exception as e:  # pylint: disable=broad-except
            print(f"Error sending message: {e}")
            return False

    def retrieve_new(self) -> List[DirectMessage]:
        """Retrieve new (unread) messages"""
        if not self.token:
            if not self.connect():
                return []

        try:
            # request new messages.
            request = DirectMessagingProtocol.request_unread_messages(
                self.token)
            self.send_stream.write(request + '\r\n')
            self.send_stream.flush()

            # get and parse the response
            response = DirectMessagingProtocol.parse_messages(
                self.recv_stream.readline())

            if response and response.type == 'ok':
                messages = []
                for msg in response.messages:
                    dm = DirectMessage()
                    dm.message = msg.get('message')
                    dm.recipient = msg.get('from')
                    # for received messages, note :'from' is the sender
                    dm.timestamp = msg.get('timestamp')
                    messages.append(dm)
                return messages
            return []

        except ConnectionError as e:
            print(f"Connection error while retrieving messages: {e}")
            return []
        except socket.error as e:
            print(f"Socket error while retrieving messages: {e}")
            return []
        except Exception as e:  # pylint: disable=broad-except
            print(f"Error retrieving new messages: {e}")
            return []

    def retrieve_all(self) -> List[DirectMessage]:
        """Retrieve all messages"""
        if not self.token:
            if not self.connect():
                return []

        try:
            # request all messages
            request = DirectMessagingProtocol.request_all_messages(
                self.token)
            self.send_stream.write(request + '\r\n')
            self.send_stream.flush()

            # get and parse the response
            response = DirectMessagingProtocol.parse_messages(
                self.recv_stream.readline())

            if response and response.type == 'ok':
                messages = []
                for msg in response.messages:
                    dm = DirectMessage()
                    dm.message = msg.get('message')
                    # determine if message was sent or received
                    if 'from' in msg:
                        dm.recipient = msg.get('from')
                        # msg received
                    else:
                        dm.recipient = msg.get('recipient')
                        # msg sent
                    dm.timestamp = msg.get('timestamp')
                    messages.append(dm)
                return messages
            return []

        except ConnectionError as e:
            print(f"Connection error while retrieving all messages: {e}")
            return []
        except socket.error as e:
            print(f"Socket error while retrieving all messages: {e}")
            return []
        except Exception as e:  # pylint: disable=broad-except
            print(f"Error retrieving all messages: {e}")
            return []

    def close(self):
        """Close the connection to the server"""
        try:
            if self.send_stream:
                self.send_stream.close()
            if self.recv_stream:
                self.recv_stream.close()
            if self.socket:
                self.socket.close()
        except Exception as e:  # pylint: disable=broad-except
            print(f"Error closing connection: {e}")
