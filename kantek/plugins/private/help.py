"""Get information about commands."""
import logging

from telethon import events
from telethon.events import NewMessage

from config import cmd_prefix
from utils.client import KantekClient
from utils.helpers import get_args

__version__ = '0.0.1'

tlog = logging.getLogger('kantek-channel-log')


@events.register(events.NewMessage(outgoing=True, pattern=f'{cmd_prefix}h(elp)?'))
async def help(event: NewMessage.Event) -> None:
    """Command to get a list of all the commands stored in the dict."""
    client: KantekClient = event.client
    commands: dict = KantekClient.commands
    _, args = await get_args(event)

    commands_list = []
    noncommands_list = []
    available = "**Available Kantek commands:**"
    unavailable = "\n\n**Commands not in Kantek or have help:**"

    if args:
        for command in args:
            info = commands.get(command, False)
            if info:
                commands_list.append(f"\n  **{command}:** {info}")
            else:
                noncommands_list.append(f"\n  **{command}**")
    else:
        for command, info in commands.items():
            commands_list.append(f"\n  **{command}**")

    if commands_list or noncommands_list:
        if commands_list and noncommands_list:
            response = available + "".join(commands_list)
            response += unavailable + "".join(noncommands_list)
        elif commands_list and not noncommands_list:
            response = available + "".join(commands_list)
        elif not commands_list and noncommands_list:
            response = unavailable + "".join(noncommands_list)
    else:
        response = "There isn't any help for the available commands."

    await client.respond(event, response)
