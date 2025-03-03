# pylint: disable=invalid-name
# -not going to change name for now
# profile.py
"""Module for handling user profiles in the messaging system.
Provides classes for profile stuff, posts, and direct messaging."""

import json
import time
from pathlib import Path


class DsuFileError(Exception):
    """Exception raised for errors related to DSU files."""


class DsuProfileError(Exception):
    """Exception raised for errors related to DSU profiles."""


class Post(dict):
    """Represents a post in a user's profile."""

    def __init__(self, entry: str = None, timestamp: float = 0):
        """Initialize a new Post.

        Args:
            entry: The content of the post
            timestamp: The time when the post was created
        """
        self._timestamp = timestamp
        self.set_entry(entry)
        dict.__init__(self, entry=self._entry,
                      timestamp=self._timestamp)

    def set_entry(self, entry):
        """Set the content of the post.

        Args:
            entry: The content to set
        """
        self._entry = entry
        dict.__setitem__(self, 'entry', entry)
        if self._timestamp == 0:
            self._timestamp = time.time()

    def get_entry(self):
        """Get the content of the post.

        Returns:
            The post content
        """
        return self._entry

    def set_time(self, timestamp: float):
        """Set the timestamp of the post.

        Args:
            timestamp: The time to set
        """
        self._timestamp = timestamp
        dict.__setitem__(self, 'timestamp', timestamp)

    def get_time(self):
        """Get the timestamp of the post.

        Returns:
            The post timestamp
        """
        return self._timestamp

    entry = property(get_entry, set_entry)
    timestamp = property(get_time, set_time)


