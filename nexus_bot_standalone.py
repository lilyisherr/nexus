import subprocess
import sys

REQUIRED_PACKAGES = ["discord.py", "aiohttp", "python-dotenv"]

def install_dependencies():
    for pkg in REQUIRED_PACKAGES:
        try:
            if pkg == "discord.py":
                import discord
            elif pkg == "aiohttp":
                import aiohttp
            elif pkg == "python-dotenv":
                import dotenv
        except ImportError:
            print(f"Installing {pkg}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
            print(f"Installed {pkg}")

install_dependencies()

import os
import datetime
import asyncio
import logging
import time
import json
from threading import Thread

import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
from dotenv import load_dotenv

load_dotenv()
if not os.getenv("DISCORD_BOT_TOKEN"):
    load_dotenv("nexus_bot.env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("nexus-bot")

BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
NEXUS_API_URL = os.getenv("NEXUS_API_URL", "https://nexusbeta.vercel.app")
NEXUS_API_KEY = os.getenv("NEXUS_API_KEY", "")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

bot_start_time = None
bot_connected = False

NEXUS_PURPLE = 0x6366F1
NEXUS_BLUE = 0x818CF8
NEXUS_GREEN = 0x10B981
NEXUS_ICON = "https://nexusbeta.vercel.app/static/img/logo.png"

STAFF_ROLES = ["Owner", "Admin", "Developer", "Moderator", "Support Team"]

ROLE_CONFIG = {
    "Owner": {"color": 0x9B59B6, "permissions": {"administrator": True}, "hoist": True, "position": 50},
    "Admin": {"color": 0xEF4444, "permissions": {"administrator": True}, "hoist": True, "position": 49},
    "Developer": {"color": 0x5865F2, "permissions": {"manage_messages": True, "manage_channels": True, "view_audit_log": True, "manage_roles": True}, "hoist": True, "position": 48},
    "Moderator": {
        "color": 0xF59E0B,
        "permissions": {
            "manage_messages": True, "kick_members": True, "ban_members": True,
            "mute_members": True, "deafen_members": True, "move_members": True,
            "manage_nicknames": True, "view_audit_log": True,
        },
        "hoist": True, "position": 47,
    },
    "Support Team": {"color": 0x10B981, "permissions": {"manage_messages": True, "manage_nicknames": True}, "hoist": True, "position": 46},
    "Bots": {"color": 0x5865F2, "permissions": {}, "hoist": True, "position": 45},
    "Beta Tester": {"color": 0x8B5CF6, "permissions": {}, "hoist": True, "position": 44},
    "Streamer": {"color": 0xEC4899, "permissions": {"attach_files": True, "embed_links": True}, "hoist": True, "position": 43},
    "Nexus User": {"color": 0x6366F1, "permissions": {}, "hoist": True, "position": 42},
    "Verified": {"color": 0x2ECC71, "permissions": {}, "hoist": False, "position": 41},
    "Not Verified": {"color": 0x95A5A6, "permissions": {}, "hoist": True, "position": 1},
    "Announcement Pings": {"color": 0xE74C3C, "permissions": {}, "hoist": False, "mentionable": True, "position": 30},
    "Website Updates": {"color": 0x3498DB, "permissions": {}, "hoist": False, "mentionable": True, "position": 29},
    "Notifications": {"color": 0x3B82F6, "permissions": {}, "hoist": False, "mentionable": True, "position": 28},
    "Updates": {"color": 0x14B8A6, "permissions": {}, "hoist": False, "mentionable": True, "position": 27},
    "Member": {"color": 0x94A3B8, "permissions": {}, "hoist": False, "position": 10},
    "Red": {"color": 0xE74C3C, "permissions": {}, "hoist": False, "position": 51},
    "Blue": {"color": 0x3498DB, "permissions": {}, "hoist": False, "position": 51},
    "Green": {"color": 0x2ECC71, "permissions": {}, "hoist": False, "position": 51},
    "Purple": {"color": 0x9B59B6, "permissions": {}, "hoist": False, "position": 51},
    "Orange": {"color": 0xE67E22, "permissions": {}, "hoist": False, "position": 51},
    "Pink": {"color": 0xFD79A8, "permissions": {}, "hoist": False, "position": 51},
    "Yellow": {"color": 0xF1C40F, "permissions": {}, "hoist": False, "position": 51},
    "Teal": {"color": 0x1ABC9C, "permissions": {}, "hoist": False, "position": 51},
}

CHANNEL_CONFIG = {
    "VERIFICATION": {
        "channels": [
            {"name": "verify", "type": "text", "topic": "Click the button below to verify and access the server.", "verify_only": True},
        ]
    },
    "WELCOME & INFO": {
        "channels": [
            {"name": "welcome", "type": "text", "topic": "Welcome to the Nexus community. New members appear here.", "read_only": True, "verified_only": True},
            {"name": "goodbye", "type": "text", "topic": "Farewell messages for departing members.", "read_only": True, "verified_only": True},
            {"name": "rules", "type": "text", "topic": "Server rules. Read them.", "read_only": True, "verified_only": True},
            {"name": "pick-your-roles", "type": "text", "topic": "Grab your notification and color roles.", "read_only": True, "verified_only": True},
            {"name": "faq", "type": "text", "topic": "Everything you need to know about Nexus.", "read_only": True, "verified_only": True},
        ]
    },
    "ANNOUNCEMENTS": {
        "channels": [
            {"name": "announcements", "type": "text", "topic": "Official Nexus announcements.", "read_only": True, "verified_only": True},
            {"name": "changelog", "type": "text", "topic": "Nexus platform updates and patch notes.", "read_only": True, "verified_only": True},
            {"name": "live-alerts", "type": "text", "topic": "Automatic go-live notifications.", "read_only": True, "verified_only": True},
        ]
    },
    "GENERAL": {
        "channels": [
            {"name": "general", "type": "text", "topic": "General discussion.", "verified_only": True},
            {"name": "off-topic", "type": "text", "topic": "Anything goes -- memes, random stuff, whatever.", "verified_only": True},
            {"name": "media", "type": "text", "topic": "Share images, videos, clips.", "verified_only": True},
            {"name": "stream-chat", "type": "text", "topic": "Talk about streaming, tips, gear.", "verified_only": True},
            {"name": "self-promo", "type": "text", "topic": "Drop your channel link. One post per day.", "verified_only": True},
        ]
    },
    "NEXUS PLATFORM": {
        "channels": [
            {"name": "nexus-help", "type": "text", "topic": "Need help with Nexus? Ask here.", "verified_only": True},
            {"name": "bug-reports", "type": "text", "topic": "Found a bug? Report it.", "verified_only": True},
            {"name": "feature-requests", "type": "text", "topic": "Suggest features you want.", "verified_only": True},
        ]
    },
    "NOTIFICATIONS": {
        "channels": [
            {"name": "milestone-alerts", "type": "text", "topic": "Subscriber milestone notifications.", "read_only": True, "verified_only": True},
        ]
    },
    "STAFF": {
        "hidden": True,
        "channels": [
            {"name": "mod-chat", "type": "text", "topic": "Private staff discussion.", "staff_only": True},
            {"name": "mod-log", "type": "text", "topic": "Automated moderation log.", "staff_only": True, "read_only": True},
            {"name": "admin-chat", "type": "text", "topic": "Admin-only.", "admin_only": True},
            {"name": "dev-updates", "type": "text", "topic": "Current development progress.", "staff_only": True},
            {"name": "staff-voice", "type": "voice", "staff_only": True},
        ]
    },
    "VOICE": {
        "channels": [
            {"name": "General Voice", "type": "voice", "verified_only": True},
            {"name": "Stream Talk", "type": "voice", "verified_only": True},
            {"name": "AFK", "type": "voice", "afk": True, "verified_only": True},
        ]
    },
}

RULES_TEXT = """**1. Be respectful.** No harassment, hate speech, slurs, or personal attacks. We want everyone to feel welcome here.

**2. No spam.** Don't flood channels with repeated messages, excessive caps, or bot commands outside designated channels.

**3. Keep it relevant.** Post in the right channel. Nexus help goes in nexus-help, streaming talk goes in the streaming channels.

**4. Self-promo has limits.** Share your channel or videos in #self-promo only. One post per day. Don't DM people to promote yourself.

**5. No NSFW content.** This is a clean server. Keep it appropriate.

**6. Don't mini-mod.** If someone breaks a rule, ping a moderator or use the report feature. Don't try to enforce rules yourself.

**7. No leaking or piracy.** Don't share paid content, cracked software, API keys, or tokens.

**8. English only in public channels.** Keeps moderation manageable for the team.

**9. Listen to staff.** Moderators, developers, and admins have the final say on all matters.

Breaking these rules can result in a warning, mute, kick, or ban depending on severity and repeat offenses."""

WELCOME_MESSAGE = """Welcome to the **Nexus** community.

Nexus is a YouTube bot and analytics platform built for live streamers. We're currently in beta and actively developing new features.

**Get started:**
1. Read the rules in #rules
2. Grab your roles in #pick-your-roles
3. Chat in #general
4. If you need help with Nexus, head to #nexus-help

**Useful links:**
[Website](https://nexusbeta.vercel.app) | [Bot Dashboard](https://nexusbeta.vercel.app/bot) | [Help Center](https://nexusbeta.vercel.app/help)"""

FAQ_SECTIONS = [
    {
        "title": "About Nexus",
        "color": NEXUS_PURPLE,
        "fields": [
            ("What is Nexus?", "Nexus is a YouTube bot and analytics platform designed for live streamers. It handles chat moderation, custom commands, timed messages, viewer tracking, and channel analytics -- all from one dashboard."),
            ("Is Nexus free?", "Yes. Nexus is completely free during the beta period. No credit card or payment info required."),
            ("What platforms does Nexus support?", "YouTube is fully supported right now. Twitch, Kick, and Twitter/X integrations are planned and in development."),
            ("Who made Nexus?", "Nexus is an independent project. You can reach the team through this Discord server or the contact page on the website."),
        ]
    },
    {
        "title": "Getting Started",
        "color": NEXUS_BLUE,
        "fields": [
            ("How do I sign up?", "Go to [nexusbeta.vercel.app](https://nexusbeta.vercel.app) and sign in with your Google account. Your YouTube channel gets linked automatically."),
            ("How do I set up the YouTube bot?", "After signing in, go to your channel settings and enable the bot. Then add **nexusbetabot** as a moderator in YouTube Studio under Settings > Community > Automated Filters."),
            ("Why does the bot need moderator access?", "The bot needs to read and send messages in your YouTube live chat. YouTube requires moderator permissions for third-party bots to interact with chat."),
            ("Can I use Nexus on multiple channels?", "Currently Nexus supports one YouTube channel per account. Multi-channel support is being worked on."),
        ]
    },
    {
        "title": "Bot Features",
        "color": NEXUS_GREEN,
        "fields": [
            ("What can the YouTube bot do?", "Spam filtering, link filtering, caps filtering, custom commands, timed messages, viewer tracking, chat logging, auto-greet new viewers, and more."),
            ("How do custom commands work?", "Create commands from the dashboard with custom responses, cooldowns, and permission levels. Viewers trigger them by typing the command name in chat."),
            ("What about the Discord bot?", "The Nexus Discord bot handles server setup, moderation, logging, role management, live notifications, and connects to the Nexus dashboard."),
            ("Can I import commands from Nightbot?", "Yes. Go to your channel settings on the dashboard, find the import section, and paste your Nightbot commands in the `!command response` format."),
        ]
    },
    {
        "title": "Dashboard & Analytics",
        "color": 0xF59E0B,
        "fields": [
            ("What analytics does Nexus track?", "Subscriber growth over time, view counts, video performance, stream session data (peak viewers, duration, chat activity), and viewer engagement metrics."),
            ("How do I access the Discord bot dashboard?", "Go to [nexusbeta.vercel.app/bot](https://nexusbeta.vercel.app/bot) and sign in with Discord. You can configure per-server settings from there."),
            ("Can I export my data?", "Yes. Go to Settings > Data Management on the main dashboard to export your data as JSON or clear specific logs."),
        ]
    },
    {
        "title": "Troubleshooting",
        "color": 0xEF4444,
        "fields": [
            ("The bot isn't responding in my YouTube chat.", "Make sure nexusbetabot is added as a moderator in YouTube Studio, the bot is toggled on in your dashboard, and you have an active live stream running."),
            ("My channel stats aren't updating.", "Stats sync automatically but can take a few minutes. You can also manually sync from the Videos page. There's a 5-minute cooldown between syncs."),
            ("I'm getting an error when I try to log in.", "Clear your browser cookies, make sure you're using a Google account that has a YouTube channel, and try again. If the issue persists, ask in #nexus-help."),
            ("How do I report a bug?", "Post in #bug-reports with a description of what happened, what you expected, and a screenshot if possible."),
        ]
    },
]

ROLE_EMOJI_MAP = {
    "\U0001f514": "Notifications",
    "\U0001f4e2": "Announcement Pings",
    "\U0001f310": "Website Updates",
    "\U0001f4f0": "Updates",
}

COLOR_ROLE_EMOJI_MAP = {
    "\u2764\ufe0f": "Red",
    "\U0001f499": "Blue",
    "\U0001f49a": "Green",
    "\U0001f49c": "Purple",
    "\U0001f9e1": "Orange",
    "\U0001f49f": "Pink",
    "\U0001f49b": "Yellow",
    "\U0001f90d": "Teal",
}

ALL_COLOR_ROLES = list(COLOR_ROLE_EMOJI_MAP.values())


def _nexus_footer(embed):
    embed.set_footer(text="Nexus", icon_url=NEXUS_ICON)
    embed.timestamp = discord.utils.utcnow()
    return embed


def live_notification(channel_name, stream_title, stream_url, thumbnail_url=None, subscriber_count=0, viewer_count=0):
    embed = discord.Embed(title=stream_title or "Live Stream", url=stream_url, color=NEXUS_PURPLE)
    embed.set_author(name=f"{channel_name} is now live on YouTube!", url=stream_url, icon_url=thumbnail_url or "")
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    embed.add_field(name="Channel", value=f"[{channel_name}]({stream_url})", inline=True)
    embed.add_field(name="Platform", value="YouTube", inline=True)
    if subscriber_count > 0:
        embed.add_field(name="Subscribers", value=f"{subscriber_count:,}", inline=True)
    embed.add_field(name="\u200b", value=f"**[Watch Stream]({stream_url})**", inline=False)
    return _nexus_footer(embed)


def milestone_notification(channel_name, milestone, subscriber_count, thumbnail_url=None, channel_url=None):
    milestones_emoji = {100: "\U0001f389", 500: "\U0001f389", 1000: "\U0001f973", 5000: "\U0001f525", 10000: "\U0001f525", 25000: "\u2b50", 50000: "\u2b50", 100000: "\U0001f48e", 500000: "\U0001f48e", 1000000: "\U0001f451"}
    emoji = milestones_emoji.get(milestone, "\U0001f389")
    embed = discord.Embed(title=f"{emoji} {channel_name} hit {milestone:,} subscribers!", description=f"Current count: **{subscriber_count:,}**", color=0xF59E0B)
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    if channel_url:
        embed.add_field(name="Channel", value=f"[Visit on YouTube]({channel_url})", inline=False)
    return _nexus_footer(embed)


def success_embed(title, description):
    e = discord.Embed(title=title, description=description, color=NEXUS_GREEN)
    return _nexus_footer(e)


def error_embed(title, description):
    e = discord.Embed(title=title, description=description, color=0xEF4444)
    return _nexus_footer(e)


def info_embed(title, description):
    e = discord.Embed(title=title, description=description, color=NEXUS_BLUE)
    return _nexus_footer(e)


class NexusAPIClient:
    def __init__(self):
        self.base_url = NEXUS_API_URL.rstrip("/")
        self.api_key = NEXUS_API_KEY

    def _headers(self):
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-Nexus-Bot-Key"] = self.api_key
        return headers

    async def get_user_by_discord_id(self, discord_id):
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/discord/user/{discord_id}"
                async with session.get(url, headers=self._headers(), timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception:
            pass
        return None

    async def get_user_channels(self, discord_id):
        user = await self.get_user_by_discord_id(discord_id)
        if not user:
            return []
        return user.get("channels", [])

    async def send_log(self, data):
        if not self.api_key:
            return
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/bot/api/logs"
                async with session.post(url, json=data, headers=self._headers(), timeout=aiohttp.ClientTimeout(total=10)):
                    pass
        except Exception:
            pass

    async def send_notification(self, notification_type, data):
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/discord/notify"
                payload = {"type": notification_type, **data}
                async with session.post(url, json=payload, headers=self._headers(), timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception:
            pass
        return None


nexus_api = NexusAPIClient()

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
        nexus_user = discord.utils.get(guild.roles, name="Nexus User")

        roles_to_add = []
        roles_to_remove = []

        if verified:
            roles_to_add.append(verified)
        if member_role:
            roles_to_add.append(member_role)
        if nexus_user:
            roles_to_add.append(nexus_user)
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


@bot.event
async def on_ready():
    global bot_start_time, bot_connected
    bot_start_time = time.time()
    bot_connected = True

    bot.add_view(VerifyButton())

    log.info("=" * 60)
    log.info("  NEXUS DISCORD BOT - STANDALONE")
    log.info("=" * 60)
    log.info(f"  Bot User     : {bot.user} (ID: {bot.user.id})")
    log.info(f"  Discord.py   : {discord.__version__}")
    log.info(f"  Servers      : {len(bot.guilds)}")
    log.info(f"  Total Users  : {sum(g.member_count or 0 for g in bot.guilds)}")
    log.info(f"  Latency      : {round(bot.latency * 1000)}ms")
    log.info("=" * 60)

    for guild in bot.guilds:
        log.info(f"  Connected to server: {guild.name} (ID: {guild.id}) - {guild.member_count} members")

    log.info("-" * 60)
    log.info("  Syncing slash commands...")
    try:
        synced = await bot.tree.sync()
        log.info(f"  Synced {len(synced)} slash command(s) globally")
        for cmd in synced:
            log.info(f"    /{cmd.name} - {cmd.description}")
    except Exception as e:
        log.error(f"  Failed to sync commands: {e}")

    log.info("-" * 60)
    log.info(f"  API URL      : {NEXUS_API_URL}")
    log.info(f"  API Key      : {'Configured' if NEXUS_API_KEY else 'NOT SET'}")
    log.info(f"  Guild ID     : {GUILD_ID if GUILD_ID else 'Not set'}")

    log.info("-" * 60)
    log.info("  Checking Nexus Dashboard connection...")
    dashboard_ok = await _check_dashboard_connection()
    if dashboard_ok:
        log.info("  Nexus Dashboard: CONNECTED")
    else:
        log.warning("  Nexus Dashboard: NOT REACHABLE")

    log.info("-" * 60)
    log.info("  Sending heartbeat to dashboard...")
    await _send_heartbeat()

    if not heartbeat_loop.is_running():
        heartbeat_loop.start()
    if not status_rotation_loop.is_running():
        status_rotation_loop.start()

    log.info("=" * 60)
    log.info("  BOT IS ONLINE AND READY")
    log.info("=" * 60)


async def _check_dashboard_connection():
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{NEXUS_API_URL.rstrip('/')}/bot/"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                return resp.status == 200
    except Exception:
        return False


async def _send_heartbeat():
    if not NEXUS_API_KEY:
        log.warning("  No API key set, skipping heartbeat")
        return False
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{NEXUS_API_URL.rstrip('/')}/bot/api/heartbeat"
            payload = {
                "bot_id": str(bot.user.id) if bot.user else "",
                "bot_name": str(bot.user) if bot.user else "",
                "guild_count": len(bot.guilds),
                "user_count": sum(g.member_count or 0 for g in bot.guilds),
                "latency_ms": round(bot.latency * 1000),
                "uptime_seconds": int(time.time() - bot_start_time) if bot_start_time else 0,
                "status": "online",
            }
            headers = {"Content-Type": "application/json", "X-Nexus-Bot-Key": NEXUS_API_KEY}
            async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    log.info("  Heartbeat sent successfully")
                    return True
                else:
                    log.warning(f"  Heartbeat response: {resp.status}")
                    return False
    except Exception as e:
        log.warning(f"  Heartbeat failed: {e}")
        return False


@tasks.loop(minutes=2)
async def heartbeat_loop():
    await _send_heartbeat()


@heartbeat_loop.before_loop
async def before_heartbeat():
    await bot.wait_until_ready()


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


@bot.event
async def on_guild_join(guild):
    log.info(f"[+] Joined server: {guild.name} (ID: {guild.id}) - {guild.member_count} members")
    log.info(f"    Now in {len(bot.guilds)} server(s)")
    await _update_presence()
    await _send_heartbeat()


@bot.event
async def on_guild_remove(guild):
    log.info(f"[-] Removed from server: {guild.name} (ID: {guild.id})")
    log.info(f"    Now in {len(bot.guilds)} server(s)")
    await _update_presence()
    await _send_heartbeat()


@bot.event
async def on_disconnect():
    global bot_connected
    bot_connected = False
    log.warning("Bot disconnected from Discord gateway")


@bot.event
async def on_resumed():
    global bot_connected
    bot_connected = True
    log.info("Bot reconnected to Discord gateway")


class ServerSetup(commands.Cog):
    def __init__(self, b):
        self.bot = b

    def _build_overwrites(self, guild, ch_data, created_roles):
        overwrites = {}

        if ch_data.get("verify_only"):
            not_verified = created_roles.get("Not Verified")
            verified = created_roles.get("Verified")
            overwrites[guild.default_role] = discord.PermissionOverwrite(view_channel=False)
            if not_verified:
                overwrites[not_verified] = discord.PermissionOverwrite(view_channel=True, send_messages=False, read_message_history=True)
            if verified:
                overwrites[verified] = discord.PermissionOverwrite(view_channel=False)
            if guild.me:
                overwrites[guild.me] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
            return overwrites or None

        if ch_data.get("admin_only"):
            overwrites[guild.default_role] = discord.PermissionOverwrite(view_channel=False)
            admin_role = created_roles.get("Admin")
            if admin_role:
                overwrites[admin_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            if guild.me:
                overwrites[guild.me] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
            return overwrites or None

        if ch_data.get("staff_only"):
            overwrites[guild.default_role] = discord.PermissionOverwrite(view_channel=False)
            for staff_name in STAFF_ROLES:
                r = created_roles.get(staff_name)
                if r:
                    perms = discord.PermissionOverwrite(view_channel=True, read_message_history=True)
                    if ch_data.get("read_only"):
                        perms.send_messages = False
                    else:
                        perms.send_messages = True
                    overwrites[r] = perms
            if guild.me:
                overwrites[guild.me] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
            return overwrites or None

        if ch_data.get("role_restricted"):
            role_name = ch_data["role_restricted"]
            restricted_role = created_roles.get(role_name)
            overwrites[guild.default_role] = discord.PermissionOverwrite(view_channel=False)
            if restricted_role:
                overwrites[restricted_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            for staff_name in STAFF_ROLES:
                r = created_roles.get(staff_name)
                if r:
                    overwrites[r] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            if guild.me:
                overwrites[guild.me] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
            return overwrites or None

        if ch_data.get("verified_only"):
            not_verified = created_roles.get("Not Verified")
            verified = created_roles.get("Verified")
            overwrites[guild.default_role] = discord.PermissionOverwrite(view_channel=False)
            if verified:
                if ch_data.get("read_only"):
                    overwrites[verified] = discord.PermissionOverwrite(view_channel=True, send_messages=False, add_reactions=ch_data.get("name") == "pick-your-roles", read_message_history=True)
                else:
                    overwrites[verified] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            if not_verified:
                overwrites[not_verified] = discord.PermissionOverwrite(view_channel=False)
            for staff_name in STAFF_ROLES:
                r = created_roles.get(staff_name)
                if r:
                    overwrites[r] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            if guild.me:
                overwrites[guild.me] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
            return overwrites or None

        if ch_data.get("read_only"):
            overwrites[guild.default_role] = discord.PermissionOverwrite(view_channel=True, send_messages=False, add_reactions=False)
            for staff_name in STAFF_ROLES:
                r = created_roles.get(staff_name)
                if r:
                    overwrites[r] = discord.PermissionOverwrite(send_messages=True)
            if guild.me:
                overwrites[guild.me] = discord.PermissionOverwrite(send_messages=True)

        return overwrites or None

    @app_commands.command(name="setup-server", description="Build the full Nexus server (roles, channels, content). Admin only.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_server(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        status = []
        suppress_logging(guild.id)

        try:
            await interaction.followup.send("Setting up roles...", ephemeral=True)

            created_roles = {}
            sorted_roles = sorted(ROLE_CONFIG.items(), key=lambda x: x[1].get("position", 0))
            for role_name, role_data in sorted_roles:
                existing = discord.utils.get(guild.roles, name=role_name)
                if existing:
                    created_roles[role_name] = existing
                    continue
                perms = discord.Permissions()
                for perm_name, perm_value in role_data.get("permissions", {}).items():
                    setattr(perms, perm_name, perm_value)
                role = await guild.create_role(
                    name=role_name, color=discord.Color(role_data["color"]),
                    permissions=perms, hoist=role_data.get("hoist", False),
                    mentionable=role_data.get("mentionable", False),
                )
                created_roles[role_name] = role
                status.append(f"Created role: {role_name}")
                await asyncio.sleep(0.5)

            bot_top = guild.me.top_role.position if guild.me else 0
            role_positions = {}
            for role_name, role_data in ROLE_CONFIG.items():
                r = created_roles.get(role_name)
                if r and r != guild.default_role:
                    target = min(role_data.get("position", 0), bot_top - 1)
                    if target > 0:
                        role_positions[r] = target
            if role_positions:
                try:
                    await guild.edit_role_positions(positions=role_positions)
                    status.append("Reordered roles in hierarchy")
                except (discord.Forbidden, discord.HTTPException):
                    status.append("Could not reorder roles (need higher bot role)")
                await asyncio.sleep(0.5)

            if guild.owner:
                owner_role = created_roles.get("Owner")
                if owner_role and owner_role not in guild.owner.roles:
                    try:
                        await guild.owner.add_roles(owner_role)
                        status.append(f"Assigned Owner role to {guild.owner.display_name}")
                    except discord.Forbidden:
                        status.append("Could not assign Owner role to server owner (permissions)")
                    await asyncio.sleep(0.3)

            bots_role = created_roles.get("Bots")
            if bots_role and guild.me and bots_role not in guild.me.roles:
                try:
                    await guild.me.add_roles(bots_role)
                    status.append("Assigned Bots role to Nexus Bot")
                except discord.Forbidden:
                    pass
                await asyncio.sleep(0.3)

            await interaction.followup.send("Setting up channels...", ephemeral=True)

            for category_name, category_data in CHANNEL_CONFIG.items():
                existing_cat = discord.utils.get(guild.categories, name=category_name)
                cat_overwrites = {}
                if category_data.get("hidden"):
                    cat_overwrites[guild.default_role] = discord.PermissionOverwrite(view_channel=False)
                    for staff_name in STAFF_ROLES:
                        r = created_roles.get(staff_name)
                        if r:
                            cat_overwrites[r] = discord.PermissionOverwrite(view_channel=True)
                    if guild.me:
                        cat_overwrites[guild.me] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

                if existing_cat:
                    category = existing_cat
                    if cat_overwrites:
                        try:
                            await category.edit(overwrites=cat_overwrites)
                        except discord.Forbidden:
                            pass
                else:
                    cat_kwargs = {"name": category_name}
                    if cat_overwrites:
                        cat_kwargs["overwrites"] = cat_overwrites
                    category = await guild.create_category(**cat_kwargs)
                    status.append(f"Created category: {category_name}")
                await asyncio.sleep(0.5)

                for ch_data in category_data.get("channels", []):
                    ch_name = ch_data["name"]
                    overwrites = self._build_overwrites(guild, ch_data, created_roles)
                    if ch_data["type"] == "voice":
                        existing_vc = discord.utils.get(guild.voice_channels, name=ch_name, category=category)
                        if not existing_vc:
                            kwargs = {"name": ch_name, "category": category}
                            if overwrites:
                                kwargs["overwrites"] = overwrites
                            vc = await guild.create_voice_channel(**kwargs)
                            if ch_data.get("afk"):
                                try:
                                    await guild.edit(afk_channel=vc, afk_timeout=300)
                                except discord.Forbidden:
                                    pass
                            status.append(f"  + {ch_name} (voice)")
                    else:
                        if discord.utils.get(guild.text_channels, name=ch_name, category=category):
                            continue
                        kwargs = {"name": ch_name, "category": category, "topic": ch_data.get("topic", "")}
                        if overwrites:
                            kwargs["overwrites"] = overwrites
                        await guild.create_text_channel(**kwargs)
                        status.append(f"  + #{ch_name}")
                    await asyncio.sleep(0.5)

            await interaction.followup.send("Posting content...", ephemeral=True)

            verify_ch = discord.utils.get(guild.text_channels, name="verify")
            if verify_ch:
                embed = discord.Embed(
                    title="Server Verification",
                    description="Click the button below to verify your account and get access to the rest of the server.\n\nThis helps us keep bots and spam accounts out.",
                    color=NEXUS_GREEN,
                )
                _nexus_footer(embed)
                await verify_ch.send(embed=embed, view=VerifyButton())
                status.append("Posted verification button")

            rules_ch = discord.utils.get(guild.text_channels, name="rules")
            if rules_ch:
                embed = discord.Embed(title="Server Rules", description=RULES_TEXT, color=NEXUS_PURPLE)
                _nexus_footer(embed)
                await rules_ch.send(embed=embed)
                status.append("Posted rules")

            welcome_ch = discord.utils.get(guild.text_channels, name="welcome")
            if welcome_ch:
                embed = discord.Embed(description=WELCOME_MESSAGE, color=NEXUS_BLUE)
                if self.bot.user and self.bot.user.avatar:
                    embed.set_thumbnail(url=self.bot.user.display_avatar.url)
                _nexus_footer(embed)
                await welcome_ch.send(embed=embed)
                status.append("Posted welcome message")

            roles_ch = discord.utils.get(guild.text_channels, name="pick-your-roles")
            if roles_ch:
                embed = discord.Embed(
                    title="Notification Roles",
                    description="React below to get pinged for specific types of updates.\n\n"
                        "\U0001f514  **Notifications** -- general pings for important stuff\n"
                        "\U0001f4e2  **Announcement Pings** -- server announcements\n"
                        "\U0001f310  **Website Updates** -- Nexus platform updates\n"
                        "\U0001f4f0  **Updates** -- changelog and patch notes",
                    color=NEXUS_PURPLE,
                )
                _nexus_footer(embed)
                msg = await roles_ch.send(embed=embed)
                for emoji in ["\U0001f514", "\U0001f4e2", "\U0001f310", "\U0001f4f0"]:
                    await msg.add_reaction(emoji)
                status.append("Posted notification role picker")

                color_embed = discord.Embed(
                    title="Name Colors",
                    description="React to pick a name color. You can only have one at a time.\nThis changes your name color without affecting your position in the member list.\n\n"
                        "\u2764\ufe0f Red | \U0001f499 Blue | \U0001f49a Green | \U0001f49c Purple\n"
                        "\U0001f9e1 Orange | \U0001f49f Pink | \U0001f49b Yellow | \U0001f90d Teal",
                    color=NEXUS_BLUE,
                )
                _nexus_footer(color_embed)
                color_msg = await roles_ch.send(embed=color_embed)
                for emoji in ["\u2764\ufe0f", "\U0001f499", "\U0001f49a", "\U0001f49c", "\U0001f9e1", "\U0001f49f", "\U0001f49b", "\U0001f90d"]:
                    await color_msg.add_reaction(emoji)
                status.append("Posted color role picker")

            faq_ch = discord.utils.get(guild.text_channels, name="faq")
            if faq_ch:
                for section in FAQ_SECTIONS:
                    embed = discord.Embed(title=section["title"], color=section["color"])
                    for name, value in section["fields"]:
                        embed.add_field(name=name, value=value, inline=False)
                    _nexus_footer(embed)
                    await faq_ch.send(embed=embed)
                    await asyncio.sleep(0.5)
                status.append("Posted FAQ dashboard")

            summary = "**Server setup complete.**\n\n" + "\n".join(status) if status else "**Server setup complete.** Everything was already set up."
            if len(summary) > 4000:
                for i in range(0, len(summary), 4000):
                    await interaction.followup.send(summary[i:i + 4000], ephemeral=True)
            else:
                await interaction.followup.send(summary, ephemeral=True)

        except discord.Forbidden:
            await interaction.followup.send("Missing permissions. Make sure my role is above the roles I need to create and I have Administrator permission.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Setup failed: {e}", ephemeral=True)
        finally:
            resume_logging(guild.id)

    @app_commands.command(name="reset-server", description="Remove all bot-created channels and roles. Admin only.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def reset_server(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        suppress_logging(guild.id)
        await interaction.followup.send("Type `CONFIRM` in the next 30 seconds to reset the server.", ephemeral=True)

        def check(m):
            return m.author == interaction.user and m.content == "CONFIRM"

        try:
            await self.bot.wait_for("message", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await interaction.followup.send("Cancelled.", ephemeral=True)
            return

        deleted = {"roles": 0, "channels": 0, "categories": 0}
        for role_name in ROLE_CONFIG:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                try:
                    await role.delete()
                    deleted["roles"] += 1
                except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                    pass
                await asyncio.sleep(0.6)

        for category_name in CHANNEL_CONFIG:
            category = discord.utils.get(guild.categories, name=category_name)
            if category:
                for ch in category.channels:
                    try:
                        await ch.delete()
                        deleted["channels"] += 1
                    except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                        pass
                    await asyncio.sleep(0.6)
                try:
                    await category.delete()
                    deleted["categories"] += 1
                except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                    pass
                await asyncio.sleep(0.6)

        resume_logging(guild.id)
        try:
            await interaction.followup.send(
                f"Reset complete. Removed {deleted['roles']} roles, {deleted['channels']} channels, {deleted['categories']} categories.",
                ephemeral=True,
            )
        except (discord.NotFound, discord.HTTPException):
            pass

    @app_commands.command(name="post-verify", description="Post the verification button to the current channel. Admin only.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def post_verify(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Server Verification",
            description="Click the button below to verify your account and get access to the rest of the server.\n\nThis helps us keep bots and spam accounts out.",
            color=NEXUS_GREEN,
        )
        _nexus_footer(embed)
        await interaction.channel.send(embed=embed, view=VerifyButton())
        await interaction.response.send_message("Verification button posted.", ephemeral=True)

    @app_commands.command(name="post-faq", description="Post the FAQ dashboard to the current channel. Admin only.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def post_faq(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        for section in FAQ_SECTIONS:
            embed = discord.Embed(title=section["title"], color=section["color"])
            for name, value in section["fields"]:
                embed.add_field(name=name, value=value, inline=False)
            _nexus_footer(embed)
            await interaction.channel.send(embed=embed)
            await asyncio.sleep(0.5)
        await interaction.followup.send("FAQ dashboard posted.", ephemeral=True)

    @app_commands.command(name="post-roles", description="Post the role picker embeds to the current channel. Admin only.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def post_roles(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        embed = discord.Embed(
            title="Notification Roles",
            description="React below to get pinged for specific types of updates.\n\n"
                "\U0001f514  **Notifications** -- general pings for important stuff\n"
                "\U0001f4e2  **Announcement Pings** -- server announcements\n"
                "\U0001f310  **Website Updates** -- Nexus platform updates\n"
                "\U0001f4f0  **Updates** -- changelog and patch notes",
            color=NEXUS_PURPLE,
        )
        _nexus_footer(embed)
        msg = await interaction.channel.send(embed=embed)
        for emoji in ["\U0001f514", "\U0001f4e2", "\U0001f310", "\U0001f4f0"]:
            await msg.add_reaction(emoji)

        color_embed = discord.Embed(
            title="Name Colors",
            description="React to pick a name color. You can only have one at a time.\nThis changes your name color without affecting your position in the member list.\n\n"
                "\u2764\ufe0f Red | \U0001f499 Blue | \U0001f49a Green | \U0001f49c Purple\n"
                "\U0001f9e1 Orange | \U0001f49f Pink | \U0001f49b Yellow | \U0001f90d Teal",
            color=NEXUS_BLUE,
        )
        _nexus_footer(color_embed)
        color_msg = await interaction.channel.send(embed=color_embed)
        for emoji in ["\u2764\ufe0f", "\U0001f499", "\U0001f49a", "\U0001f49c", "\U0001f9e1", "\U0001f49f", "\U0001f49b", "\U0001f90d"]:
            await color_msg.add_reaction(emoji)

        await interaction.followup.send("Role pickers posted.", ephemeral=True)


class NotificationsCog(commands.Cog):
    def __init__(self, b):
        self.bot = b

    async def _resolve_member(self, guild, user_id):
        member = guild.get_member(user_id)
        if member:
            return member
        try:
            member = await guild.fetch_member(user_id)
            return member
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return None

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        emoji_str = str(payload.emoji)
        if emoji_str not in ROLE_EMOJI_MAP and emoji_str not in COLOR_ROLE_EMOJI_MAP:
            return

        member = await self._resolve_member(guild, payload.user_id)
        if not member:
            return

        try:
            channel = guild.get_channel(payload.channel_id)
            if channel:
                msg = await channel.fetch_message(payload.message_id)
                if not msg.author or msg.author.id != self.bot.user.id:
                    return
            else:
                return
        except (discord.NotFound, discord.Forbidden):
            return

        role_name = ROLE_EMOJI_MAP.get(emoji_str)
        if role_name:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                try:
                    await member.add_roles(role)
                except discord.Forbidden:
                    pass
            return

        color_name = COLOR_ROLE_EMOJI_MAP.get(emoji_str)
        if color_name:
            for existing_color in ALL_COLOR_ROLES:
                existing_role = discord.utils.get(guild.roles, name=existing_color)
                if existing_role and existing_role in member.roles:
                    try:
                        await member.remove_roles(existing_role)
                    except discord.Forbidden:
                        pass
            new_role = discord.utils.get(guild.roles, name=color_name)
            if new_role:
                try:
                    await member.add_roles(new_role)
                except discord.Forbidden:
                    pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.user_id == self.bot.user.id:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        emoji_str = str(payload.emoji)
        if emoji_str not in ROLE_EMOJI_MAP and emoji_str not in COLOR_ROLE_EMOJI_MAP:
            return

        member = await self._resolve_member(guild, payload.user_id)
        if not member:
            return

        role_name = ROLE_EMOJI_MAP.get(emoji_str) or COLOR_ROLE_EMOJI_MAP.get(emoji_str)
        if role_name:
            role = discord.utils.get(guild.roles, name=role_name)
            if role and role in member.roles:
                try:
                    await member.remove_roles(role)
                except discord.Forbidden:
                    pass

    @app_commands.command(name="announce", description="Post an announcement (Mod+)")
    @app_commands.describe(title="Title", message="Content", ping="Ping @everyone")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.checks.has_permissions(manage_messages=True)
    async def announce(self, interaction: discord.Interaction, title: str, message: str, ping: bool = False):
        announcements_ch = discord.utils.get(interaction.guild.text_channels, name="announcements")
        if not announcements_ch:
            await interaction.response.send_message("Could not find #announcements.", ephemeral=True)
            return
        embed = discord.Embed(title=title, description=message, color=NEXUS_PURPLE)
        embed.set_footer(text=f"Posted by {interaction.user.display_name}", icon_url=NEXUS_ICON)
        embed.timestamp = discord.utils.utcnow()
        content = "@everyone" if ping else None
        await announcements_ch.send(content=content, embed=embed)
        await interaction.response.send_message("Announcement posted.", ephemeral=True)


class ModerationCog(commands.Cog):
    def __init__(self, b):
        self.bot = b

    @app_commands.command(name="kick", description="Kick a member")
    @app_commands.describe(member="Member to kick", reason="Reason")
    @app_commands.default_permissions(kick_members=True)
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick_member(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message("You can't kick someone with a higher or equal role.", ephemeral=True)
            return
        await member.kick(reason=reason)
        embed = discord.Embed(title="Member Kicked", description=f"**{member.display_name}** was kicked by {interaction.user.mention}\nReason: {reason}", color=0xF59E0B)
        _nexus_footer(embed)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ban", description="Ban a member")
    @app_commands.describe(member="Member to ban", reason="Reason")
    @app_commands.default_permissions(ban_members=True)
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban_member(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message("You can't ban someone with a higher or equal role.", ephemeral=True)
            return
        await member.ban(reason=reason)
        embed = discord.Embed(title="Member Banned", description=f"**{member.display_name}** was banned by {interaction.user.mention}\nReason: {reason}", color=0xEF4444)
        _nexus_footer(embed)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="timeout", description="Timeout a member")
    @app_commands.describe(member="Member to timeout", minutes="Duration in minutes", reason="Reason")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout_member(self, interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "No reason provided"):
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message("You can't timeout someone with a higher or equal role.", ephemeral=True)
            return
        duration = discord.utils.utcnow() + datetime.timedelta(minutes=minutes)
        await member.timeout(duration, reason=reason)
        embed = discord.Embed(title="Member Timed Out", description=f"**{member.display_name}** timed out for {minutes}m by {interaction.user.mention}\nReason: {reason}", color=0xF59E0B)
        _nexus_footer(embed)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="clear", description="Delete messages from a channel")
    @app_commands.describe(amount="Number of messages (1-100)")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear_messages(self, interaction: discord.Interaction, amount: int):
        if amount < 1 or amount > 100:
            await interaction.response.send_message("Must be between 1 and 100.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"Deleted {len(deleted)} message(s).", ephemeral=True)

    @app_commands.command(name="slowmode", description="Set channel slowmode")
    @app_commands.describe(seconds="Slowmode delay in seconds (0 to disable)")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(manage_channels=True)
    async def slowmode(self, interaction: discord.Interaction, seconds: int):
        if seconds < 0 or seconds > 21600:
            await interaction.response.send_message("Must be between 0 and 21600 seconds.", ephemeral=True)
            return
        await interaction.channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            await interaction.response.send_message("Slowmode disabled.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Slowmode set to {seconds} seconds.", ephemeral=True)

    @app_commands.command(name="unban", description="Unban a user by ID")
    @app_commands.describe(user_id="The user ID to unban", reason="Reason for unbanning")
    @app_commands.default_permissions(ban_members=True)
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban_member(self, interaction: discord.Interaction, user_id: str, reason: str = "No reason provided"):
        try:
            user = await self.bot.fetch_user(int(user_id))
        except (ValueError, discord.NotFound):
            await interaction.response.send_message("Invalid user ID or user not found.", ephemeral=True)
            return
        try:
            await interaction.guild.unban(user, reason=reason)
            embed = discord.Embed(title="Member Unbanned", description=f"**{user}** was unbanned by {interaction.user.mention}\nReason: {reason}", color=0x10B981)
            _nexus_footer(embed)
            await interaction.response.send_message(embed=embed)
        except discord.NotFound:
            await interaction.response.send_message("That user is not banned.", ephemeral=True)

    @app_commands.command(name="untimeout", description="Remove timeout from a member")
    @app_commands.describe(member="Member to untimeout")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    async def untimeout_member(self, interaction: discord.Interaction, member: discord.Member):
        await member.timeout(None)
        embed = discord.Embed(title="Timeout Removed", description=f"**{member.display_name}** timeout removed by {interaction.user.mention}", color=0x10B981)
        _nexus_footer(embed)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="warn", description="Warn a member")
    @app_commands.describe(member="Member to warn", reason="Reason for the warning")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.checks.has_permissions(manage_messages=True)
    async def warn_member(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        embed = discord.Embed(
            title="Warning Issued",
            description=f"**{member.display_name}** was warned by {interaction.user.mention}\nReason: {reason}",
            color=0xF59E0B,
        )
        _nexus_footer(embed)
        await interaction.response.send_message(embed=embed)

        try:
            dm_embed = discord.Embed(
                title=f"You were warned in {interaction.guild.name}",
                description=f"Reason: {reason}\n\nPlease review the server rules to avoid further action.",
                color=0xF59E0B,
            )
            _nexus_footer(dm_embed)
            await member.send(embed=dm_embed)
        except (discord.Forbidden, discord.HTTPException):
            pass

    @app_commands.command(name="role", description="Add or remove a role from a member")
    @app_commands.describe(member="Target member", role="Role to add or remove", action="Add or remove")
    @app_commands.choices(action=[
        app_commands.Choice(name="Add", value="add"),
        app_commands.Choice(name="Remove", value="remove"),
    ])
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.checks.has_permissions(manage_roles=True)
    async def role_cmd(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role, action: app_commands.Choice[str]):
        if role >= interaction.user.top_role:
            await interaction.response.send_message("You can't manage a role higher than or equal to your own.", ephemeral=True)
            return
        if role >= interaction.guild.me.top_role:
            await interaction.response.send_message("That role is higher than my highest role.", ephemeral=True)
            return
        if action.value == "add":
            await member.add_roles(role)
            embed = discord.Embed(title="Role Added", description=f"{role.mention} added to **{member.display_name}** by {interaction.user.mention}", color=0x10B981)
        else:
            await member.remove_roles(role)
            embed = discord.Embed(title="Role Removed", description=f"{role.mention} removed from **{member.display_name}** by {interaction.user.mention}", color=0xF59E0B)
        _nexus_footer(embed)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="nick", description="Change a member's nickname")
    @app_commands.describe(member="Target member", nickname="New nickname (leave blank to reset)")
    @app_commands.default_permissions(manage_nicknames=True)
    @app_commands.checks.has_permissions(manage_nicknames=True)
    async def nick_cmd(self, interaction: discord.Interaction, member: discord.Member, nickname: str = None):
        old_nick = member.display_name
        await member.edit(nick=nickname)
        new_nick = nickname or member.name
        embed = discord.Embed(title="Nickname Changed", description=f"**{old_nick}** -> **{new_nick}**\nChanged by {interaction.user.mention}", color=NEXUS_BLUE)
        _nexus_footer(embed)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="lock", description="Lock a channel (prevent messages)")
    @app_commands.describe(channel="Channel to lock", reason="Reason for locking")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(manage_channels=True)
    async def lock_channel(self, interaction: discord.Interaction, channel: discord.TextChannel = None, reason: str = "No reason provided"):
        channel = channel or interaction.channel
        overwrites = channel.overwrites_for(interaction.guild.default_role)
        overwrites.send_messages = False
        await channel.set_permissions(interaction.guild.default_role, overwrite=overwrites, reason=reason)
        embed = discord.Embed(title="Channel Locked", description=f"{channel.mention} has been locked by {interaction.user.mention}\nReason: {reason}", color=0xEF4444)
        _nexus_footer(embed)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="unlock", description="Unlock a channel (allow messages)")
    @app_commands.describe(channel="Channel to unlock", reason="Reason for unlocking")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(manage_channels=True)
    async def unlock_channel(self, interaction: discord.Interaction, channel: discord.TextChannel = None, reason: str = "No reason provided"):
        channel = channel or interaction.channel
        overwrites = channel.overwrites_for(interaction.guild.default_role)
        overwrites.send_messages = None
        await channel.set_permissions(interaction.guild.default_role, overwrite=overwrites, reason=reason)
        embed = discord.Embed(title="Channel Unlocked", description=f"{channel.mention} has been unlocked by {interaction.user.mention}\nReason: {reason}", color=0x10B981)
        _nexus_footer(embed)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="poll", description="Create a simple poll")
    @app_commands.describe(question="The poll question", option1="First option", option2="Second option", option3="Third option (optional)", option4="Fourth option (optional)")
    async def poll_cmd(self, interaction: discord.Interaction, question: str, option1: str, option2: str, option3: str = None, option4: str = None):
        number_emojis = ["\u0031\ufe0f\u20e3", "\u0032\ufe0f\u20e3", "\u0033\ufe0f\u20e3", "\u0034\ufe0f\u20e3"]
        options = [option1, option2]
        if option3:
            options.append(option3)
        if option4:
            options.append(option4)
        desc = "\n\n".join([f"{number_emojis[i]}  {opt}" for i, opt in enumerate(options)])
        embed = discord.Embed(title=f"Poll: {question}", description=desc, color=NEXUS_PURPLE)
        embed.set_footer(text=f"Asked by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        for i in range(len(options)):
            await msg.add_reaction(number_emojis[i])

    @app_commands.command(name="embed", description="Create a custom embed message")
    @app_commands.describe(title="Embed title", description="Embed content", color="Hex color (e.g. #6366f1)")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.checks.has_permissions(manage_messages=True)
    async def embed_cmd(self, interaction: discord.Interaction, title: str, description: str, color: str = "#6366f1"):
        try:
            hex_color = int(color.lstrip("#"), 16)
        except ValueError:
            hex_color = NEXUS_PURPLE
        embed = discord.Embed(title=title, description=description, color=hex_color)
        _nexus_footer(embed)
        await interaction.channel.send(embed=embed)
        await interaction.response.send_message("Embed posted.", ephemeral=True)

    @app_commands.command(name="avatar", description="Show a user's avatar")
    @app_commands.describe(member="The user to show the avatar for")
    async def avatar_cmd(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        embed = discord.Embed(title=f"{member.display_name}'s Avatar", color=member.color if member.color.value else NEXUS_BLUE)
        embed.set_image(url=member.display_avatar.url)
        if member.avatar and member.guild_avatar:
            embed.set_thumbnail(url=member.avatar.url)
            embed.set_footer(text="Showing server avatar. Thumbnail is global avatar.")
        else:
            _nexus_footer(embed)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="moveall", description="Move all members from one voice channel to another")
    @app_commands.describe(source="Source voice channel", destination="Destination voice channel")
    @app_commands.default_permissions(move_members=True)
    @app_commands.checks.has_permissions(move_members=True)
    async def moveall_cmd(self, interaction: discord.Interaction, source: discord.VoiceChannel, destination: discord.VoiceChannel):
        if not source.members:
            await interaction.response.send_message("No members in the source channel.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        moved = 0
        for member in source.members:
            try:
                await member.move_to(destination)
                moved += 1
            except discord.Forbidden:
                pass
        await interaction.followup.send(f"Moved {moved} member(s) from {source.name} to {destination.name}.", ephemeral=True)

    @app_commands.command(name="banlist", description="Show banned users")
    @app_commands.default_permissions(ban_members=True)
    @app_commands.checks.has_permissions(ban_members=True)
    async def banlist_cmd(self, interaction: discord.Interaction):
        bans = [entry async for entry in interaction.guild.bans(limit=25)]
        if not bans:
            await interaction.response.send_message("No banned users.", ephemeral=True)
            return
        desc = "\n".join([f"**{entry.user}** (ID: {entry.user.id}){' - ' + entry.reason if entry.reason else ''}" for entry in bans[:25]])
        embed = discord.Embed(title=f"Ban List ({len(bans)} shown)", description=desc, color=0xEF4444)
        _nexus_footer(embed)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="userinfo", description="Get info about a member")
    @app_commands.describe(member="The member to look up")
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        embed = discord.Embed(title=member.display_name, color=member.color if member.color.value else NEXUS_BLUE)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Username", value=str(member), inline=True)
        embed.add_field(name="ID", value=str(member.id), inline=True)
        embed.add_field(name="Joined Server", value=member.joined_at.strftime("%b %d, %Y") if member.joined_at else "Unknown", inline=True)
        embed.add_field(name="Account Created", value=member.created_at.strftime("%b %d, %Y"), inline=True)
        embed.add_field(name="Top Role", value=member.top_role.mention if member.top_role != interaction.guild.default_role else "None", inline=True)
        embed.add_field(name="Bot", value="Yes" if member.bot else "No", inline=True)
        roles = [r.mention for r in member.roles if r != interaction.guild.default_role][:15]
        if roles:
            embed.add_field(name=f"Roles ({len(roles)})", value=" ".join(roles), inline=False)
        _nexus_footer(embed)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="serverinfo", description="Get info about this server")
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        embed = discord.Embed(title=guild.name, color=NEXUS_PURPLE)
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)
        embed.add_field(name="Members", value=f"{guild.member_count:,}", inline=True)
        embed.add_field(name="Roles", value=str(len(guild.roles)), inline=True)
        embed.add_field(name="Text Channels", value=str(len(guild.text_channels)), inline=True)
        embed.add_field(name="Voice Channels", value=str(len(guild.voice_channels)), inline=True)
        embed.add_field(name="Boosts", value=f"{guild.premium_subscription_count} (Tier {guild.premium_tier})", inline=True)
        embed.add_field(name="Created", value=guild.created_at.strftime("%b %d, %Y"), inline=True)
        if guild.banner:
            embed.set_image(url=guild.banner.url)
        _nexus_footer(embed)
        await interaction.response.send_message(embed=embed)


class InfoCog(commands.Cog):
    def __init__(self, b):
        self.bot = b

    @app_commands.command(name="help", description="Show all bot commands")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(title="Nexus Bot Commands", color=NEXUS_PURPLE)
        embed.add_field(
            name="General",
            value="`/help` - Show commands\n`/info` - About Nexus\n`/stats` - Server stats\n`/userinfo` - Look up a member\n`/serverinfo` - Server details\n`/avatar` - Show user avatar\n`/poll` - Create a poll",
            inline=False,
        )
        embed.add_field(
            name="Notifications",
            value="`/announce` - Post an announcement (Mod+)\n`/embed` - Create custom embed (Mod+)",
            inline=False,
        )
        embed.add_field(
            name="Moderation",
            value="`/kick` - Kick a member\n`/ban` - Ban a member\n`/unban` - Unban by user ID\n`/banlist` - View banned users\n`/timeout` - Timeout a member\n`/untimeout` - Remove timeout\n`/warn` - Warn a member\n`/clear` - Delete messages\n`/slowmode` - Set slowmode\n`/lock` - Lock a channel\n`/unlock` - Unlock a channel",
            inline=False,
        )
        embed.add_field(
            name="Role & Member Management",
            value="`/role` - Add/remove role from member\n`/nick` - Change nickname\n`/moveall` - Move voice members",
            inline=False,
        )
        embed.add_field(
            name="Admin",
            value="`/setup-server` - Build the full server\n`/reset-server` - Remove all bot content\n`/post-verify` - Post verify button\n`/post-faq` - Post FAQ dashboard\n`/post-roles` - Post role pickers",
            inline=False,
        )
        _nexus_footer(embed)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="info", description="About Nexus")
    async def info_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Nexus",
            description="YouTube bot and analytics platform, currently in beta.\n\n"
                "**What it does:**\n"
                "- Moderates your YouTube live chat automatically\n"
                "- Custom commands and timed messages\n"
                "- Channel analytics and growth tracking\n"
                "- Video performance monitoring\n"
                "- Discord integration for live notifications\n\n"
                "**Coming soon:** Twitch, Kick, and Twitter/X support",
            color=NEXUS_PURPLE,
        )
        _nexus_footer(embed)
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Open Nexus", url="https://nexusbeta.vercel.app", style=discord.ButtonStyle.link))
        view.add_item(discord.ui.Button(label="Help Center", url="https://nexusbeta.vercel.app/help", style=discord.ButtonStyle.link))
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="stats", description="Server statistics")
    async def stats_command(self, interaction: discord.Interaction):
        guild = interaction.guild
        embed = discord.Embed(title=guild.name, color=NEXUS_BLUE)
        embed.add_field(name="Members", value=f"{guild.member_count:,}", inline=True)
        embed.add_field(name="Channels", value=str(len(guild.channels)), inline=True)
        embed.add_field(name="Roles", value=str(len(guild.roles)), inline=True)
        embed.add_field(name="Boosts", value=str(guild.premium_subscription_count), inline=True)
        embed.add_field(name="Boost Level", value=str(guild.premium_tier), inline=True)
        embed.add_field(name="Created", value=guild.created_at.strftime("%b %d, %Y"), inline=True)
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        _nexus_footer(embed)
        await interaction.response.send_message(embed=embed)


_setup_guilds = set()


def suppress_logging(guild_id):
    _setup_guilds.add(guild_id)


def resume_logging(guild_id):
    _setup_guilds.discard(guild_id)


class LoggingCog(commands.Cog):
    def __init__(self, b):
        self.bot = b

    def _suppressed(self, guild):
        return guild and guild.id in _setup_guilds

    async def _get_mod_log_channel(self, guild):
        return discord.utils.get(guild.text_channels, name="mod-log")

    async def _send_log(self, guild, embed):
        channel = await self._get_mod_log_channel(guild)
        if channel:
            try:
                await channel.send(embed=embed)
            except (discord.Forbidden, discord.HTTPException, discord.NotFound):
                pass

    async def _log_action(self, guild, action_type, embed, moderator=None, target=None, reason=None, details=None):
        await self._send_log(guild, embed)
        await nexus_api.send_log({
            "server_id": str(guild.id),
            "action_type": action_type,
            "moderator_id": str(moderator.id) if moderator else None,
            "moderator_name": str(moderator) if moderator else None,
            "target_id": str(target.id) if target else None,
            "target_name": str(target) if target else None,
            "reason": reason,
            "details": details,
        })

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if self._suppressed(member.guild):
            return
        embed = discord.Embed(color=0x10B981)
        embed.set_author(name="Member Joined", icon_url=member.display_avatar.url)
        embed.description = f"{member.mention} ({member})"
        embed.add_field(name="Account Created", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="Member Count", value=f"{member.guild.member_count:,}", inline=True)
        embed.add_field(name="Bot Account", value="Yes" if member.bot else "No", inline=True)
        embed.set_footer(text=f"ID: {member.id}", icon_url=NEXUS_ICON)
        embed.timestamp = discord.utils.utcnow()
        await self._log_action(member.guild, "join", embed, target=member)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if self._suppressed(member.guild):
            return
        embed = discord.Embed(color=0x94A3B8)
        embed.set_author(name="Member Left", icon_url=member.display_avatar.url)
        embed.description = f"**{member}** left the server"
        roles = [r.mention for r in member.roles if r != member.guild.default_role]
        if roles:
            embed.add_field(name="Roles", value=" ".join(roles[:10]), inline=False)
        if member.joined_at:
            embed.add_field(name="Joined", value=f"<t:{int(member.joined_at.timestamp())}:R>", inline=True)
        embed.add_field(name="Member Count", value=f"{member.guild.member_count:,}", inline=True)
        embed.set_footer(text=f"ID: {member.id}", icon_url=NEXUS_ICON)
        embed.timestamp = discord.utils.utcnow()
        await self._log_action(member.guild, "leave", embed, target=member)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        if self._suppressed(guild):
            return
        embed = discord.Embed(description=f"**{user}** was banned", color=0xEF4444)
        embed.set_author(name="Member Banned", icon_url=user.display_avatar.url)
        reason = None
        moderator = None
        try:
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.ban):
                if entry.target.id == user.id:
                    reason = entry.reason
                    moderator = entry.user
                    break
        except discord.Forbidden:
            pass
        if moderator:
            embed.add_field(name="Banned By", value=moderator.mention, inline=True)
        if reason:
            embed.add_field(name="Reason", value=reason, inline=True)
        embed.set_footer(text=f"ID: {user.id}", icon_url=NEXUS_ICON)
        embed.timestamp = discord.utils.utcnow()
        await self._log_action(guild, "ban", embed, moderator=moderator, target=user, reason=reason)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        if self._suppressed(guild):
            return
        embed = discord.Embed(description=f"**{user}** was unbanned", color=0x10B981)
        embed.set_author(name="Member Unbanned")
        embed.set_footer(text=f"ID: {user.id}", icon_url=NEXUS_ICON)
        embed.timestamp = discord.utils.utcnow()
        await self._log_action(guild, "unban", embed, target=user)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if self._suppressed(after.guild):
            return
        if before.roles != after.roles:
            added = [r for r in after.roles if r not in before.roles]
            removed = [r for r in before.roles if r not in after.roles]
            if not added and not removed:
                return
            embed = discord.Embed(color=NEXUS_PURPLE)
            embed.set_author(name="Roles Updated", icon_url=after.display_avatar.url)
            embed.description = f"{after.mention} ({after})"
            if added:
                embed.add_field(name="Added", value=" ".join([r.mention for r in added]), inline=True)
            if removed:
                embed.add_field(name="Removed", value=" ".join([r.mention for r in removed]), inline=True)
            embed.set_footer(text=f"ID: {after.id}", icon_url=NEXUS_ICON)
            embed.timestamp = discord.utils.utcnow()
            await self._send_log(after.guild, embed)
            details = ""
            if added:
                details += f"Added: {', '.join([r.name for r in added])}. "
            if removed:
                details += f"Removed: {', '.join([r.name for r in removed])}."
            await nexus_api.send_log({
                "server_id": str(after.guild.id),
                "action_type": "role",
                "target_id": str(after.id),
                "target_name": str(after),
                "details": details.strip(),
            })

        if before.nick != after.nick:
            embed = discord.Embed(color=0xF59E0B)
            embed.set_author(name="Nickname Changed", icon_url=after.display_avatar.url)
            embed.description = f"{after.mention}"
            embed.add_field(name="Before", value=before.nick or before.name, inline=True)
            embed.add_field(name="After", value=after.nick or after.name, inline=True)
            embed.set_footer(text=f"ID: {after.id}", icon_url=NEXUS_ICON)
            embed.timestamp = discord.utils.utcnow()
            await self._send_log(after.guild, embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot or not message.guild:
            return
        if self._suppressed(message.guild):
            return
        if message.channel.name in ("mod-log", "verify"):
            return
        embed = discord.Embed(color=0xF59E0B)
        embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)
        embed.description = f"Message deleted in {message.channel.mention}"
        content = message.content[:1024] if message.content else "[No text content]"
        embed.add_field(name="Content", value=content, inline=False)
        if message.attachments:
            embed.add_field(name="Attachments", value="\n".join([a.filename for a in message.attachments[:5]]), inline=False)
        embed.set_footer(text=f"Author: {message.author.id} | Message: {message.id}", icon_url=NEXUS_ICON)
        embed.timestamp = discord.utils.utcnow()
        await self._log_action(message.guild, "delete", embed, target=message.author, details=f"#{message.channel.name}")

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or not before.guild:
            return
        if self._suppressed(before.guild):
            return
        if before.content == after.content:
            return
        embed = discord.Embed(color=0x3B82F6)
        embed.set_author(name=str(before.author), icon_url=before.author.display_avatar.url)
        embed.description = f"Message edited in {before.channel.mention} [Jump]({after.jump_url})"
        old = before.content[:512] if before.content else "[empty]"
        new = after.content[:512] if after.content else "[empty]"
        embed.add_field(name="Before", value=old, inline=False)
        embed.add_field(name="After", value=new, inline=False)
        embed.set_footer(text=f"Author: {before.author.id}", icon_url=NEXUS_ICON)
        embed.timestamp = discord.utils.utcnow()
        await self._send_log(before.guild, embed)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        if not messages:
            return
        guild = messages[0].guild
        if not guild or self._suppressed(guild):
            return
        channel = messages[0].channel
        embed = discord.Embed(description=f"**{len(messages)} messages** bulk deleted in {channel.mention}", color=0xEF4444)
        embed.set_author(name="Bulk Delete")
        embed.set_footer(text=f"Channel: {channel.id}", icon_url=NEXUS_ICON)
        embed.timestamp = discord.utils.utcnow()
        await self._log_action(guild, "delete", embed, details=f"{len(messages)} messages in #{channel.name}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot or self._suppressed(member.guild):
            return
        if before.channel is None and after.channel is not None:
            embed = discord.Embed(description=f"{member.mention} joined **{after.channel.name}**", color=0x10B981)
            embed.set_footer(text=f"ID: {member.id}", icon_url=NEXUS_ICON)
            embed.timestamp = discord.utils.utcnow()
            await self._send_log(member.guild, embed)
        elif before.channel is not None and after.channel is None:
            embed = discord.Embed(description=f"{member.mention} left **{before.channel.name}**", color=0x94A3B8)
            embed.set_footer(text=f"ID: {member.id}", icon_url=NEXUS_ICON)
            embed.timestamp = discord.utils.utcnow()
            await self._send_log(member.guild, embed)
        elif before.channel != after.channel:
            embed = discord.Embed(description=f"{member.mention} moved **{before.channel.name}** -> **{after.channel.name}**", color=0x3B82F6)
            embed.set_footer(text=f"ID: {member.id}", icon_url=NEXUS_ICON)
            embed.timestamp = discord.utils.utcnow()
            await self._send_log(member.guild, embed)

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        if self._suppressed(invite.guild):
            return
        embed = discord.Embed(color=NEXUS_BLUE)
        embed.set_author(name="Invite Created")
        embed.description = f"**{invite.inviter}** created an invite"
        embed.add_field(name="Code", value=invite.code, inline=True)
        embed.add_field(name="Channel", value=invite.channel.mention if invite.channel else "Unknown", inline=True)
        embed.add_field(name="Max Uses", value=str(invite.max_uses) if invite.max_uses else "Unlimited", inline=True)
        embed.set_footer(text=f"Inviter: {invite.inviter.id}" if invite.inviter else "Nexus", icon_url=NEXUS_ICON)
        embed.timestamp = discord.utils.utcnow()
        await self._send_log(invite.guild, embed)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        if self._suppressed(channel.guild):
            return
        embed = discord.Embed(description=f"Channel created: **{channel.name}**", color=0x10B981)
        embed.set_author(name="Channel Created")
        if hasattr(channel, 'category') and channel.category:
            embed.add_field(name="Category", value=channel.category.name, inline=True)
        embed.add_field(name="Type", value=str(channel.type).replace("_", " ").title(), inline=True)
        embed.set_footer(text=f"ID: {channel.id}", icon_url=NEXUS_ICON)
        embed.timestamp = discord.utils.utcnow()
        await self._send_log(channel.guild, embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        if self._suppressed(channel.guild):
            return
        embed = discord.Embed(description=f"Channel deleted: **{channel.name}**", color=0xEF4444)
        embed.set_author(name="Channel Deleted")
        embed.add_field(name="Type", value=str(channel.type).replace("_", " ").title(), inline=True)
        embed.set_footer(text=f"ID: {channel.id}", icon_url=NEXUS_ICON)
        embed.timestamp = discord.utils.utcnow()
        await self._send_log(channel.guild, embed)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        if self._suppressed(role.guild):
            return
        embed = discord.Embed(description=f"Role created: **{role.name}**", color=0x10B981)
        embed.set_author(name="Role Created")
        embed.add_field(name="Color", value=str(role.color), inline=True)
        embed.add_field(name="Hoisted", value="Yes" if role.hoist else "No", inline=True)
        embed.set_footer(text=f"ID: {role.id}", icon_url=NEXUS_ICON)
        embed.timestamp = discord.utils.utcnow()
        await self._send_log(role.guild, embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        if self._suppressed(role.guild):
            return
        embed = discord.Embed(description=f"Role deleted: **{role.name}**", color=0xEF4444)
        embed.set_author(name="Role Deleted")
        embed.set_footer(text=f"ID: {role.id}", icon_url=NEXUS_ICON)
        embed.timestamp = discord.utils.utcnow()
        await self._send_log(role.guild, embed)


async def main():
    log.info("=" * 60)
    log.info("  NEXUS DISCORD BOT - STARTING UP")
    log.info("=" * 60)

    log.info("  Checking environment variables...")
    if not BOT_TOKEN:
        log.error("  DISCORD_BOT_TOKEN is not set!")
        log.error("  Create a .env file with your bot token.")
        log.error("  Example: DISCORD_BOT_TOKEN=your_token_here")
        return

    log.info(f"  DISCORD_BOT_TOKEN : {'Set' if BOT_TOKEN else 'NOT SET'}")
    log.info(f"  NEXUS_API_URL     : {NEXUS_API_URL}")
    log.info(f"  NEXUS_API_KEY     : {'Set' if NEXUS_API_KEY else 'NOT SET'}")
    log.info(f"  GUILD_ID          : {GUILD_ID if GUILD_ID else 'Not set'}")
    log.info("-" * 60)

    async with bot:
        cogs_to_load = [
            ("ServerSetup", ServerSetup),
            ("Notifications", NotificationsCog),
            ("Moderation", ModerationCog),
            ("Info", InfoCog),
            ("Logging", LoggingCog),
        ]
        for cog_name, cog_class in cogs_to_load:
            try:
                await bot.add_cog(cog_class(bot))
                log.info(f"  Loaded cog: {cog_name}")
            except Exception as e:
                log.error(f"  Failed to load cog {cog_name}: {e}")

        log.info("-" * 60)
        log.info("  Connecting to Discord...")
        await bot.start(BOT_TOKEN)


if __name__ == "__main__":
    print()
    print("  Nexus Bot Standalone - fps.ms / External Host Edition")
    print("  https://nexusbeta.vercel.app")
    print()
    asyncio.run(main())
