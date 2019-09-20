"""Main bot module. Setup logging, register components"""
import asyncio
import concurrent
import logging
import os
import sys
from argparse import ArgumentParser

import logzero

import config
from database.mysql import MySQLDB
from utils.client import KantekClient
from utils.loghandler import TGChannelLogHandler
from utils.pluginmgr import PluginManager

logger = logzero.setup_logger('kantek-logger', level=logging.DEBUG)
telethon_logger = logzero.setup_logger('telethon', level=logging.INFO)
tlog = logging.getLogger('kantek-channel-log')
handler = TGChannelLogHandler(config.log_bot_token,
                              config.log_channel_id)
tlog.addHandler(handler)
tlog.setLevel(logging.INFO)

__version__ = '0.3.1'


async def create_client(session_name, *, login=False, phone_number=None) -> KantekClient:
    """Create a kantek client."""
    client = KantekClient(
        session_name,
        config.api_id,
        config.api_hash)

    if login:
        await client.start(phone_number)
    else:
        await client.start()
        client.kantek_version = __version__
        client.plugin_mgr = PluginManager(client)
        client.db = MySQLDB()
        client.plugin_mgr.register_all()

    return client


async def main() -> None:
    """Register logger and components."""
    session_path = os.path.relpath(config.session_path)
    parser = ArgumentParser()
    parser.add_argument('-l', '--login', nargs=2, metavar=('name', 'number'),
                        help='Create a new Telegram session')
    args = parser.parse_args(sys.argv[1:])

    if args.login:
        name, phone_number = args.login
        client = await create_client(f'{session_path}/{name}',
                                     login=True, phone_number=phone_number)
        await client.disconnect()
        return

    clients = []

    for _, __, files in os.walk(session_path):
        for file in files:
            if file.endswith('.session'):
                session_name = f'{session_path}/{file[:-len(".session")]}'
                client = await create_client(session_name)
                clients.append(client)

    tlog.info('Started kantek v%s', __version__)
    logger.info('Started kantek v%s', __version__)

    await asyncio.wait([client.run_until_disconnected() for client in clients],
                       return_when=concurrent.futures.FIRST_COMPLETED)

    for client in clients:
        await client.disconnect()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
