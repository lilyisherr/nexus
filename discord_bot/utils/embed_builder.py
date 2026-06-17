import discord
from config import NEXUS_PURPLE, NEXUS_BLUE, NEXUS_GREEN, NEXUS_ICON


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
    milestones_emoji = {
        100: "\U0001f389", 500: "\U0001f389", 1000: "\U0001f973", 5000: "\U0001f525",
        10000: "\U0001f525", 25000: "\u2b50", 50000: "\u2b50", 100000: "\U0001f48e",
        500000: "\U0001f48e", 1000000: "\U0001f451",
    }
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
