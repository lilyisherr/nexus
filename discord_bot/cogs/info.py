import discord
from discord.ext import commands
from discord import app_commands
from config import NEXUS_PURPLE, NEXUS_BLUE, NEXUS_ICON


def _nexus_footer(embed):
    embed.set_footer(text="Nexus", icon_url=NEXUS_ICON)
    embed.timestamp = discord.utils.utcnow()
    return embed


class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
            name="Server Setup",
            value="`/setup-server` - Build the full server\n`/reset-server` - Remove all bot content\n`/post-verify` - Post verify button\n`/post-faq` - Post FAQ dashboard\n`/post-roles` - Post role pickers",
            inline=False,
        )
        embed.add_field(
            name="Admin Tools",
            value="`/broadcast` - Post embed to any channel\n`/setstatus` - Change bot status\n`/botstats` - Bot statistics\n`/guildlist` - List all servers\n`/purgebots` - Remove bots from voice\n`/slowmodeall` - Slowmode entire category\n`/dm` - DM a user (owner only)",
            inline=False,
        )
        _nexus_footer(embed)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="info", description="About Nexus")
    async def info_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Nexus",
            description=(
                "YouTube bot and analytics platform, currently in beta.\n\n"
                "**What it does:**\n"
                "- Moderates your YouTube live chat automatically\n"
                "- Custom commands and timed messages\n"
                "- Channel analytics and growth tracking\n"
                "- Video performance monitoring\n"
                "- Discord integration for live notifications\n\n"
                "**Coming soon:** Twitch, Kick, and Twitter/X support"
            ),
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


async def setup(bot):
    await bot.add_cog(Info(bot))
