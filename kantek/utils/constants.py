from telethon.errors import UsernameInvalidError, UsernameNotOccupiedError, InviteHashInvalidError

TELEGRAM_DOMAINS = ['t.me',
                    'telegram.dog',
                    'telegram.me',
                    'telegram.org',
                    'telegra.ph',
                    'tdesktop.com',
                    'telesco.pe',
                    'graph.org',
                    'contest.dev']

GET_ENTITY_ERRORS = (UsernameNotOccupiedError, UsernameInvalidError, ValueError, InviteHashInvalidError)

SCHEDULE_DELETION_COMMAND = "kantek_scheduled_delete"
