from telethon.errors import UsernameInvalidError, UsernameNotOccupiedError

TELEGRAM_DOMAINS = ['t.me',
                    'telegram.dog',
                    'telegram.me',
                    'telegram.org',
                    'telegra.ph',
                    'tdesktop.com',
                    'telesco.pe',
                    'graph.org',
                    'contest.dev']

GET_ENTITY_ERRORS = (UsernameNotOccupiedError, UsernameInvalidError, ValueError)
