"""Helper functions to aid with different tasks that dont require a client."""
import asyncio
import csv
import hashlib
import logging
import re
import urllib
from io import BytesIO
from typing import Dict, List, Tuple, Union

import logzero
import photohash
import requests
from faker import Faker
from PIL import Image
from requests import ConnectionError, ReadTimeout
from telethon import utils
from telethon.events import NewMessage
from telethon.tl.types import Channel, Chat, User

from utils import parsers
from utils.mdtex import Italic

INVITELINK_PATTERN = re.compile(r'(?:joinchat|join)(?:/|\?invite=)(.*|)')

logger: logging.Logger = logzero.logger


async def get_full_name(entity: Union[Channel, Chat, User]) -> str:
    """Return first_name + last_name if last_name exists else just first_name

    Args:
        user: The user

    Returns:
        The combined names
    """
    if isinstance(entity, User):
        if entity.deleted:
            return Italic('Deleted Account')
        elif entity.last_name and entity.first_name:
            return '{} {}'.format(entity.first_name, entity.last_name)
        elif entity.first_name:
            return entity.first_name
        elif entity.last_name:
            return entity.last_name
        else:
            return ''

    elif isinstance(entity, (Chat, Channel)):
        return entity.title

    return ''


async def get_args(event: NewMessage.Event) -> Tuple[Dict[str, str], List[str]]:
    """Get arguments from a event

    Args:
        event: The event

    Returns:
        Parsed arguments as returned by parser.parse_arguments()
    """
    _args = event.message.raw_text.split()[1:]
    return parsers.parse_arguments(' '.join(_args))


async def rose_csv_to_dict(filename: str) -> List[Dict[str, str]]:
    """Convert a fedban list from Rose to a json that can be imported into MySQLDB

    Args:
        filename: The name of the csv

    Returns:

    """
    bans = []
    with open(filename, encoding='utf-8', newline='') as f:  #
        csv_file = csv.reader(f, delimiter=',')
        # skip the header
        next(csv_file, None)
        for line in csv_file:
            _id = line[0]
            reason = line[-1]
            bans.append({'id': _id, 'reason': reason})
    return bans


async def resolve_invite_link(link):
    """Method to work around a bug in telethon 1.6 and 1.7 that makes the resolve_invite_link method
    unable to parse tg://invite style links

    This is temporary and will be removed

    Args:
        link:

    Returns:
        Same as telethons method

    """
    encoded_link = re.search(INVITELINK_PATTERN, link)
    if encoded_link is not None:
        encoded_link = encoded_link.group(1)
        invite_link = f't.me/joinchat/{encoded_link}'
        return utils.resolve_invite_link(invite_link)
    else:
        return None, None, None


async def netloc(url: str) -> str:
    return urllib.parse.urlparse(url).netloc


def hash_file(file: bytes):
    hasher = hashlib.sha512()
    hasher.update(file)
    return hasher.hexdigest()


async def hash_photo(photo):
    loop = asyncio.get_event_loop()
    pil_photo = Image.open(BytesIO(photo))
    photo_hash = await loop.run_in_executor(None, photohash.average_hash, pil_photo)
    return str(photo_hash)
