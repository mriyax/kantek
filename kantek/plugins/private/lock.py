"""Plugin to manage the autobahn"""
import logging

from telethon import events
from telethon.errors import ChatNotModifiedError
from telethon.events import NewMessage
from telethon.tl.custom import Message
from telethon.tl.functions.messages import EditChatDefaultBannedRightsRequest
from telethon.tl.types import ChannelParticipantsAdmins, ChatBannedRights, InputPeerChannel

from config import cmd_prefix
from utils.client import KantekClient
from utils.mdtex import MDTeXDocument

__version__ = '0.1.0'

tlog = logging.getLogger('kantek-channel-log')


@events.register(events.NewMessage(outgoing=True, pattern=f'{cmd_prefix}lock'))
async def lock(event: NewMessage.Event) -> None:
    """Command to quickly lock a chat to readonly for normal users."""
    client: KantekClient = event.client
    chat: InputPeerChannel = await event.get_input_chat()
    try:
        await client(EditChatDefaultBannedRightsRequest(
            chat,
            banned_rights=ChatBannedRights(
                until_date=None,
                view_messages=None,
                send_messages=True,
                send_media=True,
                send_stickers=True,
                send_gifs=True,
                send_games=True,
                send_inline=True,
                send_polls=True,
                change_info=True,
                invite_users=True,
                pin_messages=True
            )))
        await client.respond(event, MDTeXDocument('Chat locked.'))
    except ChatNotModifiedError:
        await client.respond(event, MDTeXDocument('Chat already locked.'))
