# Nexus Discord yyYhot - Full Setup Guide

This guide covers buildig a Discord bt that can automatically create and configure a full Nexhhs community server, and eventually integrate with the Nexus website so users can manage notifications through Discord.

---

## Part 1: Creatingthe Discord Bot Application
### Step 1: Create the Bot n Discord Developer PortalY
1. Go to [https://discord.com/developers/applications](https://discord.com/developers/applications)
2. Click **New Application** in the top right
3. Name it **Nexus Bot** (or whatever you want it called in servers)
4. Go to the **Bot** tab on the left sidebar
5. Click **Add Bot**, then confirm
6. Under the bot section:
   - Set the bot's **username** (e.g. `Nexus Bot`)
   - Upload a **profile picture** (use the Nexus logo or a variation of it)
   - Turn **OFF** the "Public Bot" toggle if you only want to add it to your own servers
   - Turn **ON** these Privileged Gateway Intents:
     - `PRESENCE INTENT`
     - `SERVER MEMBERS INTENT`
     - `MESSAGE CONTENT INTENT`
7. Click **Reset Token** and copy the bot token somewhere safe. You will need this later. Never share it or commit it to git.

### Step 2: Set Up OAuth2 Permissions

1. Go to the **OAuth2** tab, then **URL Generator**
2. Under **Scopes**, check:
   - `bot`
   - `applications.commands`
3. Under **Bot Permissions**, check:
   - `Administrator` (needed for server setup - the bot creates channels, roles, categories, etc.)
   - Or if you want to be more granular:
     - Manage Server
     - Manage Roles
     - Manage Channels
     - Create Instant Invite
     - Send Messages
     - Embed Links
     - Attach Files
     - Manage Messages
     - Read Message History
     - Add Reactions
     - Use Slash Commands
     - Manage Webhooks
4. Copy the generated URL at the bottom. This is your bot invite link.

### Step 3: Invite the Bot

1. Open the OAuth2 URL in your browser
2. Select the server you want to add it to (or create a new empty server first)
3. Authorize it

---

## Part 2: Project Setup

### Directory Structure

```
nexus-discord-bot/
  bot.py                  # Main bot entry point
  config.py               # Configuration and constants
  cogs/
    server_setup.py       # Server creation/setup commands
    notifications.py      # Notification management commands
    moderation.py         # Basic moderation commands
    info.py               # Info and help commands
  utils/
    server_builder.py     # Functions to create channels, roles, categories
    embed_builder.py      # Reusable Discord embed templates
    api_client.py         # HTTP client for talking to the Nexus website API
  requirements.txt
  .env
```

### Requirements

Create `requirements.txt`:

```
discord.py>=2.3.0
python-dotenv>=1.0.0
aiohttp>=3.9.0
```

### Environment Variables

Create `.env`:

```env
DISCORD_BOT_TOKEN=your_bot_token_here
NEXUS_API_URL=https://nexusbeta.vercel.app
NEXUS_API_KEY=your_api_key_here
GUILD_ID=your_server_id_here
```

---

## Part 3: The Bot Code

### config.py - Configuration and Constants

```python
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
NEXUS_API_URL = os.getenv("NEXUS_API_URL", "https://nexusbeta.vercel.app")
NEXUS_API_KEY = os.getenv("NEXUS_API_KEY", "")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

NEXUS_PURPLE = 0x6366F1
NEXUS_BLUE = 0x818CF8

ROLE_CONFIG = {
    "Admin": {
        "color": 0xEF4444,
        "permissions": {
            "administrator": True
        },
        "hoist": True,
        "position_priority": 10
    },
    "Moderator": {
        "color": 0xF59E0B,
        "permissions": {
            "manage_messages": True,
            "kick_members": True,
            "ban_members": True,
            "mute_members": True,
            "deafen_members": True,
            "move_members": True,
            "manage_nicknames": True
        },
        "hoist": True,
        "position_priority": 9
    },
    "Support Team": {
        "color": 0x10B981,
        "permissions": {
            "manage_messages": True,
            "manage_nicknames": True
        },
        "hoist": True,
        "position_priority": 8
    },
    "Beta Tester": {
        "color": 0x8B5CF6,
        "permissions": {},
        "hoist": True,
        "position_priority": 7
    },
    "Subscriber": {
        "color": 0x6366F1,
        "permissions": {},
        "hoist": False,
        "position_priority": 6
    },
    "Streamer": {
        "color": 0xEC4899,
        "permissions": {
            "attach_files": True,
            "embed_links": True
        },
        "hoist": True,
        "position_priority": 5
    },
    "Nexus User": {
        "color": 0x64748B,
        "permissions": {},
        "hoist": False,
        "position_priority": 4
    },
    "Notifications": {
        "color": 0x3B82F6,
        "permissions": {},
        "hoist": False,
        "mentionable": True,
        "position_priority": 3
    },
    "Updates": {
        "color": 0x14B8A6,
        "permissions": {},
        "hoist": False,
        "mentionable": True,
        "position_priority": 2
    },
    "Member": {
        "color": 0x94A3B8,
        "permissions": {},
        "hoist": False,
        "position_priority": 1
    }
}

CHANNEL_CONFIG = {
    "WELCOME & INFO": {
        "type": "category",
        "channels": [
            {
                "name": "welcome",
                "type": "text",
                "topic": "Welcome to the Nexus community. Read the rules and grab your roles.",
                "read_only": True
            },
            {
                "name": "rules",
                "type": "text",
                "topic": "Server rules. Read before posting.",
                "read_only": True
            },
            {
                "name": "announcements",
                "type": "text",
                "topic": "Official Nexus announcements and updates.",
                "read_only": True
            },
            {
                "name": "pick-your-roles",
                "type": "text",
                "topic": "React to get notification roles and other roles.",
                "read_only": True
            },
            {
                "name": "faq",
                "type": "text",
                "topic": "Frequently asked questions about Nexus.",
                "read_only": True
            }
        ]
    },
    "GENERAL": {
        "type": "category",
        "channels": [
            {
                "name": "general",
                "type": "text",
                "topic": "General discussion about anything."
            },
            {
                "name": "introductions",
                "type": "text",
                "topic": "New here? Introduce yourself."
            },
            {
                "name": "off-topic",
                "type": "text",
                "topic": "Random stuff that doesn't fit anywhere else."
            },
            {
                "name": "memes",
                "type": "text",
                "topic": "Memes and funny content."
            }
        ]
    },
    "NEXUS PLATFORM": {
        "type": "category",
        "channels": [
            {
                "name": "nexus-help",
                "type": "text",
                "topic": "Need help with Nexus? Ask here."
            },
            {
                "name": "feature-requests",
                "type": "text",
                "topic": "Suggest features you want to see in Nexus."
            },
            {
                "name": "bug-reports",
                "type": "text",
                "topic": "Found a bug? Report it here with steps to reproduce."
            },
            {
                "name": "bot-setup-help",
                "type": "text",
                "topic": "Help with setting up the Nexus YouTube bot (nexusbetabot)."
            },
            {
                "name": "showcase",
                "type": "text",
                "topic": "Show off your channel, stream setups, or how you use Nexus."
            }
        ]
    },
    "STREAMING": {
        "type": "category",
        "channels": [
            {
                "name": "stream-chat",
                "type": "text",
                "topic": "Talk about streaming, tips, gear, software."
            },
            {
                "name": "self-promo",
                "type": "text",
                "topic": "Share your YouTube channel, videos, or streams. One post per day."
            },
            {
                "name": "collabs",
                "type": "text",
                "topic": "Looking for someone to collab with? Post here."
            },
            {
                "name": "milestones",
                "type": "text",
                "topic": "Hit a subscriber milestone? Share it here."
            }
        ]
    },
    "NOTIFICATIONS": {
        "type": "category",
        "channels": [
            {
                "name": "live-alerts",
                "type": "text",
                "topic": "Automatic notifications when Nexus users go live on YouTube.",
                "read_only": True
            },
            {
                "name": "milestone-alerts",
                "type": "text",
                "topic": "Automatic notifications when users hit subscriber milestones.",
                "read_only": True
            },
            {
                "name": "changelog",
                "type": "text",
                "topic": "Nexus platform update logs and patch notes.",
                "read_only": True
            }
        ]
    },
    "DEVELOPMENT": {
        "type": "category",
        "channels": [
            {
                "name": "dev-updates",
                "type": "text",
                "topic": "Development progress and what I'm working on.",
                "staff_only": True
            },
            {
                "name": "beta-testing",
                "type": "text",
                "topic": "Beta test coordination and feedback.",
                "role_restricted": "Beta Tester"
            },
            {
                "name": "api-discussion",
                "type": "text",
                "topic": "Technical discussion about the Nexus API and integrations."
            }
        ]
    },
    "VOICE": {
        "type": "category",
        "channels": [
            {
                "name": "General Voice",
                "type": "voice"
            },
            {
                "name": "Stream Talk",
                "type": "voice"
            },
            {
                "name": "AFK",
                "type": "voice"
            }
        ]
    }
}

RULES_TEXT = """## Server Rules

**1. Be respectful.** No harassment, hate speech, slurs, or personal attacks. Disagree with ideas, not people.

**2. No spam.** Don't flood channels with repeated messages, excessive caps, or meaningless content. This includes bot commands outside designated channels.

**3. Keep it relevant.** Post in the right channel. Streaming stuff goes in streaming channels, Nexus help goes in nexus-help, etc.

**4. Self-promo has limits.** You can share your channel/videos in #self-promo only. One post per day. Don't DM people to promote your stuff.

**5. No NSFW content.** This is a clean server. No explicit images, links, or discussions.

**6. Don't mini-mod.** If someone breaks a rule, ping a moderator or use the report function. Don't try to enforce rules yourself.

**7. No leaking or piracy.** Don't share paid content, cracked software, API keys, tokens, or anything that shouldn't be public.

**8. English only in public channels.** To keep moderation manageable, please use English in all public channels.

**9. Listen to staff.** Moderators and admins have the final say. If you're asked to stop something, stop.

**Breaking these rules can result in a warning, mute, kick, or ban depending on severity.**
"""

WELCOME_MESSAGE = """## Welcome to the Nexus Community

Nexus is a YouTube bot and analytics platform currently in beta. This server is the place to get help, report bugs, suggest features, and hang out with other streamers using Nexus.

**Quick links:**
- [Nexus Website](https://nexusbeta.vercel.app)
- [Help Center](https://nexusbeta.vercel.app/help)
- [FAQ](https://nexusbeta.vercel.app/faq)

**Getting started:**
1. Read the rules in #rules
2. Grab your roles in #pick-your-roles
3. Introduce yourself in #introductions
4. If you need help with Nexus, head to #nexus-help

**Need to set up the bot?**
Check #bot-setup-help or the [Help Center](https://nexusbeta.vercel.app/help) for a step-by-step guide on adding nexusbetabot as a moderator on your YouTube channel.
"""
```

### bot.py - Main Bot Entry Point

```python
import discord
from discord.ext import commands
import logging
import asyncio
from config import BOT_TOKEN, NEXUS_PURPLE

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
    activity=discord.Activity(type=discord.ActivityType.watching, name="nexusbeta.vercel.app")
)


@bot.event
async def on_ready():
    log.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    log.info(f"Connected to {len(bot.guilds)} server(s)")

    try:
        synced = await bot.tree.sync()
        log.info(f"Synced {len(synced)} slash command(s)")
    except Exception as e:
        log.error(f"Failed to sync commands: {e}")


@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name="welcome")
    if channel:
        embed = discord.Embed(
            title=f"Welcome, {member.display_name}!",
            description=(
                f"Hey {member.mention}, welcome to the Nexus community.\n\n"
                f"Check out #rules and grab your roles in #pick-your-roles.\n"
                f"If you need help with Nexus, head to #nexus-help."
            ),
            color=NEXUS_PURPLE
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Member #{member.guild.member_count}")
        await channel.send(embed=embed)

    member_role = discord.utils.get(member.guild.roles, name="Member")
    if member_role:
        try:
            await member.add_roles(member_role)
        except discord.Forbidden:
            pass


async def load_cogs():
    cog_list = [
        "cogs.server_setup",
        "cogs.notifications",
        "cogs.moderation",
        "cogs.info",
    ]
    for cog in cog_list:
        try:
            await bot.load_extension(cog)
            log.info(f"Loaded cog: {cog}")
        except Exception as e:
            log.error(f"Failed to load cog {cog}: {e}")


async def main():
    async with bot:
        await load_cogs()
        await bot.start(BOT_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
```

### cogs/server_setup.py - Server Setup Command

This is the main cog that builds out the entire server structure with one command.

```python
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from config import (
    ROLE_CONFIG, CHANNEL_CONFIG, RULES_TEXT,
    WELCOME_MESSAGE, NEXUS_PURPLE, NEXUS_BLUE
)


class ServerSetup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup-server", description="Set up the full Nexus server structure (Admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_server(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        log_messages = []

        try:
            # Phase 1: Create roles
            await interaction.followup.send("Starting server setup. This will take a minute...", ephemeral=True)

            log_messages.append("**Phase 1: Creating roles...**")
            created_roles = {}
            for role_name, role_data in ROLE_CONFIG.items():
                existing = discord.utils.get(guild.roles, name=role_name)
                if existing:
                    created_roles[role_name] = existing
                    log_messages.append(f"  Role `{role_name}` already exists, skipping")
                    continue

                perms = discord.Permissions()
                for perm_name, perm_value in role_data.get("permissions", {}).items():
                    setattr(perms, perm_name, perm_value)

                role = await guild.create_role(
                    name=role_name,
                    color=discord.Color(role_data["color"]),
                    permissions=perms,
                    hoist=role_data.get("hoist", False),
                    mentionable=role_data.get("mentionable", False)
                )
                created_roles[role_name] = role
                log_messages.append(f"  Created role: `{role_name}`")
                await asyncio.sleep(0.5)

            # Phase 2: Create categories and channels
            log_messages.append("\n**Phase 2: Creating channels...**")
            for category_name, category_data in CHANNEL_CONFIG.items():
                existing_cat = discord.utils.get(guild.categories, name=category_name)
                if existing_cat:
                    category = existing_cat
                    log_messages.append(f"  Category `{category_name}` already exists")
                else:
                    category = await guild.create_category(category_name)
                    log_messages.append(f"  Created category: `{category_name}`")
                    await asyncio.sleep(0.3)

                for ch_data in category_data.get("channels", []):
                    ch_name = ch_data["name"]

                    if ch_data["type"] == "voice":
                        existing_ch = discord.utils.get(guild.voice_channels, name=ch_name, category=category)
                        if existing_ch:
                            log_messages.append(f"    Voice channel `{ch_name}` already exists")
                            continue
                        await guild.create_voice_channel(name=ch_name, category=category)
                        log_messages.append(f"    Created voice channel: `{ch_name}`")
                    else:
                        existing_ch = discord.utils.get(guild.text_channels, name=ch_name, category=category)
                        if existing_ch:
                            log_messages.append(f"    Text channel `{ch_name}` already exists")
                            continue

                        overwrites = {
                            guild.default_role: discord.PermissionOverwrite(
                                read_messages=True,
                                send_messages=not ch_data.get("read_only", False)
                            )
                        }

                        if ch_data.get("staff_only"):
                            overwrites[guild.default_role] = discord.PermissionOverwrite(read_messages=False)
                            for staff_role_name in ["Admin", "Moderator", "Support Team"]:
                                staff_role = created_roles.get(staff_role_name)
                                if staff_role:
                                    overwrites[staff_role] = discord.PermissionOverwrite(
                                        read_messages=True, send_messages=True
                                    )

                        if ch_data.get("role_restricted"):
                            restricted_role = created_roles.get(ch_data["role_restricted"])
                            if restricted_role:
                                overwrites[guild.default_role] = discord.PermissionOverwrite(read_messages=False)
                                overwrites[restricted_role] = discord.PermissionOverwrite(
                                    read_messages=True, send_messages=True
                                )
                                for staff_role_name in ["Admin", "Moderator"]:
                                    staff_role = created_roles.get(staff_role_name)
                                    if staff_role:
                                        overwrites[staff_role] = discord.PermissionOverwrite(
                                            read_messages=True, send_messages=True
                                        )

                        channel = await guild.create_text_channel(
                            name=ch_name,
                            category=category,
                            topic=ch_data.get("topic", ""),
                            overwrites=overwrites
                        )
                        log_messages.append(f"    Created text channel: `{ch_name}`")

                    await asyncio.sleep(0.3)

            # Phase 3: Post welcome message and rules
            log_messages.append("\n**Phase 3: Posting initial content...**")

            rules_channel = discord.utils.get(guild.text_channels, name="rules")
            if rules_channel:
                rules_embed = discord.Embed(
                    title="Server Rules",
                    description=RULES_TEXT,
                    color=NEXUS_PURPLE
                )
                rules_embed.set_footer(text="Last updated: March 2026")
                await rules_channel.send(embed=rules_embed)
                log_messages.append("  Posted rules")

            welcome_channel = discord.utils.get(guild.text_channels, name="welcome")
            if welcome_channel:
                welcome_embed = discord.Embed(
                    description=WELCOME_MESSAGE,
                    color=NEXUS_BLUE
                )
                welcome_embed.set_thumbnail(url=self.bot.user.display_avatar.url)
                await welcome_channel.send(embed=welcome_embed)
                log_messages.append("  Posted welcome message")

            # Phase 4: Set up role picker
            roles_channel = discord.utils.get(guild.text_channels, name="pick-your-roles")
            if roles_channel:
                role_embed = discord.Embed(
                    title="Pick Your Roles",
                    description=(
                        "React to this message to get roles:\n\n"
                        "🔔 - **Notifications** - Get pinged for important announcements\n"
                        "📢 - **Updates** - Get pinged for Nexus platform updates\n"
                        "🎮 - **Streamer** - You stream on YouTube (unlocks self-promo)\n"
                        "🧪 - **Beta Tester** - You're testing beta features"
                    ),
                    color=NEXUS_PURPLE
                )
                role_msg = await roles_channel.send(embed=role_embed)
                for emoji in ["🔔", "📢", "🎮", "🧪"]:
                    await role_msg.add_reaction(emoji)
                log_messages.append("  Posted role picker")

            # Phase 5: Post FAQ
            faq_channel = discord.utils.get(guild.text_channels, name="faq")
            if faq_channel:
                faq_embed = discord.Embed(
                    title="Frequently Asked Questions",
                    color=NEXUS_PURPLE
                )
                faq_embed.add_field(
                    name="What is Nexus?",
                    value="Nexus is a YouTube bot and analytics platform. It moderates your live chat, tracks your channel stats, and gives you a dashboard to manage everything.",
                    inline=False
                )
                faq_embed.add_field(
                    name="Is Nexus free?",
                    value="Yes. Nexus is free during the beta period. No credit card needed.",
                    inline=False
                )
                faq_embed.add_field(
                    name="How do I set up the bot?",
                    value="Sign in at [nexusbeta.vercel.app](https://nexusbeta.vercel.app), add your channel, then add `nexusbetabot` as a moderator in YouTube Studio > Settings > Community. Full guide in #bot-setup-help or the [Help Center](https://nexusbeta.vercel.app/help).",
                    inline=False
                )
                faq_embed.add_field(
                    name="What platforms does Nexus support?",
                    value="YouTube right now. Twitch, Kick, and Twitter/X integrations are in development.",
                    inline=False
                )
                faq_embed.add_field(
                    name="I found a bug. Where do I report it?",
                    value="Post in #bug-reports with what happened, what you expected, and a screenshot if possible.",
                    inline=False
                )
                await faq_channel.send(embed=faq_embed)
                log_messages.append("  Posted FAQ")

            # Done
            log_messages.append("\n**Server setup complete.**")
            summary = "\n".join(log_messages)

            if len(summary) > 4000:
                for i in range(0, len(summary), 4000):
                    await interaction.followup.send(summary[i:i+4000], ephemeral=True)
            else:
                await interaction.followup.send(summary, ephemeral=True)

        except discord.Forbidden:
            await interaction.followup.send(
                "I don't have the required permissions. Make sure my role is above the roles I'm trying to create, and I have Administrator permission.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(f"Setup failed: {str(e)}", ephemeral=True)

    @app_commands.command(name="nuke-server", description="Remove all bot-created channels and roles (Admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def nuke_server(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        confirm_embed = discord.Embed(
            title="Are you sure?",
            description="This will delete all channels and roles created by the setup command. This cannot be undone.\n\nType `CONFIRM` in the next 30 seconds to proceed.",
            color=0xEF4444
        )
        await interaction.followup.send(embed=confirm_embed, ephemeral=True)

        def check(m):
            return m.author == interaction.user and m.content == "CONFIRM"

        try:
            await self.bot.wait_for("message", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await interaction.followup.send("Cancelled. No changes made.", ephemeral=True)
            return

        deleted = {"roles": 0, "channels": 0, "categories": 0}

        for role_name in ROLE_CONFIG:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                try:
                    await role.delete()
                    deleted["roles"] += 1
                    await asyncio.sleep(0.3)
                except discord.Forbidden:
                    pass

        for category_name in CHANNEL_CONFIG:
            category = discord.utils.get(guild.categories, name=category_name)
            if category:
                for channel in category.channels:
                    try:
                        await channel.delete()
                        deleted["channels"] += 1
                        await asyncio.sleep(0.3)
                    except discord.Forbidden:
                        pass
                try:
                    await category.delete()
                    deleted["categories"] += 1
                except discord.Forbidden:
                    pass

        await interaction.followup.send(
            f"Cleanup complete. Removed {deleted['roles']} roles, {deleted['channels']} channels, {deleted['categories']} categories.",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(ServerSetup(bot))
```

### cogs/notifications.py - Notification Management

```python
import discord
from discord.ext import commands
from discord import app_commands
from config import NEXUS_PURPLE


class Notifications(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.role_emoji_map = {
            "🔔": "Notifications",
            "📢": "Updates",
            "🎮": "Streamer",
            "🧪": "Beta Tester"
        }

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        channel = guild.get_channel(payload.channel_id)
        if not channel or channel.name != "pick-your-roles":
            return

        emoji = str(payload.emoji)
        role_name = self.role_emoji_map.get(emoji)
        if not role_name:
            return

        role = discord.utils.get(guild.roles, name=role_name)
        member = guild.get_member(payload.user_id)
        if role and member:
            try:
                await member.add_roles(role)
            except discord.Forbidden:
                pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.user_id == self.bot.user.id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        channel = guild.get_channel(payload.channel_id)
        if not channel or channel.name != "pick-your-roles":
            return

        emoji = str(payload.emoji)
        role_name = self.role_emoji_map.get(emoji)
        if not role_name:
            return

        role = discord.utils.get(guild.roles, name=role_name)
        member = guild.get_member(payload.user_id)
        if role and member:
            try:
                await member.remove_roles(role)
            except discord.Forbidden:
                pass

    @app_commands.command(name="live", description="Post a go-live notification (Streamer role required)")
    @app_commands.describe(
        title="Your stream title",
        url="Link to your YouTube stream"
    )
    async def go_live(self, interaction: discord.Interaction, title: str, url: str):
        streamer_role = discord.utils.get(interaction.guild.roles, name="Streamer")
        if streamer_role not in interaction.user.roles:
            await interaction.response.send_message("You need the Streamer role to use this command.", ephemeral=True)
            return

        notifications_role = discord.utils.get(interaction.guild.roles, name="Notifications")
        mention = notifications_role.mention if notifications_role else ""

        live_channel = discord.utils.get(interaction.guild.text_channels, name="live-alerts")
        if not live_channel:
            await interaction.response.send_message("Could not find the #live-alerts channel.", ephemeral=True)
            return

        embed = discord.Embed(
            title=title,
            url=url,
            description=f"**{interaction.user.display_name}** is now live on YouTube!",
            color=NEXUS_PURPLE
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="Watch Now", value=f"[Click here to watch]({url})", inline=False)
        embed.set_footer(text="Nexus Bot Notifications")
        embed.timestamp = discord.utils.utcnow()

        await live_channel.send(content=mention, embed=embed)
        await interaction.response.send_message("Live notification posted.", ephemeral=True)

    @app_commands.command(name="announce", description="Post an announcement (Admin/Mod only)")
    @app_commands.describe(
        title="Announcement title",
        message="Announcement content",
        ping="Whether to ping @everyone"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def announce(self, interaction: discord.Interaction, title: str, message: str, ping: bool = False):
        announcements_channel = discord.utils.get(interaction.guild.text_channels, name="announcements")
        if not announcements_channel:
            await interaction.response.send_message("Could not find #announcements channel.", ephemeral=True)
            return

        embed = discord.Embed(
            title=title,
            description=message,
            color=NEXUS_PURPLE
        )
        embed.set_footer(text=f"Posted by {interaction.user.display_name}")
        embed.timestamp = discord.utils.utcnow()

        content = "@everyone" if ping else None
        await announcements_channel.send(content=content, embed=embed)
        await interaction.response.send_message("Announcement posted.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Notifications(bot))
```

### cogs/moderation.py - Basic Moderation

```python
import discord
from discord.ext import commands
from discord import app_commands
from config import NEXUS_PURPLE


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="kick", description="Kick a member from the server")
    @app_commands.describe(member="The member to kick", reason="Reason for the kick")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick_member(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message("You can't kick someone with a higher or equal role.", ephemeral=True)
            return

        await member.kick(reason=reason)
        embed = discord.Embed(
            title="Member Kicked",
            description=f"**{member.display_name}** was kicked by {interaction.user.mention}\nReason: {reason}",
            color=0xF59E0B
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ban", description="Ban a member from the server")
    @app_commands.describe(member="The member to ban", reason="Reason for the ban")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban_member(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message("You can't ban someone with a higher or equal role.", ephemeral=True)
            return

        await member.ban(reason=reason)
        embed = discord.Embed(
            title="Member Banned",
            description=f"**{member.display_name}** was banned by {interaction.user.mention}\nReason: {reason}",
            color=0xEF4444
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="clear", description="Delete messages from a channel")
    @app_commands.describe(amount="Number of messages to delete (1-100)")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear_messages(self, interaction: discord.Interaction, amount: int):
        if amount < 1 or amount > 100:
            await interaction.response.send_message("Amount must be between 1 and 100.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"Deleted {len(deleted)} message(s).", ephemeral=True)

    @app_commands.command(name="timeout", description="Timeout a member")
    @app_commands.describe(
        member="The member to timeout",
        minutes="Duration in minutes",
        reason="Reason for the timeout"
    )
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout_member(self, interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "No reason provided"):
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message("You can't timeout someone with a higher or equal role.", ephemeral=True)
            return

        duration = discord.utils.utcnow() + __import__("datetime").timedelta(minutes=minutes)
        await member.timeout(duration, reason=reason)
        embed = discord.Embed(
            title="Member Timed Out",
            description=f"**{member.display_name}** was timed out for {minutes} minute(s) by {interaction.user.mention}\nReason: {reason}",
            color=0xF59E0B
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Moderation(bot))
```

### cogs/info.py - Info and Help Commands

```python
import discord
from discord.ext import commands
from discord import app_commands
from config import NEXUS_PURPLE, NEXUS_BLUE


class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Show all available commands")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Nexus Bot Commands",
            color=NEXUS_PURPLE
        )
        embed.add_field(
            name="General",
            value=(
                "`/help` - Show this message\n"
                "`/info` - Show server and Nexus info\n"
                "`/stats` - Show server stats\n"
                "`/nexus` - Link to the Nexus platform"
            ),
            inline=False
        )
        embed.add_field(
            name="Notifications",
            value=(
                "`/live` - Post a go-live alert (Streamer role)\n"
                "`/announce` - Post an announcement (Mod+)"
            ),
            inline=False
        )
        embed.add_field(
            name="Moderation",
            value=(
                "`/kick` - Kick a member (Mod+)\n"
                "`/ban` - Ban a member (Mod+)\n"
                "`/timeout` - Timeout a member (Mod+)\n"
                "`/clear` - Delete messages (Mod+)"
            ),
            inline=False
        )
        embed.add_field(
            name="Admin",
            value=(
                "`/setup-server` - Create all channels, roles, and content\n"
                "`/nuke-server` - Remove all bot-created channels and roles"
            ),
            inline=False
        )
        embed.set_footer(text="Nexus Bot")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="info", description="Show info about Nexus")
    async def info_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Nexus",
            description=(
                "YouTube bot and analytics platform. Currently in beta.\n\n"
                "**What it does:**\n"
                "- Moderates your YouTube live chat (spam, links, caps filtering)\n"
                "- Custom commands and timed messages\n"
                "- Channel analytics and growth tracking\n"
                "- Video performance monitoring\n"
                "- Discord webhook notifications\n\n"
                "**Links:**\n"
                "[Website](https://nexusbeta.vercel.app) | "
                "[Help Center](https://nexusbeta.vercel.app/help) | "
                "[FAQ](https://nexusbeta.vercel.app/faq)"
            ),
            color=NEXUS_PURPLE
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="stats", description="Show server statistics")
    async def stats_command(self, interaction: discord.Interaction):
        guild = interaction.guild
        embed = discord.Embed(
            title=f"{guild.name} Stats",
            color=NEXUS_BLUE
        )
        embed.add_field(name="Members", value=str(guild.member_count), inline=True)
        embed.add_field(name="Channels", value=str(len(guild.channels)), inline=True)
        embed.add_field(name="Roles", value=str(len(guild.roles)), inline=True)
        embed.add_field(name="Boosts", value=str(guild.premium_subscription_count), inline=True)
        embed.add_field(name="Boost Level", value=str(guild.premium_tier), inline=True)
        embed.add_field(name="Created", value=guild.created_at.strftime("%b %d, %Y"), inline=True)
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="nexus", description="Get a link to the Nexus platform")
    async def nexus_link(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Nexus Platform",
            description="[Click here to open Nexus](https://nexusbeta.vercel.app)\n\nSign in with Google to get started. It's free during beta.",
            color=NEXUS_PURPLE
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Info(bot))
```

### utils/embed_builder.py - Reusable Embed Templates

```python
import discord
from config import NEXUS_PURPLE, NEXUS_BLUE


def live_notification(channel_name, stream_title, stream_url, thumbnail_url=None):
    embed = discord.Embed(
        title=stream_title,
        url=stream_url,
        description=f"**{channel_name}** is now live on YouTube!",
        color=NEXUS_PURPLE
    )
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    embed.add_field(name="Status", value="Live Now", inline=True)
    embed.add_field(name="Platform", value="YouTube", inline=True)
    embed.set_footer(text="Nexus Bot Notifications")
    embed.timestamp = discord.utils.utcnow()
    return embed


def milestone_notification(channel_name, milestone, subscriber_count, thumbnail_url=None):
    embed = discord.Embed(
        title=f"{channel_name} hit {milestone} subscribers!",
        description=f"Current count: **{subscriber_count:,}**",
        color=0xF59E0B
    )
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    embed.set_footer(text="Nexus Bot Notifications")
    embed.timestamp = discord.utils.utcnow()
    return embed


def error_embed(title, description):
    return discord.Embed(title=title, description=description, color=0xEF4444)


def success_embed(title, description):
    return discord.Embed(title=title, description=description, color=0x10B981)
```

---

## Part 4: Connecting the Bot to the Nexus Website

This is how you would eventually let users manage Discord notifications from the Nexus dashboard.

### How It Works

1. **User links their Discord account on Nexus** - Add a "Connect Discord" button in the Nexus Integrations tab. This uses Discord OAuth2 to get their Discord user ID and the servers they're in.

2. **Nexus stores the Discord user ID** - Add a `discord_user_id` column to the User model in `app.py`.

3. **Bot receives webhook calls from Nexus** - When a user goes live or hits a milestone, Nexus sends an HTTP request to the bot's API (or directly uses the Discord webhook URL already stored per channel).

4. **Bot posts to the right channel** - The bot looks up the user's notification preferences and posts to #live-alerts or #milestone-alerts.

### What to Add to Nexus (app.py)

Add these database columns to the User model:

```python
discord_user_id = db.Column(db.String(255), nullable=True)
discord_server_id = db.Column(db.String(255), nullable=True)
```

Add a Discord OAuth route:

```python
@app.route('/auth/discord')
@login_required
def discord_auth():
    discord_client_id = os.environ.get('DISCORD_CLIENT_ID')
    redirect_uri = url_for('discord_callback', _external=True)
    scope = 'identify guilds'
    return redirect(
        f'https://discord.com/api/oauth2/authorize?client_id={discord_client_id}'
        f'&redirect_uri={redirect_uri}&response_type=code&scope={scope}'
    )

@app.route('/auth/discord/callback')
@login_required
def discord_callback():
    code = request.args.get('code')
    # Exchange code for token, get user info, save discord_user_id
    # Standard OAuth2 flow with discord.com/api/oauth2/token
    pass
```

### What to Add to the Bot

Add an API endpoint the Nexus website can call:

```python
from aiohttp import web

async def handle_notification(request):
    data = await request.json()
    notification_type = data.get("type")  # "live" or "milestone"
    guild_id = data.get("guild_id")
    channel_name = data.get("channel_name")
    
    guild = bot.get_guild(int(guild_id))
    if not guild:
        return web.json_response({"error": "Guild not found"}, status=404)
    
    if notification_type == "live":
        channel = discord.utils.get(guild.text_channels, name="live-alerts")
        if channel:
            embed = live_notification(
                data["channel_name"],
                data.get("stream_title", "Live Stream"),
                data.get("stream_url", ""),
                data.get("thumbnail_url")
            )
            notifications_role = discord.utils.get(guild.roles, name="Notifications")
            content = notifications_role.mention if notifications_role else None
            await channel.send(content=content, embed=embed)
    
    return web.json_response({"status": "sent"})

# Run alongside the bot
app_web = web.Application()
app_web.router.add_post("/api/notification", handle_notification)
```

---

## Part 5: Running the Bot

### Local Development

```bash
cd nexus-discord-bot
pip install -r requirements.txt
python bot.py
```

### On Replit

1. Create a new Replit project
2. Add the bot code
3. Set `DISCORD_BOT_TOKEN` in Secrets
4. Run `python bot.py`
5. Use UptimeRobot or similar to keep it alive (or deploy it)

### On a VPS

```bash
git clone your-repo
cd nexus-discord-bot
pip install -r requirements.txt
# Use screen, tmux, or systemd to keep it running
python bot.py
```

---

## Part 6: Server Structure Summary

When you run `/setup-server`, the bot creates this:

### Roles (top to bottom)
| Role | Color | Purpose |
|------|-------|---------|
| Admin | Red | Full server access |
| Moderator | Amber | Message management, kick/ban |
| Support Team | Green | Help desk, message management |
| Beta Tester | Purple | Access to beta-testing channel |
| Subscriber | Indigo | YouTube subscribers |
| Streamer | Pink | Can use /live and post in self-promo |
| Nexus User | Gray | Verified Nexus account holder |
| Notifications | Blue | Pingable for announcements |
| Updates | Teal | Pingable for platform updates |
| Member | Slate | Auto-assigned on join |

### Channels
| Category | Channels | Access |
|----------|----------|--------|
| WELCOME & INFO | welcome, rules, announcements, pick-your-roles, faq | Read-only for members |
| GENERAL | general, introductions, off-topic, memes | Everyone |
| NEXUS PLATFORM | nexus-help, feature-requests, bug-reports, bot-setup-help, showcase | Everyone |
| STREAMING | stream-chat, self-promo, collabs, milestones | Everyone |
| NOTIFICATIONS | live-alerts, milestone-alerts, changelog | Read-only (bot posts here) |
| DEVELOPMENT | dev-updates, beta-testing, api-discussion | Staff / Beta Testers |
| VOICE | General Voice, Stream Talk, AFK | Everyone |

---

## Part 7: What Comes After

Once the bot and server are set up, here's how it connects back to Nexus:

1. **Discord OAuth on Nexus** - Users link their Discord account from the Settings page. This stores their Discord user ID so Nexus knows who they are on Discord.

2. **Auto role assignment** - When a user links their Nexus account, the bot automatically gives them the "Nexus User" role in the Discord server.

3. **Live notifications from Nexus** - Instead of users manually running `/live`, Nexus detects when they go live on YouTube and tells the bot to post in #live-alerts automatically.

4. **Milestone alerts** - When Nexus detects a subscriber milestone (1K, 5K, 10K, etc.), it tells the bot to post in #milestone-alerts.

5. **Notification preferences on Nexus** - Users can toggle which Discord notifications they want from their Nexus dashboard (under Integrations). The bot respects those preferences.

6. **Bug reports from Discord to Nexus** - Messages posted in #bug-reports could be forwarded to a Nexus admin panel or stored in the database for tracking.

This turns the Discord server into a live extension of the Nexus platform rather than just a separate community server.
