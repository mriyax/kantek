"""File containing the settings for kantek."""
from typing import List, Union

api_id: Union[str, int] = ''
api_hash: str = ''
phone: str = ''
session_path: str = f'sessions/'

log_bot_token: str = ''
log_channel_id: Union[str, int] = ''

gban_group = ''

# This is regex so make sure to escape the usual characters
cmd_prefix: str = r'\.'

db_username = 'kantek'
db_name = 'kantek'
db_password = 'PASSWORD'
db_host = 'localhost'

# Optional
# if these options are empty the feature will be disabled.

# The file were bans and unbans are stored
# The extension is .spjson and will be automatically added.
strafregister_file: str = ''

# Channels to fetch bans from
vollzugsanstalten: List[int] = []
