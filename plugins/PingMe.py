import logging
import random

import discord
from discord.ext import commands

from WolfBot import WolfConfig, WolfUtils

LOG = logging.getLogger("DakotaBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class PingMe:
    """
    A very simple method responsible for handling cases where the bot is pinged (in non-commands).
    """

    def __init__(self, bot: discord.ext.commands.Bot):
        self._bot = bot
        self._config = WolfConfig.get_config()

        LOG.info("Loaded plugin!")

    async def on_message(self, message: discord.Message):
        possible_replies = ["aroowooooo", "rooo", "woorooro", "arowwo"]

        if not WolfUtils.should_process_message(message):
            return

        if message.content.startswith(self._bot.command_prefix):
            return

        bot_mention = f"<@{self._bot.user.id}>"

        # Don't let people ping Dakota to get a response.
        if bot_mention == message.content:
            return

        if bot_mention in message.content:
            await message.channel.send(self.husky_speak())

    @commands.command(name="husky", brief="Act like a husky.")
    @commands.has_permissions(manage_messages=True)
    async def be_a_husky(self, ctx: commands.Context, num: int = 1):
        """
        Channel your inner husky!

        Generate a string of husky-like dialogue (huskyspeak) and post it to the current chat. You may control the
        number of "lines" of dialogue generated by using the "num" parameter.

        Huskyspeak is generated (more or less) by choosing a "prefix" like `ar`, `aw`, `r` or `w` and then appending a
        random number of zeroes. This isn't exactly how a husky will speak, but it's probably close enough. Maybe.
        I don't know; I'm a wolf, not a husky. Stop asking me to be a husky pls thx.

        Parameters:
            num - The number of lines of huskyspeak to generate.

        Caveats:
            1. This command may have an accident on the rug if not let out in time.
            2. This command may eat your shoes if you do not give it the attention it wants.
            3. This command may steal food from the fridge if it is not fed in time.
            4. This command may cause "zoomies" knocking over the plant on the coffee table.
            5. The above caveat is choosen randomly and you have no way of telling. You may be trying to stop the wrong
               caveat altogether. I don't know.

            6. This command may cause other nearby huskies to start talking and not shut up for at least five minutes.
            7. This command will make nearby wolves annoyed at the incessant chattering.
            8. This command will not work on Alaskan Malamutes or anything above low-content wolfdogs.
            9. This command may work unexpectedly on furries that are part-Husky. Caution is advised when running this
               command at Anthrocon or Midwest Fur Fest.z
        """
        huskies = []

        for _ in range(num):
            huskies.append(self.husky_speak())

        await ctx.send("\n".join(huskies))

    @staticmethod
    def husky_speak(seed=None):
        rng = random.Random(seed)
        verbs = ["oo", "roo", "woo", "awoo", "aroo"]

        word_count = random.randint(1, 5)
        words = []

        for _ in range(word_count):
            w_verbs = []
            w_length = random.randint(1, len(verbs))

            for _ in range(w_length):
                verb = ""

                mode = rng.randint(0, 4)
                if mode <= 2:
                    verb += rng.choice(["aw", "r", "w", "ar"])
                elif mode <= 3:
                    verb += rng.choice(["awr", "arw", "r", "aw"])

                verb += "o" * rng.randint(2, 3)

                w_verbs.append(verb)

            words.append("".join(w_verbs))

        return " ".join(words)


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(PingMe(bot))
