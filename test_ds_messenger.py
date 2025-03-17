# test_ds_messenger.py
"""Test module for the DS Messenger functionality.."""

import time
import unittest
import socket
import json
from unittest.mock import patch, MagicMock, mock_open
from ds_messenger import DirectMessenger, DirectMessage


class TestDirectMessage(unittest.TestCase):
    # -@patch for mock objects, magic optional 
    # (assume not running)
    """Test cases for the DirectMessage class."""
    
    def test_direct_message_creation(self):
        """creating a DirectMessage instance"""
        dm = DirectMessage()
        self.assertIsNone(dm.recipient)
        self.assertIsNone(dm.message)
        self.assertIsNone(dm.timestamp)
    
    def test_is_valid(self):
        """the is_valid method"""
        dm = DirectMessage()
        self.assertFalse(dm.is_valid())
        
        dm.message = "Test message"
        self.assertTrue(dm.is_valid())
        
        dm.recipient = "recipient"
        self.assertTrue(dm.is_valid())
        
        dm.timestamp = "1234567890"
        self.assertTrue(dm.is_valid())
        
        dm.message = None
        self.assertFalse(dm.is_valid())


class TestDirectMessenger(unittest.TestCase):
    """Test cases for the DirectMessenger class."""

    def setUp(self):
        """Setting up the test info"""
        # creating the usernames for tests
        timestamp = str(int(time.time()))
        self.test_user1 = {
            'username': f'testuser1_{timestamp}',
            'password': 'testpass1'
        }
        self.test_user2 = {
            'username': f'testuser2_{timestamp}',
            'password': 'testpass2'
        }

        print("\nCreating test users:")
        print(f"User1: {self.test_user1['username']}")
        print(f"User2: {self.test_user2['username']}")

        # create messenger instances
        self.messenger1 = DirectMessenger(
            username=self.test_user1['username'],
            password=self.test_user1['password']
        )
        self.messenger2 = DirectMessenger(
            username=self.test_user2['username'],
            password=self.test_user2['password']
        )

    def test_init(self):
        """Test DirectMessenger"""
        messenger = DirectMessenger(
            dsuserver="test.server",
            username="testuser",
            password="testpass"
        )
        self.assertIsNone(messenger.token)
        self.assertEqual(messenger.dsuserver, "test.server")
        self.assertEqual(messenger.username, "testuser")
        self.assertEqual(messenger.password, "testpass")
        self.assertEqual(messenger.port, 3001)
        self.assertIsNone(messenger.socket)
        self.assertIsNone(messenger.send_stream)
        self.assertIsNone(messenger.recv_stream)
        
        # test with default server
        messenger = DirectMessenger(
            username="testuser",
            password="testpass"
        )
        self.assertEqual(messenger.dsuserver, "127.0.0.1")
    
    def test_connect_authentication_failure(self):
        """connect method with auth failure"""
        with patch('socket.socket') as mock_socket:
            mock_recv = MagicMock()
            mock_send = MagicMock()
            
            # set up the mock to return an error response
            mock_recv.readline.return_value = '{"response": {"type": "error", "message": "Invalid credentials"}}'
            mock_socket.return_value.makefile.side_effect = [mock_recv, mock_send]
            
            messenger = DirectMessenger(
                username="testuser",
                password="testpass"
            )
            result = messenger.connect()
            self.assertFalse(result)
            self.assertIsNone(messenger.token)

    def test_connect_connection_error(self):
        """connect method - ConnectionError"""
        with patch('socket.socket') as mock_socket:
            mock_socket.return_value.connect.side_effect = ConnectionError("Connection error")
            
            messenger = DirectMessenger(
                username="testuser",
                password="testpass"
            )
            result = messenger.connect()
            self.assertFalse(result)
            
    def test_connect_socket_error(self):
        """connect method handling a socket.error"""
        with patch('socket.socket') as mock_socket:
            mock_socket.return_value.connect.side_effect = socket.error("Socket error")
            
            messenger = DirectMessenger(
                username="testuser",
                password="testpass"
            )
            result = messenger.connect()
            self.assertFalse(result)
    
    def test_connect_general_exception(self):
        """connect method handling (general) exceptions"""
        with patch('socket.socket') as mock_socket:
            mock_socket.return_value.connect.side_effect = Exception("General error")
            
            messenger = DirectMessenger(
                username="testuser",
                password="testpass"
            )
            result = messenger.connect()
            self.assertFalse(result)
    
    def test_connect_without_credentials(self):
        """connect method without any creds."""
        with patch('socket.socket') as mock_socket:
            mock_recv = MagicMock()
            mock_send = MagicMock()
            mock_socket.return_value.makefile.side_effect = [mock_recv, mock_send]
            
            messenger = DirectMessenger()
            result = messenger.connect()
            self.assertFalse(result)

    def test_connection_failure(self):
        """Test - connection failure"""
        with patch('socket.socket') as mock_socket:
            mock_socket.return_value.connect.side_effect = socket.error("Connection refused")
            
            messenger = DirectMessenger(
                username="testuser",
                password="testpass"
            )
            result = messenger.connect()
            self.assertFalse(result)
            self.assertIsNone(messenger.token)

    def test_send_without_token(self):
        """Test send method without a  token"""
        with patch.object(DirectMessenger, 'connect', return_value=False):
            messenger = DirectMessenger()
            result = messenger.send("Test message", "recipient")
            self.assertFalse(result)

    @patch('socket.socket')
    def test_send_with_token(self, mock_socket):
        """Test send method with a token"""
        mock_recv = MagicMock()
        mock_send = MagicMock()
        
        mock_recv.readline.return_value = '{"response": {"type": "ok", "message": "Direct message sent"}}'
        
        mock_socket.return_value.makefile.side_effect = [mock_recv, mock_send]
        
        messenger = DirectMessenger()
        messenger.token = "test_token"
        messenger.socket = mock_socket.return_value
        messenger.recv_stream = mock_recv
        messenger.send_stream = mock_send
        
        result = messenger.send("Test message", "recipient")
        self.assertTrue(result)
        
        mock_send.write.assert_called_once()
        mock_send.flush.assert_called_once()
    
    @patch('socket.socket')
    def test_send_error_response(self, mock_socket):
        """Test send method with error response"""
        mock_recv = MagicMock()
        mock_send = MagicMock()
        
        mock_recv.readline.return_value = '{"response": {"type": "error", "message": "Error sending message"}}'
        
        mock_socket.return_value.makefile.side_effect = [mock_recv, mock_send]
        
        messenger = DirectMessenger()
        messenger.token = "test_token"
        messenger.socket = mock_socket.return_value
        messenger.recv_stream = mock_recv
        messenger.send_stream = mock_send
        
        result = messenger.send("Test message", "recipient")
        self.assertFalse(result)
    
    @patch('socket.socket')
    def test_send_connection_error(self, mock_socket):
        """Test send method for ConnectionError"""
        mock_recv = MagicMock()
        mock_send = MagicMock()
        
        mock_send.write.side_effect = ConnectionError("Connection error")
        
        mock_socket.return_value.makefile.side_effect = [mock_recv, mock_send]
        
        messenger = DirectMessenger()
        messenger.token = "test_token"
        messenger.socket = mock_socket.return_value
        messenger.recv_stream = mock_recv
        messenger.send_stream = mock_send
        
        result = messenger.send("Test message", "recipient")
        self.assertFalse(result)
    
    @patch('socket.socket')
    def test_send_socket_error(self, mock_socket):
        """Test send method for socket.error"""
        mock_recv = MagicMock()
        mock_send = MagicMock()
        
        mock_send.write.side_effect = socket.error("Socket error")
        
        mock_socket.return_value.makefile.side_effect = [mock_recv, mock_send]
        
        messenger = DirectMessenger()
        messenger.token = "test_token"
        messenger.socket = mock_socket.return_value
        messenger.recv_stream = mock_recv
        messenger.send_stream = mock_send
        
        result = messenger.send("Test message", "recipient")
        self.assertFalse(result)
    
    @patch('socket.socket')
    def test_send_general_exception(self, mock_socket):
        """Test send method for (general) exceptions"""
        mock_recv = MagicMock()
        mock_send = MagicMock()
        
        mock_send.write.side_effect = Exception("General error")
        
        mock_socket.return_value.makefile.side_effect = [mock_recv, mock_send]
        
        messenger = DirectMessenger()
        messenger.token = "test_token"
        messenger.socket = mock_socket.return_value
        messenger.recv_stream = mock_recv
        messenger.send_stream = mock_send
        
        result = messenger.send("Test message", "recipient")
        self.assertFalse(result)
            
    @patch('socket.socket')
    def test_retrieve_new_messages(self, mock_socket):
        """Test retrieving naynew messages"""
        mock_recv = MagicMock()
        mock_send = MagicMock()
        
        mock_recv.readline.return_value = (
            '{"response": {"type": "ok", "messages": ['
            '{"message": "Test message", "from": "sender", "timestamp": "1234567890"}'
            ']}}'
        )
        
        mock_socket.return_value.makefile.side_effect = [mock_recv, mock_send]
        
        messenger = DirectMessenger()
        messenger.token = "test_token"
        messenger.socket = mock_socket.return_value
        messenger.recv_stream = mock_recv
        messenger.send_stream = mock_send
        
        messages = messenger.retrieve_new()
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].message, "Test message")
        self.assertEqual(messages[0].recipient, "sender")
        self.assertEqual(messages[0].timestamp, "1234567890")
        
        mock_send.write.assert_called_once()
        mock_send.flush.assert_called_once()
    
    @patch('socket.socket')
    def test_retrieve_new_messages_error_response(self, mock_socket):
        """Test retrieving new messages w/ error response"""
        mock_recv = MagicMock()
        mock_send = MagicMock()
        
        mock_recv.readline.return_value = '{"response": {"type": "error", "message": "Error retrieving messages"}}'
        
        mock_socket.return_value.makefile.side_effect = [mock_recv, mock_send]
        
        messenger = DirectMessenger()
        messenger.token = "test_token"
        messenger.socket = mock_socket.return_value
        messenger.recv_stream = mock_recv
        messenger.send_stream = mock_send
        
        messages = messenger.retrieve_new()
        self.assertEqual(len(messages), 0)

    @patch('socket.socket')
    def test_retrieve_new_connection_error(self, mock_socket):
        """Test retrieving new messages ConnectionError"""
        mock_recv = MagicMock()
        mock_send = MagicMock()
        
        mock_send.write.side_effect = ConnectionError("Connection error")
        
        mock_socket.return_value.makefile.side_effect = [mock_recv, mock_send]
        
        messenger = DirectMessenger()
        messenger.token = "test_token"
        messenger.socket = mock_socket.return_value
        messenger.recv_stream = mock_recv
        messenger.send_stream = mock_send
        
        messages = messenger.retrieve_new()
        self.assertEqual(len(messages), 0)
    
    @patch('socket.socket')
    def test_retrieve_new_socket_error(self, mock_socket):
        """Test retrieving new messages for socket.error"""
        mock_recv = MagicMock()
        mock_send = MagicMock()
        
        mock_send.write.side_effect = socket.error("Socket error")
        
        mock_socket.return_value.makefile.side_effect = [mock_recv, mock_send]
        
        messenger = DirectMessenger()
        messenger.token = "test_token"
        messenger.socket = mock_socket.return_value
        messenger.recv_stream = mock_recv
        messenger.send_stream = mock_send
        
        messages = messenger.retrieve_new()
        self.assertEqual(len(messages), 0)
    
    @patch('socket.socket')
    def test_retrieve_new_general_exception(self, mock_socket):
        """Test retrieving new messages for any genealexceptions"""
        mock_recv = MagicMock()
        mock_send = MagicMock()
        
        mock_send.write.side_effect = Exception("General error")
        
        mock_socket.return_value.makefile.side_effect = [mock_recv, mock_send]
        
        messenger = DirectMessenger()
        messenger.token = "test_token"
        messenger.socket = mock_socket.return_value
        messenger.recv_stream = mock_recv
        messenger.send_stream = mock_send
        
        messages = messenger.retrieve_new()
        self.assertEqual(len(messages), 0)

    @patch('socket.socket')
    def test_retrieve_all_messages(self, mock_socket):
        """Test retrieving all messages.."""
        mock_recv = MagicMock()
        mock_send = MagicMock()
        
        mock_recv.readline.return_value = (
            '{"response": {"type": "ok", "messages": ['
            '{"message": "Incoming", "from": "sender", "timestamp": "1234567890"},'
            '{"message": "Outgoing", "recipient": "recipient", "timestamp": "1234567891"}'
            ']}}'
        )
        
        mock_socket.return_value.makefile.side_effect = [mock_recv, mock_send]
        
        messenger = DirectMessenger()
        messenger.token = "test_token"
        messenger.socket = mock_socket.return_value
        messenger.recv_stream = mock_recv
        messenger.send_stream = mock_send
        
        messages = messenger.retrieve_all()
        self.assertEqual(len(messages), 2)
        # check the first message (received)
        self.assertEqual(messages[0].message, "Incoming")
        self.assertEqual(messages[0].recipient, "sender")
        self.assertEqual(messages[0].timestamp, "1234567890")
        # check the second message (sent)
        self.assertEqual(messages[1].message, "Outgoing")
        self.assertEqual(messages[1].recipient, "recipient")
        self.assertEqual(messages[1].timestamp, "1234567891")
        
        mock_send.write.assert_called_once()
        mock_send.flush.assert_called_once()
    
    @patch('socket.socket')
    def test_retrieve_all_messages_error_response(self, mock_socket):
        """Test retrieving all messages with an error response"""
        mock_recv = MagicMock()
        mock_send = MagicMock()
        
        mock_recv.readline.return_value = '{"response": {"type": "error", "message": "Error retrieving messages"}}'
        
        mock_socket.return_value.makefile.side_effect = [mock_recv, mock_send]
        
        messenger = DirectMessenger()
        messenger.token = "test_token"
        messenger.socket = mock_socket.return_value
        messenger.recv_stream = mock_recv
        messenger.send_stream = mock_send
        
        messages = messenger.retrieve_all()
        self.assertEqual(len(messages), 0)
    
    @patch('socket.socket')
    def test_retrieve_all_connection_error(self, mock_socket):
        """Test retrieving all messages -- ConnectionError"""
        mock_recv = MagicMock()
        mock_send = MagicMock()
        
        mock_send.write.side_effect = ConnectionError("Connection error")
        
        mock_socket.return_value.makefile.side_effect = [mock_recv, mock_send]
        
        messenger = DirectMessenger()
        messenger.token = "test_token"
        messenger.socket = mock_socket.return_value
        messenger.recv_stream = mock_recv
        messenger.send_stream = mock_send
        
        messages = messenger.retrieve_all()
        self.assertEqual(len(messages), 0)
    
    @patch('socket.socket')
    def test_retrieve_all_socket_error(self, mock_socket):
        """Test retrieving all messages -- socket.error"""
        mock_recv = MagicMock()
        mock_send = MagicMock()
        
        mock_send.write.side_effect = socket.error("Socket error")
        
        mock_socket.return_value.makefile.side_effect = [mock_recv, mock_send]
        
        messenger = DirectMessenger()
        messenger.token = "test_token"
        messenger.socket = mock_socket.return_value
        messenger.recv_stream = mock_recv
        messenger.send_stream = mock_send
        
        messages = messenger.retrieve_all()
        self.assertEqual(len(messages), 0)
    
    @patch('socket.socket')
    def test_retrieve_all_general_exception(self, mock_socket):
        """Test retrieving all messages just with general exceptions"""
        mock_recv = MagicMock()
        mock_send = MagicMock()
        
        mock_send.write.side_effect = Exception("General error")
        
        mock_socket.return_value.makefile.side_effect = [mock_recv, mock_send]
        
        messenger = DirectMessenger()
        messenger.token = "test_token"
        messenger.socket = mock_socket.return_value
        messenger.recv_stream = mock_recv
        messenger.send_stream = mock_send
        
        messages = messenger.retrieve_all()
        self.assertEqual(len(messages), 0)

    def test_retrieve_without_token(self):
        """Test retrieving messages without a token"""
        # test retrieve_new
        with patch.object(DirectMessenger, 'connect', return_value=False):
            messenger = DirectMessenger()
            messages = messenger.retrieve_new()
            self.assertEqual(len(messages), 0)
        
        # test retrieve_all
        with patch.object(DirectMessenger, 'connect', return_value=False):
            messenger = DirectMessenger()
            messages = messenger.retrieve_all()
            self.assertEqual(len(messages), 0)

    @patch('socket.socket')
    def test_retrieve_messages_error_handling(self, mock_socket):
        """Test error handling in the retrieve methods"""
        mock_recv = MagicMock()
        mock_send = MagicMock()
        
        mock_recv.readline.side_effect = ConnectionError("Connection lost")
        
        mock_socket.return_value.makefile.side_effect = [mock_recv, mock_send]
        
        messenger = DirectMessenger()
        messenger.token = "test_token"
        messenger.socket = mock_socket.return_value
        messenger.recv_stream = mock_recv
        messenger.send_stream = mock_send
        
        # test retrieve_new error handling
        messages = messenger.retrieve_new()
        self.assertEqual(len(messages), 0)
        
        # reset the mock
        mock_recv.readline.side_effect = ConnectionError("Connection lost")
        
        # test retrieve_all error handling
        messages = messenger.retrieve_all()
        self.assertEqual(len(messages), 0)

    def test_close(self):
        """Test the close method"""
        mock_socket = MagicMock()
        mock_send = MagicMock()
        mock_recv = MagicMock()
        
        messenger = DirectMessenger()
        messenger.socket = mock_socket
        messenger.send_stream = mock_send
        messenger.recv_stream = mock_recv
        
        messenger.close()
        
        mock_send.close.assert_called_once()
        mock_recv.close.assert_called_once()
        mock_socket.close.assert_called_once()
        
        # test exception handling
        mock_send.close.side_effect = Exception("Error closing stream")
        messenger.close()  # Should not raise an exception

    def test_close_with_exception(self):
        """Test close method with some exception handling"""
        mock_socket = MagicMock()
        mock_send = MagicMock()
        mock_recv = MagicMock()
        
        # set up the mocks to raise exceptions
        mock_send.close.side_effect = Exception("Error closing send stream")
        mock_recv.close.side_effect = Exception("Error closing recv stream")
        mock_socket.close.side_effect = Exception("Error closing socket")
        
        messenger = DirectMessenger()
        messenger.socket = mock_socket
        messenger.send_stream = mock_send
        messenger.recv_stream = mock_recv
        
        # this should NOT raise an exception
        messenger.close()

    def test_connection(self):
        """Test connection to server"""
        try:
            print("\nTesting connection...")
            result = self.messenger1.connect()
            if not result:
                print(f"Connection failed for {self.test_user1['username']}")
            self.assertTrue(result)
            self.assertIsNotNone(self.messenger1.token)
        except (socket.error, ConnectionError):
            print("Server not available, skipping integration test")
            self.skipTest("Server not available")

    def test_send_message(self):
        """Test sending a message"""
        try:
            print("\nTesting message sending...")
            # firstly, connect both users
            print("Connecting user2...")
            self.assertTrue(self.messenger2.connect())
            print("Connecting user1...")
            self.assertTrue(self.messenger1.connect())

            # send a message from user1 to user2
            message = "Hello, this is a test message!"
            print(f"Sending message: {message}")
            success = self.messenger1.send(message, self.test_user2['username'])
            self.assertTrue(success)
        except (socket.error, ConnectionError):
            print("Server not available, skipping integration test")
            self.skipTest("Server not available")

    def test_retrieve_new_messages(self):
        """Test retrieving new messages"""
        try:
            print("\nTesting new message retrieval...")
            # first connect both users
            print("Connecting users...")
            self.assertTrue(self.messenger2.connect())
            self.assertTrue(self.messenger1.connect())

            # send a message from user1 to user2
            message = "Test message for new messages"
            print(f"Sending message: {message}")
            self.messenger1.send(message, self.test_user2['username'])

            # wait briefly for message to be processed
            time.sleep(1)

            # retrieve the new messages for user2
            print("Retrieving new messages...")
            messages = self.messenger2.retrieve_new()
            self.assertGreater(len(messages), 0)
            self.assertEqual(messages[0].message, message)
        except (socket.error, ConnectionError):
            print("Server not available, skipping integration test")
            self.skipTest("Server not available")

    def test_retrieve_all_messages(self):
        """Test retrieving all messages"""
        try:
            print("\nTesting all messages retrieval...")
            # first connect both users
            print("Connecting users...")
            self.assertTrue(self.messenger2.connect())
            self.assertTrue(self.messenger1.connect())

            # send a message from user1 to user2
            message = "Test message for all messages"
            print(f"Sending message: {message}")
            self.messenger1.send(message, self.test_user2['username'])

            # wait briefly for message to be processed
            time.sleep(1)

            # retrieve all messages for both users
            print("Retrieving all messages...")
            messages1 = self.messenger1.retrieve_all()
            messages2 = self.messenger2.retrieve_all()

            self.assertGreater(len(messages1), 0)
            self.assertGreater(len(messages2), 0)
        except (socket.error, ConnectionError):
            print("Server not available, skipping integration test")
            self.skipTest("Server not available")

    def tearDown(self):
        """Cleaning up after each test"""
        if hasattr(self, 'messenger1') and self.messenger1:
            self.messenger1.close()
        if hasattr(self, 'messenger2') and self.messenger2:
            self.messenger2.close()


if __name__ == '__main__':
    print("Make sure the server is running on "
          "port 3001 before starting tests!")
    unittest.main(verbosity=2)
