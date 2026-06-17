import discord
from discord.ext import commands
from discord import app_commands
from config import NEXUS_PURPLE, NEXUS_ICON, ROLE_EMOJI_MAP, COLOR_ROLE_EMOJI_MAP, ALL_COLOR_ROLES


def _nexus_footer(embed):
    embed.set_footer(text="Nexus", icon_url=NEXUS_ICON)
    embed.timestamp = discord.utils.utcnow()
    return embed


class Notifications(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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



async def setup(bot):
    await bot.add_cog(Notifications(bot))
