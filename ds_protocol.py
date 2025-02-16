# ds_protocol.py
"""Protocol module for the messaging system that handles message formatting
and parsing for communication."""

from collections import namedtuple
import json
import time

# Responses
ServerResponse = namedtuple('ServerResponse', ['type', 'message', 'token'])
MessageResponse = namedtuple('MessageResponse', ['type', 'messages'])


class DirectMessagingProtocol:
    """Protocol for direct messaging functionality"""
    # p.s static methods do not depend on instance attr and rather act like
    # 'utility' functions which are related to the class. so
    # instead of requiring
    # an instance of DMP, the methods can perform their actions
    # directly (can also
    # use regular, but it would unnecessarily store the methods)

    @staticmethod
    def create_join(username: str, password: str) -> str:
        """Creates a join message"""
        return json.dumps({
            "join": {
                "username": username,
                "password": password,
                "token": ""
            }
        })

    @staticmethod
    def create_direct_message(token: str, message: str, recipient: str) -> str:
        """Creates a direct message"""
        return json.dumps({
            "token": token,
            "directmessage": {
                "entry": message,
                "recipient": recipient,
                "timestamp": str(time.time())
            }
        })

    @staticmethod
    def request_unread_messages(token: str) -> str:
        """Creates a request for unread messages"""
        return json.dumps({
            "token": token,
            "directmessage": "new"
        })

    @staticmethod
    def request_all_messages(token: str) -> str:
        """Creates a request for all messages"""
        return json.dumps({
            "token": token,
            "directmessage": "all"
        })

    @staticmethod
    def parse_response(json_msg: str) -> ServerResponse:
        """Parses server response"""
        try:
            json_obj = json.loads(json_msg)
            if 'response' in json_obj:
                resp = json_obj['response']
                return ServerResponse(
                    type=resp.get('type'),
                    message=resp.get('message', ''),
                    token=resp.get('token', '')
                )
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            print(f"Invalid JSON: {json_msg}")
        except KeyError as e:
            print(f"Missing key in response: {e}")
        except AttributeError as e:
            print(f"Invalid attribute access in response: {e}")
        except Exception as e:  # pylint: disable=broad-except
            print(f"Unexpected error parsing response: {e}")
        return None

    @staticmethod
    def parse_messages(json_msg: str) -> MessageResponse:
        """Parses message response"""
        try:
            json_obj = json.loads(json_msg)
            if 'response' in json_obj:
                resp = json_obj['response']
                return MessageResponse(
                    type=resp.get('type'),
                    messages=resp.get('messages', [])
                )
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            print(f"Invalid JSON: {json_msg}")
        except KeyError as e:
            print(f"Missing key in response: {e}")
        except AttributeError as e:
            print(f"Invalid attribute access in response: {e}")
        except Exception as e:  # pylint: disable=broad-except
            print(f"Unexpected error parsing response: {e}")
        return None