class DirectMessage:
    """Represents a direct message between users."""

    def __init__(self, message=None, recipient=None,
                 timestamp=None, from_user=None):
        """Initialize a new DirectMessage.

        Args:
            message: The content of the message or a dictionary of message data
            recipient: The username of the recipient
            timestamp: The time when the message was sent
            from_user: The username of the sender
        """
        #  message is a dictionary, extract values from it
        if isinstance(message, dict):
            data = message
            self._message = data.get('message')
            self._recipient = data.get('recipient')
            self._timestamp = data.get('timestamp') or time.time()
            self._from_user = data.get('from_user')
            self._entry = self._message  # For compatibility
        else:
            # a normal init but with separate arguments
            self._message = message
            self._recipient = recipient
            self._timestamp = timestamp or time.time()
            self._from_user = from_user
            self._entry = message  # For compatibility

    def get_entry(self):
        """Get the message content (alias for compatibility).

        Returns:
            The message content
        """
        return self._message

    def get_message(self):
        """Get the message content.

        Returns:
            The message content
        """
        return self._message

    def get_recipient(self):
        """Get the recipient username.

        Returns:
            The recipient's username
        """
        return self._recipient

    def get_timestamp(self):
        """Get the message timestamp.

        Returns:
            The message timestamp
        """
        return self._timestamp

    def get_from_user(self):
        """Get the sender username.

        Returns:
            The sender's username
        """
        return self._from_user

    def to_dict(self):
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the message
        """
        return {
            'message': self._message,
            'recipient': self._recipient,
            'timestamp': self._timestamp,
            'from_user': self._from_user,
            'entry': self._entry
        }

    # add a get method for dictionary access
    def get(self, key, default=None):
        # pylint: disable=too-many-return-statements
        """Dict-like get method for compatibility.

        Args:
            key: The key to look up
            default: The default value to return if key not found

        Returns:
            The value associated with the key or the default
        """
        if key == 'message':
            return self._message
        if key == 'recipient':
            return self._recipient
        if key == 'timestamp':
            return self._timestamp
        if key == 'from':
            return self._from_user
        if key == 'from_user':
            return self._from_user
        if key == 'entry':
            return self._entry
        return default

    entry = property(get_entry)
    message = property(get_message)
    recipient = property(get_recipient)
    timestamp = property(get_timestamp)
    from_user = property(get_from_user)


class Profile:
    """Represents a user profile in the DS messaging system."""

    def __init__(self, dsuserver=None, username=None,
                 password=None):
        """Initialize a new Profile.

        Args:
            dsuserver: The DSU server address
            username: The user's username
            password: The user's password
        """
        self.dsuserver = dsuserver  # REQUIRED
        self.username = username    # REQUIRED
        self.password = password    # REQUIRED
        self.bio = ''              # OPTIONAL
        self._posts = []           # OPTIONAL
        self._messages = []        # Added for direct messaging
        self._friends = set()      # Added to store recipients/friends

    def add_post(self, post: Post) -> None:
        """Add a post to the profile.

        Args:
            post: The Post object to add
        """
        self._posts.append(post)

    def del_post(self, index: int) -> bool:
        """Delete a post from the profile.

        Args:
            index: The index of the post to delete

        Returns:
            True if post was deleted, False if index was invalid
        """
        try:
            del self._posts[index]
            return True
        except IndexError:
            return False

    def get_posts(self) -> list[Post]:
        """Get all posts in the profile.

        Returns:
            List of Post objects
        """
        return self._posts

    def add_direct_message(self, message):
        """
        Add a direct message to the profile with improved handling.
        
        Args:
            message: The DirectMessage object or dict to add
        """
        if isinstance(message, dict):
            message = DirectMessage(message)
        
        # add message to our collection
        self._messages.append(message)
        
        # update friends list with both sender and recipient
        if message.get_recipient() and message.get_recipient() != self.username:
            self._friends.add(message.get_recipient())
        if message.get_from_user() and message.get_from_user() != self.username:
            self._friends.add(message.get_from_user())

    def get_direct_messages(self) -> list[DirectMessage]:
        """Get all direct messages.

        Returns:
            List of DirectMessage objects
        """
        return self._messages

    def get_messages_with(self, username: str) -> list[DirectMessage]:
        """Get all messages exchanged with a specific user.

        Args:
            username: The username to filter messages by

        Returns:
            List of DirectMessage objects exchanged with the specified user
        """
        return [
            msg for msg in self._messages
            if username in (msg.recipient, msg.from_user)
        ]

    def get_friends(self) -> list:
        """Get list of friends/recipients.

        Returns:
            Sorted list of usernames
        """
        return sorted(list(self._friends))

    def add_friend(self, username: str) -> None:
        """Add a friend/recipient.

        Args:
            username: The username to add as a friend
        """
        if username and username.strip():
            self._friends.add(username.strip())

    def save_profile(self, path: str) -> None:
        """Save the profile to a DSU file.

        Args:
            path: The file path to save to

        Raises:
            DsuFileError: If there's an error saving the file
        """
        p = Path(path)

        if p.suffix == '.dsu':
            try:
                data = {
                    'username': self.username,
                    'password': self.password,
                    'dsuserver': self.dsuserver,
                    'bio': self.bio,
                    '_posts': self._posts,
                    '_messages':
                    [msg.to_dict() for msg in self._messages],
                    '_friends': list(self._friends)
                }

                with open(p, 'w', encoding='utf-8') as f:
                    json.dump(data, f)
            except Exception as ex:
                raise DsuFileError("Error while attempting to "
                                   "process the DSU file.", ex) from ex
        else:
            raise DsuFileError("Invalid DSU file path or type")

    def load_profile(self, path: str) -> None:
        """Load a profile from a DSU file.

        Args:
            path: The file path to load from

        Raises:
            DsuFileError: If the file doesn't exist or is invalid
            DsuProfileError: If there's an error processing the profile data
        """
        p = Path(path)

        if p.exists() and p.suffix == '.dsu':
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                self.username = data.get('username')
                self.password = data.get('password')
                self.dsuserver = data.get('dsuserver')
                self.bio = data.get('bio', '')

                # load the posts
                self._posts = []
                for post_data in data.get('_posts', []):
                    post = Post(post_data.get('entry'),
                                post_data.get('timestamp'))
                    self._posts.append(post)

                # load messages
                self._messages = []
                for msg_data in data.get('_messages', []):
                    msg = DirectMessage(msg_data)
                    self._messages.append(msg)

                # load friends
                self._friends = set(data.get('_friends', []))

            except Exception as ex:
                raise DsuProfileError(ex) from ex
        else:
            raise DsuFileError()
