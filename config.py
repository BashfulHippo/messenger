# config.py
"""Configuration management for the messaging app."""

import json
from pathlib import Path

DEFAULT_CONFIG = {
    "server": "127.0.0.1",
    "port": 3001,
    "poll_interval": 2,
    "max_retries": 5,
    "db_path": "messenger.db",
    "log_file": "messenger.log"
}


class Config:
    """manages application configuration."""

    def __init__(self, config_path='config.json'):
        self.config_path = Path(config_path)
        self.settings = DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        """load config from file if it exists."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    self.settings.update(loaded)
            except (json.JSONDecodeError, IOError):
                pass  # use defaults

    def save(self):
        """save current config to file."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2)
        except IOError:
            pass

    def get(self, key, default=None):
        """get a config value."""
        return self.settings.get(key, default)

    def set(self, key, value):
        """set a config value."""
        self.settings[key] = value
        self.save()

    @property
    def server(self):
        return self.settings['server']

    @property
    def port(self):
        return self.settings['port']

    @property
    def poll_interval(self):
        return self.settings['poll_interval']

    @property
    def max_retries(self):
        return self.settings['max_retries']

    @property
    def db_path(self):
        return self.settings['db_path']

    @property
    def log_file(self):
        return self.settings['log_file']
