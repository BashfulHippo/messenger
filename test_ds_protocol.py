# test_ds_protocol.py
"""Test module for the the Protocol implementation."""

import unittest
import unittest.mock as mock
import socket
import time
import json
from ds_protocol import DirectMessagingProtocol, ServerResponse, MessageResponse


class TestDirectMessagingProtocol(unittest.TestCase):
    """Test cases for the DirectMessagingProtocol class."""

    def setUp(self):
        self.protocol = DirectMessagingProtocol()
        self.server_host = '127.0.0.1'
        self.server_port = 3001
        # adding timestamps to usernames to make them unique for each test run
        timestamp = str(int(time.time()))
        self.test_user1 = {'username': f'testuser1_{timestamp}',
                           'password': 'testpass1'}
        self.test_user2 = {'username': f'testuser2_{timestamp}',
                           'password': 'testpass2'}
        self.socket = None
        self.token = None

    def test_create_join(self):
        """join message"""
        join_msg = self.protocol.create_join(
            self.test_user1['username'],
            self.test_user1['password']
        )
        # parse the message to ensure it's a valid JSON
        json_obj = json.loads(join_msg)
        self.assertIn('join', json_obj)
        self.assertEqual(json_obj['join']['username'], self.test_user1['username'])
        self.assertEqual(json_obj['join']['password'], self.test_user1['password'])
        self.assertEqual(json_obj['join']['token'], "")

    def test_create_direct_message(self):
        """direct message"""
        token = "test_token"
        message = "Test message"
        recipient = "test_recipient"
        dm_msg = self.protocol.create_direct_message(token, message, recipient)
        
        # parse and validate the message
        json_obj = json.loads(dm_msg)
        self.assertEqual(json_obj['token'], token)
        self.assertIn('directmessage', json_obj)
        self.assertEqual(json_obj['directmessage']['entry'], message)
        self.assertEqual(json_obj['directmessage']['recipient'], recipient)
        self.assertIsNotNone(json_obj['directmessage']['timestamp'])

    def test_request_unread_messages(self):
        """Creating a request for unread messages"""
        token = "test_token"
        request_msg = self.protocol.request_unread_messages(token)
        
        # parse and validate the message
        json_obj = json.loads(request_msg)
        self.assertEqual(json_obj['token'], token)
        self.assertEqual(json_obj['directmessage'], "new")

    def test_request_all_messages(self):
        """Creatin a request for all messages"""
        token = "test_token"
        request_msg = self.protocol.request_all_messages(token)
        
        # parse and validate the message
        json_obj = json.loads(request_msg)
        self.assertEqual(json_obj['token'], token)
        self.assertEqual(json_obj['directmessage'], "all")

    def test_parse_response_success(self):
        """A successful server response"""
        json_msg = '{"response": {"type": "ok", "message": "Join successful", "token": "test_token"}}'
        response = self.protocol.parse_response(json_msg)
        self.assertIsNotNone(response)
        self.assertEqual(response.type, "ok")
        self.assertEqual(response.message, "Join successful")
        self.assertEqual(response.token, "test_token")

    def test_parse_response_error(self):
        """An error server response"""
        json_msg = '{"response": {"type": "error", "message": "Invalid username or password"}}'
        response = self.protocol.parse_response(json_msg)
        self.assertIsNotNone(response)
        self.assertEqual(response.type, "error")
        self.assertEqual(response.message, "Invalid username or password")
        self.assertEqual(response.token, "")

    def test_parse_response_invalid_json(self):
        """An invalid JSON response"""
        json_msg = 'not valid json'
        response = self.protocol.parse_response(json_msg)
        self.assertIsNone(response)

    def test_parse_response_missing_key(self):
        """A response with missing key"""
        json_msg = '{"invalid_key": {}}'
        response = self.protocol.parse_response(json_msg)
        self.assertIsNone(response)
        
    def test_parse_response_missing_response_key(self):
        """A response without 'response' key"""
        json_msg = '{"some_other_key": {}}'
        response = self.protocol.parse_response(json_msg)
        self.assertIsNone(response)
        
    def test_parse_response_key_error(self):
        """KeyError (doesn't seem to be raised despite all efforts, so
        a custom override seems to be necessary to manually create the
        error."""
        # mock json.loads to return a dict with a response that raises KeyError.
        original_loads = json.loads
        
        def mock_loads(s):
            resp_dict = {}
            
            # creates a special dict that should raise KeyError when accessed
            class CustomDict(dict):
                def get(self, key, default=None):
                    raise KeyError(key)
            
            resp_dict['response'] = CustomDict()
            return resp_dict
        
        # applying the mock
        json.loads = mock_loads
        
        try:
            response = self.protocol.parse_response('{"response": {}}')
            self.assertIsNone(response)
        finally:
            # Restore original function
            json.loads = original_loads

    def test_parse_messages_key_error(self):
        """KeyError"""
        # mock json.loads to return a dict with a response that raises KeyError
        original_loads = json.loads
        
        def mock_loads(s):
            resp_dict = {}
            
            # create a special dict that will raise KeyError when accessed
            class CustomDict(dict):
                def get(self, key, default=None):
                    raise KeyError(key)
            
            resp_dict['response'] = CustomDict()
            return resp_dict
        
        # applying the mock
        json.loads = mock_loads
        
        try:
            response = self.protocol.parse_messages('{"response": {}}')
            self.assertIsNone(response)
        finally:
            # restoring the original function
            json.loads = original_loads
        
    def test_parse_response_attribute_error(self):
        """AttributeError"""
        json_msg = '{"response": null}'
        response = self.protocol.parse_response(json_msg)
        self.assertIsNone(response)
        
    def test_parse_response_general_exception(self):
        """General exception"""
        # patching json.loads to raise an exception..
        original_loads = json.loads
        
        def mock_loads(s):
            if s == 'general_exception_test':
                raise Exception("Unexpected error")
            return original_loads(s)
            
        json.loads = mock_loads
        try:
            response = self.protocol.parse_response('general_exception_test')
            self.assertIsNone(response)
        finally:
            json.loads = original_loads

    def test_parse_messages_success(self):
        """A successful message response"""
        json_msg = '{"response": {"type": "ok", "messages": [{"message": "Test message", "from": "sender", "timestamp": "1234567890"}]}}'
        response = self.protocol.parse_messages(json_msg)
        self.assertIsNotNone(response)
        self.assertEqual(response.type, "ok")
        self.assertEqual(len(response.messages), 1)
        self.assertEqual(response.messages[0]["message"], "Test message")
        self.assertEqual(response.messages[0]["from"], "sender")
        self.assertEqual(response.messages[0]["timestamp"], "1234567890")

    def test_parse_messages_empty(self):
        """Response with NO messages"""
        json_msg = '{"response": {"type": "ok", "messages": []}}'
        response = self.protocol.parse_messages(json_msg)
        self.assertIsNotNone(response)
        self.assertEqual(response.type, "ok")
        self.assertEqual(len(response.messages), 0)

    def test_parse_messages_invalid_json(self):
        """An invalid JSON message response"""
        json_msg = 'not valid json'
        response = self.protocol.parse_messages(json_msg)
        self.assertIsNone(response)

    def test_parse_messages_missing_key(self):
        """A msg with missing key"""
        json_msg = '{"invalid_key": {}}'
        response = self.protocol.parse_messages(json_msg)
        self.assertIsNone(response)
        
    def test_parse_messages_missing_response_key(self):
        """A msg without 'response' key"""
        json_msg = '{"some_other_key": {}}'
        response = self.protocol.parse_messages(json_msg)
        self.assertIsNone(response)
        
    def test_parse_messages_attribute_error(self):
        """For AttributeError"""
        json_msg = '{"response": null}'
        response = self.protocol.parse_messages(json_msg)
        self.assertIsNone(response)
        
    def test_parse_messages_general_exception(self):
        """parsing a message response that causes a (general) exception"""
        original_loads = json.loads
        
        def mock_loads(s):
            if s == 'general_exception_test':
                raise Exception("Unexpected error")
            return original_loads(s)
            
        json.loads = mock_loads
        try:
            response = self.protocol.parse_messages('general_exception_test')
            self.assertIsNone(response)
        finally:
            json.loads = original_loads

    def connect_to_server(self):
        """a method to connect to the server"""
        try:
            self.socket = socket.socket(socket.AF_INET,
                                        socket.SOCK_STREAM)
            self.socket.connect((self.server_host, self.server_port))
            return self.socket.makefile('r'), self.socket.makefile('w')
        except (socket.error, ConnectionError) as e:
            print(f"Connection error: {e}")
            return None, None

    def join_server(self, username, password):
        """method to join the server"""
        reader, writer = self.connect_to_server()
        if not reader or not writer:
            print("Failed to connect to server")
            return False, None

        try:
            # send join request
            join_msg = self.protocol.create_join(username,
                                                 password)
            print(f"Sending join message: {join_msg}")
            writer.write(join_msg + '\r\n')
            writer.flush()

            # get response
            response_text = reader.readline()
            print(f"Join response: {response_text}")
            response = self.protocol.parse_response(response_text)

            if response and response.type == 'ok':
                print(f"Successfully joined with token: {response.token}")
                return True, response.token

            print(f"Join failed: "
                  f"{response.message if response else 'No response'}")
            return False, None
        except (socket.error, ValueError) as e:
            print(f"Error during join: {e}")
            return False, None

    def test_join_server(self):
        """Test joining the server"""
        try:
            # Check server availability first
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex((self.server_host, self.server_port))
            sock.close()
            
            if result != 0:
                print("Server not available, skipping test")
                self.skipTest("Server not available")
                
            success, token = self.join_server(self.test_user1['username'],
                                              self.test_user1['password'])
            self.assertTrue(success)
            self.assertIsNotNone(token)
        except (socket.error, ConnectionError):
            print("Server not available, skipping test")
            self.skipTest("Server not available")

    def test_send_direct_message(self):
        """Test sending a direct message"""
        try:
            # Check server availability first
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex((self.server_host, self.server_port))
            sock.close()
            
            if result != 0:
                print("Server not available, skipping test")
                self.skipTest("Server not available")
                
            print("\nTesting direct message sending...")

            # first create recipient user
            print(f"Creating recipient user: {self.test_user2['username']}")
            success, _ = self.join_server(self.test_user2['username'],
                                        self.test_user2['password'])
            self.assertTrue(success)
            if self.socket:
                self.socket.close()

            # wait a moment before creating sender
            time.sleep(1)

            # now create sender user
            print(f"Creating sender user: {self.test_user1['username']}")
            success, token = self.join_server(self.test_user1['username'],
                                            self.test_user1['password'])
            self.assertTrue(success)
            self.assertIsNotNone(token)

            reader = self.socket.makefile('r')
            writer = self.socket.makefile('w')

            # send direct message
            message = "Hello, this is a test message!"
            dm_msg = self.protocol.create_direct_message(
                token,
                message,
                self.test_user2['username']
            )
            print(f"Sending direct message: {dm_msg}")
            writer.write(dm_msg + '\r\n')
            writer.flush()

            # check response
            response_text = reader.readline()
            print(f"Direct message response: {response_text}")
            response = self.protocol.parse_response(response_text)

            self.assertIsNotNone(response)
            if response.type != 'ok':
                print(f"Error sending message: {response.message}")
            self.assertEqual(response.type, 'ok')
        except (socket.error, ConnectionError):
            print("Server not available, skipping test")
            self.skipTest("Server not available")

    def test_request_messages(self):
        """Test requesting messages"""
        try:
            # Check server availability first
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex((self.server_host, self.server_port))
            sock.close()
            
            if result != 0:
                print("Server not available, skipping test")
                self.skipTest("Server not available")
                
            success, token = self.join_server(self.test_user1['username'],
                                            self.test_user1['password'])
            self.assertTrue(success)

            reader = self.socket.makefile('r')
            writer = self.socket.makefile('w')

            # request new messages
            new_msg_request = self.protocol.request_unread_messages(token)
            writer.write(new_msg_request + '\r\n')
            writer.flush()

            # check response
            response_text = reader.readline()
            response = self.protocol.parse_messages(response_text)
            self.assertIsNotNone(response)
            self.assertEqual(response.type, 'ok')
        except (socket.error, ConnectionError):
            print("Server not available, skipping test")
            self.skipTest("Server not available")

    def tearDown(self):
        """Cleaning up after each test.."""
        if self.socket:
            try:
                self.socket.close()
            except socket.error:
                pass


if __name__ == '__main__':
    print("Make sure the server is running on localhost:3001")
    print("Starting tests...")
    unittest.main(verbosity=2)