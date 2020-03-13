import json
import os

from telethon import TelegramClient
from telethon.sessions import StringSession

import config


def main():
    session_path = os.path.relpath(config.session_path)
    string_sessions = {}

    for _, __, files in os.walk(session_path):
        for file in files:
            if file.endswith('.session'):
                session_name = f'{session_path}/{file[:-len(".session")]}'
                client = TelegramClient(session_name, config.api_id, config.api_hash)
                string_sessions[file[:-len(".session")]] = StringSession.save(client.session)

    with open('sessions.json', 'w') as f:
        json.dump(string_sessions, f)


if __name__ == '__main__':
    main()
