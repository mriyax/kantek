"""Module containing all operations related to MySQL"""
import asyncio
import json
from typing import Dict, Optional

import aiomysql
import aiomysql.connection

import config


class Chats:
    """A table containing Telegram Chats"""
    name = 'chats'

    def __init__(self, db: aiomysql.connection.Connection) -> None:
        self.db = db

    async def create(self):
        await self.db.execute('''create table if not exists `{}` (
            `id` varchar(255) not null primary key,
            `tags` text not null,
            `named_tags` text not null
        )'''.format(self.name))
        await self.db.save()

    async def add_chat(self, chat_id: int) -> Dict:
        """Add a Chat to the DB or return an existing one.

        Args:
            chat_id: The id of the chat

        Returns: The chat Document

        """
        sql = 'insert ignore into `{}` (`id`, `tags`, `named_tags`) values (%s, "[]", "{{}}")'.format(
            self.name)
        await self.db.execute(sql, chat_id)
        await self.db.save()

        sql = 'select * from `{}` where `id` = %s'.format(self.name)
        chat = await self.db.execute(sql, chat_id, fetch='one')

        chat['tags'] = json.loads(chat['tags'])
        chat['named_tags'] = json.loads(chat['named_tags'])
        return chat

    async def get_chat(self, chat_id: int) -> Dict:
        """Return a Chat document

        Args:
            chat_id: The id of the chat

        Returns: The chat Document

        """
        sql = 'select * from `{}` where `id` = %s'.format(self.name)
        chat = await self.db.execute(sql, str(chat_id), fetch='one')

        if chat is None:
            return await self.add_chat(chat_id)
        else:
            chat['tags'] = json.loads(chat['tags'])
            chat['named_tags'] = json.loads(chat['named_tags'])
            return chat


class AutobahnBlacklist:
    """Base class for all types of Blacklists."""
    name = None

    def __init__(self, db: aiomysql.connection.Connection) -> None:
        self.db = db

    async def create(self):
        await self.db.execute('''create table if not exists `{}` (
            `id` int not null auto_increment primary key,
            `string` varchar(255) not null unique
        )'''.format(self.name))
        await self.db.save()

    async def add_item(self, item: str) -> Dict:
        """Add a Chat to the DB or return an existing one.

        Args:
            item: The id of the chat

        Returns: The Document

        """
        sql = 'insert ignore into `{}` (`string`) values (%s)'.format(self.name)
        await self.db.execute(sql, item)
        await self.db.save()

        sql = 'select * from `{}` where `string` = %s'.format(self.name)
        return await self.db.execute(sql, item, fetch='one')

    async def delete_item(self, item: str) -> None:
        """Delete a Chat from the DB.

        Args:
            item: The id of the chat

        Returns: None

        """
        sql = 'delete from `{}` where `string` = %s'.format(self.name)
        await self.db.execute(sql, item)
        await self.db.save()

    async def get_item(self, item: str) -> Dict:
        """Get a Chat from the DB or return an existing one.

        Args:
            item: The id of the chat

        Returns: The Document

        """
        sql = 'select * from `{}` where `string` = %s'.format(self.name)
        return await self.db.execute(sql, item, fetch='one')

    async def get_all(self) -> Dict:
        """Get all items in the Blacklist."""
        sql = 'select * from `{}`'.format(self.name)
        docs = await self.db.execute(sql, fetch='all')
        return {doc['string']: doc['id'] for doc in docs}


class AutobahnBioBlacklist(AutobahnBlacklist):
    """Blacklist with strings in a bio."""
    name = 'bio_blacklist'
    hex_type = '0x0'


class AutobahnStringBlacklist(AutobahnBlacklist):
    """Blacklist with strings in a message"""
    name = 'string_blacklist'
    hex_type = '0x1'


class AutobahnFilenameBlacklist(AutobahnBlacklist):
    """Blacklist with strings in a filename"""
    name = 'filename_blacklist'
    hex_type = '0x2'


class AutobahnChannelBlacklist(AutobahnBlacklist):
    """Blacklist with blacklisted channel ids"""
    name = 'channel_blacklist'
    hex_type = '0x3'


class AutobahnDomainBlacklist(AutobahnBlacklist):
    """Blacklist with blacklisted domains"""
    name = 'domain_blacklist'
    hex_type = '0x4'


