#!/usr/bin/env python3

import datetime
import logging
import os
import sys
import traceback

import discord
from discord.ext import commands

from WolfBot import WolfConfig
from WolfBot import WolfStatics
from WolfBot import WolfUtils
from WolfBot.WolfStatics import Colors, ChannelKeys

BOT_CONFIG = WolfConfig.get_config()
LOCAL_STORAGE = WolfConfig.get_session_store()

initialized = False

# Determine restart reason (pretty mode) - HACK FOR BOT INIT
restart_reason = BOT_CONFIG.get("restartReason", "start")
start_status = discord.Status.idle

if restart_reason == "admin":
    start_activity = discord.Activity(name="Restarting...", type=discord.ActivityType.playing)
elif restart_reason == "update":
    start_activity = discord.Activity(name="Updating...", type=discord.ActivityType.playing)
else:
    start_activity = discord.Activity(name="Starting...", type=discord.ActivityType.playing)

# initialize our bot here
bot = commands.Bot(command_prefix=BOT_CONFIG.get('prefix', '/'), activity=start_activity, status=start_status)

# set up logging
LOCAL_STORAGE.set('logPath', 'logs/dakotabot-' + str(datetime.datetime.utcnow()).split(' ')[0] + '.log')
logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                    handlers=[logging.FileHandler(LOCAL_STORAGE.get('logPath'), 'a'),
                              logging.StreamHandler(sys.stdout)])
# WolfUtils.configure_loggers()
MASTER_LOGGER = logging.getLogger("DakotaBot")
MASTER_LOGGER.setLevel(logging.INFO)
LOG = MASTER_LOGGER.getChild('Core')


async def initialize():
    global restart_reason
    global start_activity
    global initialized

    # Delete temporary restart configs
    if restart_reason != "start":
        BOT_CONFIG.delete("restartReason")
        del start_activity
        restart_reason = "start"

    LOG.info("DakotaBot is online, running discord.py " + discord.__version__)

    # Lock the bot to a single guild
    if not BOT_CONFIG.get("developerMode", False):
        if BOT_CONFIG.get("guildId") is None:
            LOG.error("No Guild ID specified! Quitting.")
            exit(127)

        for guild in bot.guilds:
            if guild.id != BOT_CONFIG.get("guildId"):
                guild.leave()

    # Load plugins
    sys.path.insert(1, os.getcwd() + "/plugins/")

    bot.load_extension('BotAdmin')

    plugin_list = BOT_CONFIG.get('plugins', [])

    if BOT_CONFIG.get("developerMode", False):
        plugin_list = ["Debug"] + plugin_list

    for plugin in plugin_list:
        # noinspection PyBroadException
        try:
            bot.load_extension(plugin)
        except:  # This is a very hacky way to do this, but we need to persist module loading through a failure
            await on_error('initialize/load_plugin/' + plugin)

    # Inform on restart
    if BOT_CONFIG.get("restartNotificationChannel") is not None:
        channel = bot.get_channel(BOT_CONFIG.get("restartNotificationChannel"))
        await channel.send(embed=discord.Embed(
            title="Bot Manager",
            description="The bot has been successfully restarted, and is now online.",
            color=Colors.SUCCESS
        ))
        BOT_CONFIG.delete("restartNotificationChannel")

    initialized = True


@bot.event
async def on_ready():
    if not initialized:
        await initialize()

    bot_presence = BOT_CONFIG.get('presence', {"game": "DakotaBot", "type": 2, "status": "dnd"})

    await bot.change_presence(activity=discord.Activity(name=bot_presence['game'], type=bot_presence['type']),
                              status=discord.Status[bot_presence['status']])


@bot.event
async def on_guild_join(guild):
    if not BOT_CONFIG.get("developerMode", False):
        if guild.id != BOT_CONFIG.get("guildId"):
            guild.leave()


