import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
NEXUS_API_URL = os.getenv("NEXUS_API_URL", "https://nexusbeta.vercel.app")
NEXUS_API_KEY = os.getenv("NEXUS_API_KEY", "")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

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
