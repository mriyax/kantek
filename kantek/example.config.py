"""File containing the settings for kantek."""
from typing import List, Union

api_id: Union[str, int] = ''
api_hash: str = ''
phone: str = ''
session_path: str = f'sessions/'

log_bot_token: str = ''
log_channel_id: Union[str, int] = ''

gban_group = ''
gban_sender_session = 'kantek-session'
gban_messages = (
    '/gban {uid} {reason}',
    '/fban {uid} {reason}'
)
ungban_messages = (
    '/ungban {uid}',
    '/unfban {uid}'
)

# This is regex so make sure to escape the usual characters
cmd_prefix: str = r'\.'

db_username = 'kantek'
db_name = 'kantek'
db_password = 'PASSWORD'
db_host = 'localhost'

# Optional
# if these options are empty the feature will be disabled.

# Channels to fetch bans from
vollzugsanstalten: List[int] = []

spamwatch_host: str = 'https://api.spamwat.ch'
spamwatch_token: str = ''
