import discord
from discord.ext import commands
from discord import app_commands
import datetime
import platform
import os
try:
    import psutil as _psutil
except ImportError:
    _psutil = None
from config import NEXUS_ICON, NEXUS_PURPLE, NEXUS_GREEN

import logging
log = logging.getLogger("nexus-bot")


def _nexus_footer(embed):
    embed.set_footer(text="Nexus", icon_url=NEXUS_ICON)
    embed.timestamp = discord.utils.utcnow()
    return embed


async def _check_owner(bot, user: discord.User) -> bool:
    return await bot.is_owner(user)


def _is_admin(interaction: discord.Interaction) -> bool:
    if not interaction.guild:
        return False
    return (
        interaction.user.guild_permissions.administrator
        or interaction.user.guild_permissions.manage_guild
    )


class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="botstats", description="Show Nexus bot statistics (admin only)")
    async def botstats(self, interaction: discord.Interaction):
        if not _is_admin(interaction):
            await interaction.response.send_message("You need Administrator or Manage Guild permissions.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        guilds = self.bot.guilds
        total_members = sum(g.member_count or 0 for g in guilds)
        total_channels = sum(len(g.channels) for g in guilds)
        latency_ms = round(self.bot.latency * 1000, 1)

        try:
            if _psutil:
                cpu = _psutil.cpu_percent(interval=0.5)
                mem = _psutil.virtual_memory()
                mem_str = f"{mem.used // 1024 // 1024}MB / {mem.total // 1024 // 1024}MB ({mem.percent}%)"
            else:
                cpu = None
                mem_str = "N/A"
        except Exception:
            cpu = None
            mem_str = "N/A"

        embed = discord.Embed(title="Nexus Bot Statistics", color=NEXUS_PURPLE)
        embed.add_field(name="Servers", value=f"{len(guilds):,}", inline=True)
        embed.add_field(name="Total Members", value=f"{total_members:,}", inline=True)
        embed.add_field(name="Channels", value=f"{total_channels:,}", inline=True)
        embed.add_field(name="Latency", value=f"{latency_ms}ms", inline=True)
        embed.add_field(name="Python", value=platform.python_version(), inline=True)
        embed.add_field(name="discord.py", value=discord.__version__, inline=True)
        if cpu is not None:
            embed.add_field(name="CPU", value=f"{cpu}%", inline=True)
        embed.add_field(name="RAM", value=mem_str, inline=True)
        _nexus_footer(embed)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="setstatus", description="Manually set the bot's status (admin only)")
    @app_commands.describe(
        status_type="Type of activity",
        text="Status text",
        online_status="Online presence indicator"
    )
    @app_commands.choices(
        status_type=[
            app_commands.Choice(name="Watching", value="watching"),
            app_commands.Choice(name="Playing", value="playing"),
            app_commands.Choice(name="Listening to", value="listening"),
            app_commands.Choice(name="Competing in", value="competing"),
            app_commands.Choice(name="Streaming", value="streaming"),
        ],
        online_status=[
            app_commands.Choice(name="Online", value="online"),
            app_commands.Choice(name="Idle", value="idle"),
            app_commands.Choice(name="Do Not Disturb", value="dnd"),
        ]
    )
    async def setstatus(self, interaction: discord.Interaction, status_type: str, text: str, online_status: str = "online"):
        if not _is_admin(interaction):
            await interaction.response.send_message("You need Administrator or Manage Guild permissions.", ephemeral=True)
            return
        presence = {
            "online": discord.Status.online,
            "idle": discord.Status.idle,
            "dnd": discord.Status.do_not_disturb,
        }.get(online_status, discord.Status.online)

        if status_type == "streaming":
            activity = discord.Streaming(name=text, url="https://nexusbeta.vercel.app")
        elif status_type == "playing":
            activity = discord.Game(name=text)
        elif status_type == "listening":
            activity = discord.Activity(type=discord.ActivityType.listening, name=text)
        elif status_type == "competing":
            activity = discord.Activity(type=discord.ActivityType.competing, name=text)
        else:
            activity = discord.Activity(type=discord.ActivityType.watching, name=text)

        await self.bot.change_presence(status=presence, activity=activity)
        embed = discord.Embed(
            title="Status Updated",
            description=f"**{status_type.capitalize()}** {text}\nPresence: **{online_status}**",
            color=NEXUS_GREEN,
        )
        _nexus_footer(embed)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="guildlist", description="List all servers the bot is in (admin only)")
    async def guildlist(self, interaction: discord.Interaction):
        if not await _check_owner(self.bot, interaction.user) and not _is_admin(interaction):
            await interaction.response.send_message("This command requires Administrator permissions.", ephemeral=True)
            return
        guilds = sorted(self.bot.guilds, key=lambda g: g.member_count or 0, reverse=True)
        lines = [f"`{i+1}.` **{g.name}** — {g.member_count:,} members (ID: {g.id})" for i, g in enumerate(guilds[:20])]
        description = "\n".join(lines)
        if len(guilds) > 20:
            description += f"\n\n*…and {len(guilds) - 20} more*"
        embed = discord.Embed(
            title=f"Servers ({len(guilds)} total)",
            description=description or "No servers.",
            color=NEXUS_PURPLE,
        )
        _nexus_footer(embed)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="dm", description="Send a DM to a user (owner only)")
    @app_commands.describe(user="The user to DM", message="The message to send")
    async def dm_user(self, interaction: discord.Interaction, user: discord.Member, message: str):
        if not await _check_owner(self.bot, interaction.user):
            await interaction.response.send_message("This command is owner-only.", ephemeral=True)
            return
        try:
            embed = discord.Embed(
                title="Message from Nexus",
                description=message,
                color=NEXUS_PURPLE,
            )
            _nexus_footer(embed)
            await user.send(embed=embed)
            await interaction.response.send_message(f"✅ DM sent to **{user.display_name}**.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Could not DM that user — they may have DMs disabled.", ephemeral=True)

    @app_commands.command(name="broadcast", description="Post a custom embed to any channel (admin only)")
    @app_commands.describe(
        channel="Channel to post in",
        title="Embed title",
        message="Embed body text",
        color="Hex color (e.g. #6366f1)",
        ping_everyone="Whether to @everyone ping above the embed"
    )
    @app_commands.choices(ping_everyone=[
        app_commands.Choice(name="Yes", value="yes"),
        app_commands.Choice(name="No", value="no"),
    ])
    async def broadcast(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        title: str,
        message: str,
        color: str = "#6366f1",
        ping_everyone: str = "no",
    ):
        if not _is_admin(interaction):
            await interaction.response.send_message("You need Administrator or Manage Guild permissions.", ephemeral=True)
            return
        try:
            color_int = int(color.strip("#"), 16)
        except ValueError:
            color_int = 0x6366F1
        embed = discord.Embed(title=title, description=message, color=color_int)
        _nexus_footer(embed)
        content = "@everyone" if ping_everyone == "yes" else None
        try:
            await channel.send(content=content, embed=embed)
            await interaction.response.send_message(f"✅ Announcement posted in {channel.mention}.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(f"❌ Missing permissions to post in {channel.mention}.", ephemeral=True)

    @app_commands.command(name="purgebots", description="Remove all bot accounts from a voice channel (admin only)")
    @app_commands.describe(channel="Voice channel to clean bots from")
    async def purgebots(self, interaction: discord.Interaction, channel: discord.VoiceChannel = None):
        if not _is_admin(interaction):
            await interaction.response.send_message("You need Administrator or Manage Guild permissions.", ephemeral=True)
            return
        if not channel and interaction.user.voice:
            channel = interaction.user.voice.channel
        if not channel:
            await interaction.response.send_message("Please specify a voice channel or be in one.", ephemeral=True)
            return
        bots_kicked = 0
        for member in list(channel.members):
            if member.bot:
                try:
                    await member.move_to(None, reason=f"/purgebots by {interaction.user}")
                    bots_kicked += 1
                except discord.Forbidden:
                    pass
        embed = discord.Embed(
            title="Bots Removed",
            description=f"Removed **{bots_kicked}** bot(s) from **{channel.name}**.",
            color=NEXUS_GREEN,
        )
        _nexus_footer(embed)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="slowmodeall", description="Set slowmode on all channels in a category (admin only)")
    @app_commands.describe(category="Category to apply slowmode to", seconds="Slowmode in seconds (0 to disable)")
    async def slowmodeall(self, interaction: discord.Interaction, category: discord.CategoryChannel, seconds: int):
        if not _is_admin(interaction):
            await interaction.response.send_message("You need Administrator or Manage Guild permissions.", ephemeral=True)
            return
        if seconds < 0 or seconds > 21600:
            await interaction.response.send_message("Slowmode must be between 0 and 21600 seconds.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        updated = 0
        for ch in category.text_channels:
            try:
                await ch.edit(slowmode_delay=seconds)
                updated += 1
            except discord.Forbidden:
                pass
        embed = discord.Embed(
            title="Slowmode Applied",
            description=f"Set {seconds}s slowmode on **{updated}** channel(s) in **{category.name}**.",
            color=NEXUS_GREEN,
        )
        _nexus_footer(embed)
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Owner(bot))
