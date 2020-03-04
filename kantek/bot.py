"""Main bot module. Setup logging, register components"""
import asyncio
import concurrent
import logging
import os
import sys
from argparse import ArgumentParser

import logzero

import config
import spamwatch
from database.mysql import MySQLDB
from utils.client import KantekClient
from utils.loghandler import TGChannelLogHandler
from utils.pluginmgr import PluginManager

try:
    from config import spamwatch_host, spamwatch_token
except ImportError:
    spamwatch_host = ''
    spamwatch_token = ''

logger = logzero.setup_logger('kantek-logger', level=logging.DEBUG)
telethon_logger = logzero.setup_logger('telethon', level=logging.INFO)
tlog = logging.getLogger('kantek-channel-log')
handler = TGChannelLogHandler(config.log_bot_token,
                              config.log_channel_id)
tlog.addHandler(handler)
tlog.setLevel(logging.INFO)

__version__ = '0.3.1'


async def create_client(session_name, *, login=False, bot=False, phone_number=None, db=None, gban_sender=None) -> KantekClient:
    """Create a kantek client."""
    client = KantekClient(
        session_name,
        config.api_id,
        config.api_hash)

    if login:
        if bot:
            await client.start(bot_token=phone_number)
        else:
            await client.start(phone=phone_number)
    else:
        await client.start()
        client.kantek_version = __version__
        client.plugin_mgr = PluginManager(client)
        client.plugin_mgr.register_all()
        client.db = db
        client.gban_sender = client if gban_sender is None else gban_sender

        if spamwatch_host and spamwatch_token:
            client.sw = spamwatch.Client(spamwatch_token, host=spamwatch_host)

    return client


async def main() -> None:
    """Register logger and components."""
    session_path = os.path.relpath(config.session_path)
    gban_sender = config.gban_sender_session
    parser = ArgumentParser()
    parser.add_argument('-l', '--login', nargs=2, metavar=('name', 'number'),
                        help='Create a new Telegram session')
    parser.add_argument('-b', '--bot', help='Login as a bot', default=False, action='store_true')
    args = parser.parse_args(sys.argv[1:])

    if args.login:
        name, phone_number = args.login
        client = await create_client(f'{session_path}/{name}', login=True,
                                     bot=args.bot, phone_number=phone_number)
        await client.disconnect()
        return

    clients = []
    db = MySQLDB()
    await db.connect()

    session_name = f'{session_path}/{gban_sender}'
    gban_sender_client = await create_client(session_name, db=db)
    clients.append(gban_sender_client)

    for _, __, files in os.walk(session_path):
        for file in files:
            if file.endswith('.session') and file != f'{gban_sender}.session':
                session_name = f'{session_path}/{file[:-len(".session")]}'
                client = await create_client(session_name, db=db, gban_sender=gban_sender_client)
                clients.append(client)

    tlog.info('Started kantek v%s', __version__)
    logger.info('Started kantek v%s', __version__)

    await asyncio.wait([client.run_until_disconnected() for client in clients],
                       return_when=concurrent.futures.FIRST_COMPLETED)

    db.disconnect()
    for client in clients:
        await client.disconnect()

    if spamwatch_host and spamwatch_token:
        client.sw = spamwatch.Client(spamwatch_token, host=spamwatch_host)
        client.sw_url = spamwatch_host


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