@bot.event
async def on_command_error(ctx, error: commands.CommandError):
    command_name = ctx.message.content.split(' ')[0][1:]

    # Handle cases where the calling user is missing a required permission.
    if isinstance(error, commands.MissingPermissions):
        if BOT_CONFIG.get("developerMode", False):
            await ctx.send(embed=discord.Embed(
                title="Command Handler",
                description="**You are not authorized to run `/{}`:**\n```{}```\n\nPlease ask a staff member for "
                            "assistance".format(command_name, str(error)),
                color=Colors.DANGER
            ))

        LOG.error("Encountered permission error when attempting to run command %s: %s", command_name, str(error))

    # Handle cases where the command is disabled.
    elif isinstance(error, commands.DisabledCommand):
        if BOT_CONFIG.get("developerMode", False):
            embed = discord.Embed(
                title="Command Handler",
                description="**The command `/{}` does not exist.** See `/help` for valid "
                            "commands.".format(command_name),
                color=Colors.DANGER
            )

            if ctx.message.author.guild_permissions.administrator:
                embed.set_footer(text="E_DISABLED_COMMAND")
            await ctx.send(embed=embed)

        LOG.error("Command %s is disabled.", command_name)

    # Handle cases where the command does not exist.
    elif isinstance(error, commands.CommandNotFound):
        if BOT_CONFIG.get("developerMode", False):
            await ctx.send(embed=discord.Embed(
                title="Command Handler",
                description="**The command `/{}` does not exist.** See `/help` for valid "
                            "commands.".format(command_name, ),
                color=Colors.DANGER
            ))

        LOG.error("Command %s does not exist to the system.", command_name)

    # Handle cases where a prerequisite command check failed to execute
    elif isinstance(error, commands.CheckFailure):
        await ctx.send(embed=discord.Embed(
            title="Command Handler",
            description="**The command `/{}` failed an execution check.** "
                        "Additional information may be provided below.".format(command_name),
            color=Colors.DANGER
        ).add_field(name="Error Log", value="```" + str(error) + "```", inline=False))

        LOG.error("Encountered check failure when attempting to run command %s: %s", command_name, str(error))

    # Handle cases where a command is run over a Direct Message without working over DMs
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.send(embed=discord.Embed(
            title="Command Handler",
            description="**The command `/{}` may not be run in a DM.** See `/help` for valid "
                        "commands.".format(command_name),
            color=Colors.DANGER
        ))

        LOG.error("Command %s may not be run in a direct message!", command_name)

    # Handle cases where a command is run missing a required argument
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=discord.Embed(
            title="Command Handler",
            description="**The command `/{}` could not run, because it is missing arguments.**\n"
                        "See `/help {}` for the arguments required.".format(command_name, command_name),
            color=Colors.DANGER
        ).add_field(name="Missing Parameter", value="`" + str(error).split(" ")[0] + "`", inline=True))
        LOG.error("Command %s was called with the wrong parameters.", command_name)
        return

    # Handle cases where an argument can not be parsed properly.
    elif isinstance(error, commands.BadArgument):
        await ctx.send(embed=discord.Embed(
            title="Command Handler",
            description="**The command `/{}` could not understand the arguments given.**\n"
                        "See `/help {}` and the error below to fix this issue.".format(command_name, command_name),
            color=Colors.DANGER
        ).add_field(name="Error Log", value="```" + str(error) + "```", inline=False))

        LOG.error("Command %s was unable to parse arguments: %s.", command_name, str(error))

    # Handle cases where the bot is missing a required execution permission.
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send(embed=discord.Embed(
            title="Command Handler",
            description="**The command `/{}` could not execute successfully, as the bot does not have a required"
                        "permission.**\nPlease make sure that the bot has the following permissions: "
                        "`{}`".format(command_name, ', '.join(error.missing_perms)),
            color=Colors.DANGER
        ))

        LOG.error("Bot is missing permissions %s to execute command %s", error.missing_perms, command_name)

    # Handle commands on cooldown
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(embed=discord.Embed(
            title="Command Handler",
            description="**The command `/{}` has been run too much recently!**\nPlease wait {} seconds until trying "
                        "again.".format(command_name, error.retry_after),
            color=Colors.DANGER
        ))

        LOG.error("Command %s was on cooldown, and is unable to be run for %s seconds. Cooldown: %s", command_name,
                  round(error.retry_after, 0), error.cooldown)

    # Handle any and all other error cases.
    else:
        await ctx.send(embed=discord.Embed(
            title="Bot Error Handler",
            description="The bot has encountered a fatal error running the command given. Logs are below.",
            color=Colors.DANGER
        ).add_field(name="Error Log", value="```" + str(error) + "```", inline=False))
        LOG.error("Error running command %s. See below for trace.\n%s",
                  ctx.message.content, ''.join(traceback.format_exception(type(error), error, error.__traceback__)))

        # Send it over to the main error logger as well.
        raise error


# noinspection PyUnusedLocal
@bot.event
async def on_error(event_method, *args, **kwargs):
    LOG.error('Exception in method %s:\n%s', event_method, traceback.format_exc())

    try:
        channel = BOT_CONFIG.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)

        if channel is None:
            LOG.warning('A logging channel is not set up! Error messages will not be forwarded to Discord.')
            return

        channel = bot.get_channel(channel)

        embed = discord.Embed(
            title="Bot Exception Handler",
            description=WolfUtils.trim_string(
                "Exception in method `" + event_method + "`:\n```" + traceback.format_exc() + "```", 2048, True),
            color=Colors.DANGER
        )

        await channel.send("<@{}>, an error has occurred with the bot. See attached "
                           "embed.".format(WolfStatics.__developers__[0]),
                           embed=embed)
    except Exception as e:
        LOG.critical("There was an error sending an error to the error channel.\n " + str(e))


@bot.event
async def on_message(message):
    if not WolfUtils.should_process_message(message):
        return

    if message.content.startswith(bot.command_prefix):
        if message.author.id in BOT_CONFIG.get('userBlacklist', []):
            LOG.info("Blacklisted user %s attempted to run command %s", message.author, message.content)
            return

        if message.content.lower().split(' ')[0][1:] in BOT_CONFIG.get('ignoredCommands', []):
            LOG.info("User %s ran an ignored command %s", message.author, message.content)
            return

        if message.content.lower().split(' ')[0].startswith('/r/'):
            LOG.info("User %s linked to subreddit %s, ignoring command", message.author, message.content)
            return

        if BOT_CONFIG.get('lockdown', False) and (message.author.id not in WolfStatics.__developers__):
            LOG.info("Lockdown mode is enabled for the bot. Command blocked.")
            return

        LOG.info("User %s ran %s", message.author, message.content)

        await bot.process_commands(message)


def get_developers():
    """
    Get a list of all registered bot developers.
    """
    return WolfStatics.__developers__


if __name__ == '__main__':
    bot.run(BOT_CONFIG['apiKey'])

    # Auto restart if a reason is present
    if BOT_CONFIG.get("restartReason") is not None:
        print("READY FOR RESTART!")
        os.execl(sys.executable, *([sys.executable] + sys.argv))
