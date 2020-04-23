"""File containing the Custom TelegramClient"""
import ast
import asyncio
import datetime
import logging
import re
import socket
from typing import Optional, Tuple, Union

import logzero
import spamwatch
from aiohttp import ClientError, ClientSession, ClientTimeout
from faker import Faker
from spamwatch.types import Permission
from telethon import TelegramClient, hints
from telethon.errors import UserAdminInvalidError
from telethon.events import ChatAction, NewMessage
from telethon.tl.custom import Message
from telethon.tl.functions.channels import EditBannedRequest
from telethon.tl.patched import Message
from telethon.tl.types import ChatBannedRights
from yarl import URL

import config
from config import cmd_prefix
from database.mysql import MySQLDB
from utils.constants import SCHEDULE_DELETION_COMMAND
from utils.mdtex import FormattedBase, MDTeXDocument, Section
from utils.pluginmgr import PluginManager

logger: logging.Logger = logzero.logger

AUTOMATED_BAN_REASONS = ['spambot', 'vollzugsanstalt', 'kriminalamt']
SPAMADD_PATTERN = re.compile(r"(?i)spam adding (?P<count>\d+)\+ members")


class KantekClient(TelegramClient):  # pylint: disable = R0901, W0223
    """Custom telethon client that has the plugin manager as attribute."""
    commands: dict = {}
    plugin_mgr: Optional[PluginManager] = None
    db: Optional[MySQLDB] = None
    gban_sender: Optional['KantekClient'] = None
    kantek_version: str = ''
    sw: spamwatch.Client = None
    sw_url: str = None
    aioclient: ClientSession = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aioclient = ClientSession(timeout=ClientTimeout(total=2))

    async def respond(self, event: NewMessage.Event,
                      msg: Union[str, FormattedBase, Section, MDTeXDocument],
                      reply: bool = True, link_preview: bool = True,
                      delete: Optional[int] = None) -> Message:
        """Respond to the message an event caused or to the message that was replied to

        Args:
            event: The event of the message
            msg: The message text
            reply: If it should reply to the message that was replied to
            link_preview: Should the link preview be shown?
            delete: Seconds until the sent message should be deleted

        Returns: None

        """
        msg = str(msg)
        if reply:
            if isinstance(event, ChatAction.Event):
                reply_to = event.action_message.id
            else:
                reply_to = (event.reply_to_msg_id or event.message.id)
            sent_msg: Message = await event.respond(msg, reply_to=reply_to, link_preview=link_preview)
        else:
            sent_msg: Message = await event.respond(msg, reply_to=event.message.id, link_preview=link_preview)
        if delete is not None:
            # While asyncio.sleep would work, it would stop the function from returning which is annoying
            await self.send_message(sent_msg.chat, f'{SCHEDULE_DELETION_COMMAND} [Scheduled deletion]',
                                    schedule=datetime.timedelta(seconds=delete), reply_to=sent_msg.id)
        return sent_msg

    async def gban(self, uid: Union[int, str], reason: str) -> Tuple[bool, str]:
        """Command to gban a user

        Args:
            uid: User ID
            reason: Ban reason

        Returns:
            True if ban was successful else false, ban reason

        """
        # if the user account is deleted this can be None
        if uid is None:
            return

        sql = 'select * from `banlist` where `id` = %s limit 1'
        user = await self.db.execute(sql, uid, fetch='one')

        for ban_reason in AUTOMATED_BAN_REASONS:
            if user and (ban_reason in user['ban_reason'].lower()):
                if ban_reason == 'kriminalamt':
                    return False, 'Already banned by kriminalamt'
                else:
                    return False, 'Already banned by autobahn'

        if user:
            count = SPAMADD_PATTERN.search(reason)
            previous_count = SPAMADD_PATTERN.search(user['ban_reason'])
            if count is not None and previous_count is not None:
                count = int(count.group('count')) + int(previous_count.group('count'))
                reason = f"spam adding {count}+ members"

        await self.gban_sender.send_message(
            config.gban_group,
            f'<a href="tg://user?id={uid}">{uid}</a>', parse_mode='html')
        for message in config.gban_messages:
            await self.gban_sender.send_message(
                config.gban_group,
                message.format(uid=uid, reason=reason))
        await asyncio.sleep(0.5)

        sql = 'insert into `banlist` (`id`, `ban_reason`) values (%s, %s)'\
              'on duplicate key update `ban_reason` = %s'
        await self.db.execute(sql, uid, reason, reason)
        await self.db.save()

        if self.sw and self.sw.permission in [Permission.Admin,
                                              Permission.Root]:
            self.sw.add_ban(int(uid), reason)
        # Some bots are slow so wait a while before clearing mentions
        await asyncio.sleep(10)
        await self.edit_folder(config.gban_group, folder=1)

        return True, reason

    async def ungban(self, uid: Union[int, str]):
        """Command to gban a user

        Args:
            uid: User ID

        Returns: None

        """
        await self.gban_sender.send_message(
            config.gban_group,
            f'<a href="tg://user?id={uid}">{uid}</a>', parse_mode='html')
        for message in config.ungban_messages:
            await self.gban_sender.send_message(
                config.gban_group,
                message.format(uid=uid))
        await asyncio.sleep(10)
        await self.edit_folder(config.gban_group, folder=1)

        sql = 'delete from `banlist` where `id` = %s'
        await self.db.execute(sql, uid)
        await self.db.save()

        if self.sw and self.sw.permission in [Permission.Admin,
                                              Permission.Root]:
            self.sw.delete_ban(int(uid))

    async def ban(self, chat, uid):
        """Bans a user from a chat."""
        try:
            await self(EditBannedRequest(
                chat, uid, ChatBannedRights(
                    until_date=datetime.datetime(2038, 1, 1),
                    view_messages=True
                )
            ))
        except UserAdminInvalidError as err:
            logger.error(err)

    async def get_cached_entity(self, entity: hints.EntitiesLike):
        input_entity = await self.get_input_entity(entity)
        return await self.get_entity(input_entity)

    async def resolve_url(self, url: str, base_domain: bool = True) -> str:
        """Follow all redirects and return the base domain

        Args:
            url: The url
            base_domain: Flag if any subdomains should be stripped

        Returns:
            The base comain as given by urllib.parse
        """
        faker = Faker()
        headers = {'User-Agent': faker.user_agent()}
        old_url = url
        if not url.startswith('http'):
            url = f'http://{url}'
        try:
            async with self.aioclient.get(url, headers=headers) as response:
                url: URL = response.url
        except (ClientError, asyncio.TimeoutError, socket.gaierror) as err:
            logger.warning(err)
            return old_url

        if base_domain:
            # split up the result to only get the base domain
            # www.sitischu.com => sitischu.com
            url = url.host
            _base_domain = url.split('.', maxsplit=url.count('.') - 1)[-1]
            if _base_domain:
                url = _base_domain
        return str(url)
