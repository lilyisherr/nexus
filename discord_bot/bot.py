import discord
from discord.ext import commands, tasks
import logging
import asyncio
from config import BOT_TOKEN, NEXUS_PURPLE, NEXUS_ICON, NEXUS_GREEN

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("nexus-bot")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
intents.guilds = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None,
    activity=discord.Activity(type=discord.ActivityType.watching, name="nexusbeta.vercel.app"),
)


def _nexus_footer(embed):
    embed.set_footer(text="Nexus", icon_url=NEXUS_ICON)
    embed.timestamp = discord.utils.utcnow()
    return embed


class VerifyButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Verify", style=discord.ButtonStyle.green, custom_id="nexus_verify_btn", emoji="\u2705")
    async def verify_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user

        not_verified = discord.utils.get(guild.roles, name="Not Verified")
        verified = discord.utils.get(guild.roles, name="Verified")
        member_role = discord.utils.get(guild.roles, name="Member")

        roles_to_add = []
        roles_to_remove = []

        if verified:
            roles_to_add.append(verified)
        if member_role:
            roles_to_add.append(member_role)
        if not_verified and not_verified in member.roles:
            roles_to_remove.append(not_verified)

        try:
            if roles_to_add:
                await member.add_roles(*roles_to_add)
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove)
            await interaction.response.send_message("You're verified. Welcome to the server.", ephemeral=True)
            log.info(f"[VERIFY] {member} ({member.id}) verified in {guild.name}")
        except discord.Forbidden:
            await interaction.response.send_message("Something went wrong. Contact a moderator.", ephemeral=True)


@bot.event
async def on_ready():
    bot.add_view(VerifyButton())

    log.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    log.info(f"Connected to {len(bot.guilds)} server(s)")
    try:
        synced = await bot.tree.sync()
        log.info(f"Synced {len(synced)} slash command(s)")
    except Exception as e:
        log.error(f"Failed to sync commands: {e}")
    if not status_rotation_loop.is_running():
        status_rotation_loop.start()


@bot.event
async def on_member_join(member):
    guild = member.guild

    if member.bot:
        bots_role = discord.utils.get(guild.roles, name="Bots")
        if bots_role:
            try:
                await member.add_roles(bots_role)
                log.info(f"[AUTO-ROLE] Assigned Bots role to {member} (bot account)")
            except discord.Forbidden:
                pass
        return

    not_verified = discord.utils.get(guild.roles, name="Not Verified")
    if not_verified:
        try:
            await member.add_roles(not_verified)
            log.info(f"[JOIN] {member} joined {guild.name} - assigned Not Verified")
        except discord.Forbidden:
            pass

    welcome_ch = discord.utils.get(guild.text_channels, name="welcome")
    if welcome_ch:
        verify_ch = discord.utils.get(guild.text_channels, name="verify")
        embed = discord.Embed(
            title=f"Welcome to {guild.name}!",
            description=(
                f"Hey {member.mention}, glad you're here.\n\n"
                f"Before you can access the rest of the server, head over to "
                f"{'<#' + str(verify_ch.id) + '>' if verify_ch else '#verify'} "
                f"and click the verify button.\n\n"
                f"After that, check out #rules and #pick-your-roles to get set up."
            ),
            color=NEXUS_PURPLE,
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Member Count", value=f"#{guild.member_count:,}", inline=True)
        embed.add_field(name="Account Age", value=f"{(discord.utils.utcnow() - member.created_at).days} days", inline=True)
        _nexus_footer(embed)
        await welcome_ch.send(embed=embed)


@bot.event
async def on_member_remove(member):
    if member.bot:
        return

    guild = member.guild
    goodbye_ch = discord.utils.get(guild.text_channels, name="goodbye")
    if goodbye_ch:
        roles = [r.name for r in member.roles if r != guild.default_role and r.name not in ("Not Verified", "Verified", "Member")]
        embed = discord.Embed(
            description=f"**{member.display_name}** just left the server.",
            color=0x94A3B8,
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        if roles:
            embed.add_field(name="Roles", value=", ".join(roles[:8]), inline=False)
        join_date = member.joined_at
        if join_date:
            days = (discord.utils.utcnow() - join_date).days
            embed.add_field(name="Was here for", value=f"{days} day{'s' if days != 1 else ''}", inline=True)
        embed.add_field(name="Member Count", value=f"{guild.member_count:,}", inline=True)
        _nexus_footer(embed)
        await goodbye_ch.send(embed=embed)

    log.info(f"[LEAVE] {member} left {guild.name}")


ROTATING_STATUSES = [
    ("streaming", "YouTube live chats"),
    ("watching", "{members} members"),
    ("listening", "your stream chat"),
    ("competing", "YouTube Analytics"),
    ("streaming", "live stream data"),
    ("watching", "nexusbeta.vercel.app"),
    ("listening", "stream alerts"),
    ("watching", "{members} creators"),
    ("competing", "moderation speed"),
    ("streaming", "real-time analytics"),
    ("watching", "your YouTube channel"),
    ("listening", "YouTube API requests"),
    ("competing", "uptime records"),
    ("streaming", "Nexus Platform"),
    ("watching", "live chat moderation"),
    ("listening", "bot commands"),
    ("competing", "Beta testing"),
    ("streaming", "viewer stats"),
    ("watching", "for new streamers"),
    ("listening", "stream commands"),
    ("competing", "response time"),
    ("streaming", "channel growth"),
    ("watching", "YouTube dashboards"),
    ("listening", "live notifications"),
    ("competing", "server count"),
]

_status_index = 0


async def _update_presence():
    global _status_index
    kind, text = ROTATING_STATUSES[_status_index % len(ROTATING_STATUSES)]
    total_members = sum(g.member_count or 0 for g in bot.guilds)
    text = text.format(members=f"{total_members:,}")
    if kind == "streaming":
        activity = discord.Streaming(name=text, url="https://nexusbeta.vercel.app")
    elif kind == "competing":
        activity = discord.Activity(type=discord.ActivityType.competing, name=text)
    elif kind == "listening":
        activity = discord.Activity(type=discord.ActivityType.listening, name=text)
    else:
        activity = discord.Activity(type=discord.ActivityType.watching, name=text)
    await bot.change_presence(status=discord.Status.online, activity=activity)
    _status_index += 1


@tasks.loop(seconds=30)
async def status_rotation_loop():
    try:
        await _update_presence()
    except Exception:
        pass


@status_rotation_loop.before_loop
async def before_status_rotation():
    await bot.wait_until_ready()


@bot.event
async def on_guild_join(guild):
    log.info(f"Joined server: {guild.name} (ID: {guild.id})")


@bot.event
async def on_guild_remove(guild):
    log.info(f"Removed from server: {guild.name} (ID: {guild.id})")


async def load_cogs():
    cog_list = [
        "cogs.server_setup",
        "cogs.notifications",
        "cogs.moderation",
        "cogs.info",
        "cogs.logging",
        "cogs.owner",
    ]
    for cog in cog_list:
        try:
            await bot.load_extension(cog)
            log.info(f"Loaded cog: {cog}")
        except Exception as e:
            log.error(f"Failed to load cog {cog}: {e}")


async def main():
    if not BOT_TOKEN:
        log.error("DISCORD_BOT_TOKEN is not set. The bot cannot start without a valid token.")
        log.error("Set DISCORD_BOT_TOKEN in your environment variables.")
        return
    async with bot:
        await load_cogs()
        await bot.start(BOT_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
