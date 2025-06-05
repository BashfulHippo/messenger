# Messenger

A multi-threaded desktop messaging application built with Python and Tkinter.

## Features

- **Multi-threaded architecture**: Separate threads for UI, network operations, and message polling to ensure responsive interface during network operations
- **Offline message queuing**: Messages are queued locally when disconnected and automatically sent upon reconnection
- **Connection recovery**: Automatic reconnection with exponential backoff
- **SQLite storage**: Persistent local storage for messages, contacts, and user data
- **Secure password storage**: Password hashing with bcrypt (or pbkdf2 fallback)

## Architecture

The application uses a 3-thread model:

1. **Main Thread (GUI)**: Handles all Tkinter operations, reads from incoming queue
2. **Network Thread**: Sends messages from outgoing queue, handles reconnection logic
3. **Polling Thread**: Polls server for new messages, pushes to incoming queue

Thread-safe communication is achieved through synchronized queues.

## Project Structure

```
messenger.py      - Main GUI application
ds_messenger.py   - Network messaging module
ds_protocol.py    - JSON protocol implementation
database.py       - SQLite database layer
security.py       - Password hashing utilities
config.py         - Configuration management
Profile.py        - Legacy profile storage (dsu format)
```

## Usage

```bash
python messenger.py
```

On first run, you'll be prompted for server connection details. Messages are stored locally and persist across sessions.

## Configuration

Settings are stored in `config.json`:

```json
{
  "server": "127.0.0.1",
  "port": 3001,
  "poll_interval": 2,
  "max_retries": 5
}
```

## Requirements

- Python 3.8+
- tkinter (usually included with Python)
- bcrypt (optional, for password hashing)

## Testing

```bash
python -m pytest test_ds_messenger.py test_ds_protocol.py
```

Note: Integration tests require a running server on port 3001.
