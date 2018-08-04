import logging
import re

import discord
from discord.ext import commands

from WolfBot import WolfUtils, WolfStatics

LOG = logging.getLogger("DakotaBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class UniversalBanList:
    """
    The UBL is a read-only module intentionally gimped on features. If a user sends a message, changes their username,
    or joins with a username containing a string found in the UBL, the user is immediately and automatically banned.

    This is a *very* aggressive anti-spam method, and should not be relied on for regular control. See AntiSpam instead.

    DO NOT EDIT THIS FILE WITHOUT TALKING TO KAZ AND CLOVER.
    """

    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot

        # Universal Ban List of phrases used by the bot. Any phrases here will trigger an instant ban.
        self._ubl_phrases = [
            "\u5350"  # Swastika unicode
        ]

        # UBL list of phrases to target *just usernames*.
        self._ubl_usernames = [
            "hitler",
            WolfStatics.Regex.INVITE_REGEX
        ]

        LOG.info("Loaded plugin!")

    async def filter_message(self, message: discord.Message, context: str = "new_message"):
        if not WolfUtils.should_process_message(message):
            return

        if message.author.permissions_in(message.channel).manage_messages:
            return

        for ubl_term in self._ubl_phrases:
            if re.search(ubl_term, message.content, re.IGNORECASE) is not None:
                await message.author.ban(reason=f"[AUTOMATIC BAN - UBL Module] User used UBL keyword `{ubl_term}`",
                                         delete_message_days=5)
                LOG.info("Banned UBL triggering user (context %s, keyword %s, from %s in %s): %s", context,
                         message.author, ubl_term, message.channel, message.content)

    async def on_message(self, message):
        await self.filter_message(message)

    # noinspection PyUnusedLocal
    async def on_message_edit(self, before, after):
        await self.filter_message(after, "edit")

    async def on_member_join(self, member: discord.Member):
        if member.guild_permissions.manage_guild:
            return

        blacklist = self._ubl_phrases + self._ubl_usernames

        for ubl_term in blacklist:
            if re.search(ubl_term, member.display_name, re.IGNORECASE) is not None:
                await member.ban(reason=f"[AutoBan - UBL Module] New user's name contains UBL keyword `{ubl_term}`",
                                 delete_message_days=0)
                LOG.info("Banned UBL triggering new join of user %s (matching UBL %s)", member, ubl_term)

    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if after.guild_permissions.manage_guild:
            return

        if before.nick == after.nick and before.name == after.name:
            return

        blacklist = self._ubl_phrases + self._ubl_usernames

        for ubl_term in blacklist:
            if after.nick is not None and re.search(ubl_term, after.nick, re.IGNORECASE) is not None:
                u_type = 'nickname'
            elif after.name is not None and re.search(ubl_term, after.name, re.IGNORECASE):
                u_type = 'username'
            else:
                continue

            await after.ban(reason=f"[AutoBan - UBL Module] User {after} changed {u_type} to include UBL "
                                   f"keyword {ubl_term}")
            LOG.info("Banned UBL triggering %s change of user %s (matching UBL %s)", u_type, after, ubl_term)


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(UniversalBanList(bot))
