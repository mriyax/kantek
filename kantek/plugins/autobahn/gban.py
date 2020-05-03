"""Plugin to handle global bans"""
import asyncio
import datetime
import logging
from typing import Dict, Optional, List

import logzero
from telethon import events
from telethon.errors import MessageIdInvalidError
from telethon.events import NewMessage
from telethon.tl.custom import Message
from telethon.tl.functions.channels import EditBannedRequest
from telethon.tl.functions.messages import ReportRequest
from telethon.tl.types import Channel, InputReportReasonSpam, ChatBannedRights

from config import cmd_prefix, gban_group
from utils import helpers
from utils.client import KantekClient
from utils.mdtex import MDTeXDocument, Section, KeyValueItem, Bold, Code

__version__ = '0.4.0'

tlog = logging.getLogger('kantek-channel-log')
logger: logging.Logger = logzero.logger

DEFAULT_REASON = 'spam[gban]'
CHUNK_SIZE = 10


@events.register(events.NewMessage(outgoing=True, pattern=f'{cmd_prefix}gban'))
async def gban(event: NewMessage.Event) -> None:
    """Command to globally ban a user."""

    chat: Channel = await event.get_chat()
    msg: Message = event.message
    client: KantekClient = event.client
    keyword_args, args = await helpers.get_args(event)
    chat_document = await client.db.groups.get_chat(event.chat_id)
    db_named_tags: Dict = chat_document['named_tags']
    gban = db_named_tags.get('gban')
    verbose = False
    if gban == 'verbose' or event.is_private:
        verbose = True
    await msg.delete()
    if msg.is_reply:

        bancmd = db_named_tags.get('gbancmd')
        reply_msg: Message = await msg.get_reply_message()
        uid = reply_msg.from_id
        if args:
            ban_reason = args[0]
        else:
            ban_reason = DEFAULT_REASON
        try:
            await reply_msg.forward_to(gban_group)
        except MessageIdInvalidError as err:
            logger.error(err)
        await client.gban(uid, ban_reason)
        await client(ReportRequest(chat, [reply_msg.id], InputReportReasonSpam()))
        if chat.creator or chat.admin_rights:
            if bancmd == 'manual' or bancmd is None:
                await client(EditBannedRequest(
                    chat, uid, ChatBannedRights(
                        until_date=datetime.datetime(2038, 1, 1),
                        view_messages=True
                    )
                ))
            elif bancmd is not None:
                await reply_msg.reply(f'{bancmd} {ban_reason}')
                await asyncio.sleep(0.5)
            await reply_msg.delete()
    else:
        uids = []
        ban_reason = []
        for arg in args:
            if isinstance(arg, int):
                uids.append(arg)
            else:
                ban_reason.append(arg)
        if ban_reason:
            ban_reason = ' '.join(ban_reason)
        else:
            ban_reason = keyword_args.get('reason', DEFAULT_REASON)

        skipped_uids = {}
        banned_uids = {}
        progress_message: Optional[Message]
        if verbose and len(uids) > 10:
            progress_message: Message = await client.send_message(chat, f"Processing {len(uids)} User IDs")
        else:
            progress_message = None
        while uids:
            uid_batch = uids[:CHUNK_SIZE]
            for uid in uid_batch:
                banned, reason = await client.gban(uid, ban_reason)
                if not banned:
                    skipped_uids[reason] = skipped_uids.get(reason, []) + [str(uid)]
                # sleep to avoid flooding the bots too much
                else:
                    banned_uids[reason] = banned_uids.get(reason, []) + [str(uid)]
                await asyncio.sleep(0.5)
            uids = uids[CHUNK_SIZE:]
            if uids:
                if progress_message:
                    await progress_message.edit(
                        f"Sleeping for 10 seconds after banning {len(uid_batch)} Users. {len(uids)} Users left.")
                await asyncio.sleep(10)

        if progress_message:
            await progress_message.delete()

        if verbose:
            sections = []
            if banned_uids:
                bans = _build_message(banned_uids)
                sections.append(Section(Bold('GBanned Users'), *bans))
            if skipped_uids:
                bans = _build_message(skipped_uids)
                sections.append(Section(Bold('Skipped GBan'), *bans))

            await client.respond(event, MDTeXDocument(*sections))


def _build_message(bans: Dict[str, List[str]]) -> List[KeyValueItem]:
    sections = []
    for reason, uids in bans.items():
        sections.append(KeyValueItem(Bold('Reason'), reason))
        sections.append(KeyValueItem(Bold('IDs'), Code(', '.join(uids))))
    return sections


@events.register(events.NewMessage(outgoing=True, pattern=f'{cmd_prefix}ungban'))
async def ungban(event: NewMessage.Event) -> None:
    """Command to globally unban a user."""
    msg: Message = event.message
    client: KantekClient = event.client
    keyword_args, args = await helpers.get_args(event)
    await msg.delete()

    users_to_unban = [*args]
    if msg.is_reply:
        reply_msg: Message = await msg.get_reply_message()
        uid = reply_msg.from_id
        users_to_unban.append(uid)

    unbanned_users = []
    for uid in users_to_unban:
        if await client.db.banlist.get_user(uid):
            await client.ungban(uid)
            unbanned_users.append(str(uid))
    if unbanned_users:
        await client.respond(event, MDTeXDocument(
            Section(Bold('Un-GBanned Users'),
                    KeyValueItem(Bold('IDs'), Code(', '.join(unbanned_users))))))

        
KantekClient.commands.update({
    "gban": "Used for manual Gbans \n Usage : gban <id> <reason> \n Note: If more than 1 work for reason than use double quotes at the start and end"
})
        
