import discord
from discord.ext import commands
import aiohttp
import logging
from config import NEXUS_API_URL, NEXUS_API_KEY, NEXUS_PURPLE, NEXUS_BLUE, NEXUS_ICON

log = logging.getLogger("nexus-bot")

_setup_guilds = set()


def suppress_logging(guild_id):
    _setup_guilds.add(guild_id)


def resume_logging(guild_id):
    _setup_guilds.discard(guild_id)


class Logging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

    async def _send_to_api(self, data):
        if not NEXUS_API_KEY:
            return
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{NEXUS_API_URL.rstrip('/')}/bot/api/logs"
                headers = {"Content-Type": "application/json", "X-Nexus-Bot-Key": NEXUS_API_KEY}
                async with session.post(url, json=data, headers=headers, timeout=aiohttp.ClientTimeout(total=10)):
                    pass
        except Exception:
            pass

    async def _log_action(self, guild, action_type, embed, moderator=None, target=None, reason=None, details=None):
        await self._send_log(guild, embed)
        await self._send_to_api({
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
            await self._send_to_api({
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


async def setup(bot):
    await bot.add_cog(Logging(bot))
