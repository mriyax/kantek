"""Plugin to manage the banlist of the bot."""
import asyncio
import csv
import logging
import os
import time
from typing import List

import pymysql
from spamwatch.types import Ban, Permission
from telethon import events
from telethon.events import NewMessage
from telethon.tl.custom import Message

from config import cmd_prefix
from database.mysql import MySQLDB
from utils import helpers, parsers
from utils.client import KantekClient
from utils.mdtex import (Bold, Code, Italic, KeyValueItem, MDTeXDocument,
                         Section)

__version__ = '0.2.0'

tlog = logging.getLogger('kantek-channel-log')

SWAPI_SLICE_LENGTH = 50

@events.register(events.NewMessage(outgoing=True, pattern=f'{cmd_prefix}b(an)?l(ist)?'))
async def banlist(event: NewMessage.Event) -> None:
    """Command to query and manage the banlist."""
    client: KantekClient = event.client
    msg: Message = event.message
    db: MySQLDB = client.db
    args = msg.raw_text.split()[1:]
    response = ''
    if not args:
        pass
    elif args[0] == 'query':
        response = await _query_banlist(event, db)
    elif args[0] == 'import':
        waiting_message = await client.respond(event, 'Importing bans. This might take a while.')
        response = await _import_banlist(event, db)
        await waiting_message.delete()
    elif args[0] == 'export':
        waiting_message = await client.respond(event, 'Exporting bans. This might take a while.')
        response = await _export_banlist(event, db)
        await waiting_message.delete()
    if response:
        await client.respond(event, response)


async def _query_banlist(event: NewMessage.Event, db: MySQLDB) -> MDTeXDocument:
    msg: Message = event.message
    args = msg.raw_text.split()[2:]
    keyword_args, args = parsers.parse_arguments(' '.join(args))
    reason = keyword_args.get('reason')
    users = []
    if args:
        with db.cursor() as cursor:
            uids = [str(uid) for uid in args]
            sql = 'select * from `banlist` where `id` in ({})'.format(','.join(uids))
            cursor.execute(sql)
            users = cursor.fetchall()
            query_results = [KeyValueItem(Code(user['id']), user['ban_reason'])
                             for user in users] or [Italic('None')]
    elif reason is not None:
        with db.cursor() as cursor:
            sql = 'select count(*) as count from `banlist` where `ban_reason` like "%{}%"'.format(
                pymysql.escape_string(reason))
            cursor.execute(sql)
            count = cursor.fetchone()['count']
            query_results = [KeyValueItem(Bold('Count'), Code(count))]
    else:
        with db.cursor() as cursor:
            sql = 'select count(*) as count from `banlist`'
            cursor.execute(sql)
            count = cursor.fetchone()['count']
            query_results = [KeyValueItem(Bold('Total Count'), Code(count))]

    return MDTeXDocument(Section(Bold('Query Results'), *query_results))


async def _import_banlist(event: NewMessage.Event, db: MySQLDB) -> MDTeXDocument:
    msg: Message = event.message
    client: KantekClient = event.client
    filename = 'tmp/banlist_import.csv'
    if msg.is_reply:
        reply_msg: Message = await msg.get_reply_message()
        _, ext = os.path.splitext(reply_msg.document.attributes[0].file_name)
        if ext == '.csv':
            await reply_msg.download_media('tmp/banlist_import.csv')
            start_time = time.time()
            _banlist = await helpers.rose_csv_to_dict(filename)
            if _banlist:
                with db.cursor() as cursor:
                    sql = 'insert into `banlist` (`id`, `ban_reason`) values (%s, %s)' \
                          'on duplicate key update `ban_reason` = %s'

                    for ban in _banlist:
                        cursor.execute(sql, (ban['id'], ban['reason'], ban['id']))

                db.commit()

                if client.sw and client.sw.permission in [Permission.Admin, Permission.Root]:
                    bans = {}
                    for b in _banlist:
                        bans[b['reason']] = bans.get(b['reason'], []) + [b['id']]
                    admin_id = (await client.get_me()).id
                    for reason, uids in bans.items():
                        uids_copy = uids[:]
                        while uids_copy:
                            client.sw.add_bans([Ban(int(uid), reason, admin_id)
                                                for uid in uids_copy[:SWAPI_SLICE_LENGTH]])
                            uids_copy = uids_copy[SWAPI_SLICE_LENGTH:]

            stop_time = time.time() - start_time
            return MDTeXDocument(Section(Bold('Import Result'),
                                         f'Added {len(_banlist)} entries.'),
                                 Italic(f'Took {stop_time:.02f}s'))
        else:
            return MDTeXDocument(Section(Bold('Error'), 'File is not a CSV'))


async def _export_banlist(event: NewMessage.Event, db: MySQLDB) -> MDTeXDocument:
    client: KantekClient = event.client
    chat = await event.get_chat()
    with db.cursor() as cursor:
        sql = 'select * from `banlist`'
        cursor.execute(sql)
        users = cursor.fetchall()
        os.makedirs('tmp/', exist_ok=True)
        start_time = time.time()
        with open('tmp/banlist_export.csv', 'w', newline='') as f:
            f.write('id,reason\n')
            cwriter = csv.writer(f)
            for user in users:
                cwriter.writerow([user['id'], user['ban_reason']])
        stop_time = time.time() - start_time
        await client.send_file(chat, 'tmp/banlist_export.csv',
                               caption=str(Italic(f'Took {stop_time:.02f}s')))
