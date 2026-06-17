import discord
from discord.ext import commands
from discord import app_commands
import datetime
from config import NEXUS_ICON, NEXUS_PURPLE, NEXUS_BLUE


def _nexus_footer(embed):
    embed.set_footer(text="Nexus", icon_url=NEXUS_ICON)
    embed.timestamp = discord.utils.utcnow()
    return embed


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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


async def setup(bot):
    await bot.add_cog(Moderation(bot))