class AutobahnFileBlacklist(AutobahnBlacklist):
    """Blacklist with blacklisted files"""
    name = 'file_blacklist'
    hex_type = '0x5'


class AutobahnMHashBlacklist(AutobahnBlacklist):
    """Blacklist with media hashes"""
    name = 'mhash_blacklist'
    hex_type = '0x6'


class AutobahnTLDBlacklist(AutobahnBlacklist):
    """Blacklist with blacklisted top level domains"""
    name = 'tld_blacklist'
    hex_type = '0x7'

class AutobahnLinkPreviewBlacklist(AutobahnBlacklist):
    """Blacklist with link preview strings for domains"""
    name = 'linkpreview_blacklist'
    hex_type = '0x8'


class BanList:
    """A list of banned ids and their reason"""
    name = 'banlist'

    def __init__(self, db: aiomysql.connection.Connection):
        self.db = db

    async def create(self):
        await self.db.execute('''create table if not exists `{}` (
            `id` int not null primary key,
            `ban_reason` varchar(255) not null
        )'''.format(self.name))
        await self.db.save()

    async def add_user(self, _id: int, reason: str) -> Dict:
        """Add a Chat to the DB or return an existing one.

        Args:
            _id: The id of the User
            reason: The ban reason

        Returns: The chat Document

        """
        sql = 'insert ignore into `{}` (`id`, `string`) values (%s, %s)'.format(self.name)
        await self.db.execute(sql, _id, reason)
        await self.db.save()

        sql = 'select * from `{}` where `id` = %s'.format(self.name)
        return await self.db.execute(sql, _id, fetch='one')

    async def get_user(self, uid: int) -> Optional[Dict]:
        sql = 'select * from `{}` where `id` = %s'.format(self.name)
        return await self.db.execute(sql, str(uid), fetch='one')


class MySQLDB:
    """Handle creation of all required Documents."""

    def __init__(self):
        self._lock = asyncio.Lock()
        self._db = None
        self.ab_collection_map = {}

    async def connect(self):
        self._db = await aiomysql.connect(host=config.db_host, user=config.db_username,
                                          password=config.db_password, db=config.db_name,
                                          cursorclass=aiomysql.DictCursor)

        await self._create_tables()
        self.ab_collection_map = {
            '0x0': self.ab_bio_blacklist,
            '0x1': self.ab_string_blacklist,
            '0x2': self.ab_filename_blacklist,
            '0x3': self.ab_channel_blacklist,
            '0x4': self.ab_domain_blacklist,
            '0x5': self.ab_file_blacklist,
            '0x6': self.ab_mhash_blacklist,
            '0x7': self.ab_tld_blacklist,
            '0x8': self.ab_linkpreview_blacklist
        }

    async def _create_tables(self):
        self.groups = await self._get_table(Chats)
        self.ab_bio_blacklist = await self._get_table(AutobahnBioBlacklist)
        self.ab_string_blacklist = await self._get_table(AutobahnStringBlacklist)
        self.ab_filename_blacklist = await self._get_table(AutobahnFilenameBlacklist)
        self.ab_channel_blacklist = await self._get_table(AutobahnChannelBlacklist)
        self.ab_domain_blacklist = await self._get_table(AutobahnDomainBlacklist)
        self.ab_file_blacklist = await self._get_table(AutobahnFileBlacklist)
        self.ab_mhash_blacklist = await self._get_table(AutobahnMHashBlacklist)
        self.ab_tld_blacklist = await self._get_table(AutobahnTLDBlacklist)
        self.ab_linkpreview_blacklist = await self._get_table(AutobahnLinkPreviewBlacklist)
        self.banlist = await self._get_table(BanList)

    async def save(self):
        async with self._lock:
            await self._db.commit()

    async def execute(self, stmt, *values, fetch=False):
        async with self._lock:
            cursor = await self._db.cursor()

            try:
                await cursor.execute(stmt, values)

                if fetch == 'all':
                    return await cursor.fetchall()
                elif fetch == 'one':
                    return await cursor.fetchone()
            finally:
                await cursor.close()

    def disconnect(self):
        self._db.close()

    async def _get_table(self, table):
        """Return a table or create it if it doesn't exist yet.

        Args:
            table: The name of the table

        Returns: The Table object

        """
        _table = table(self)
        await _table.create()
        return _table
