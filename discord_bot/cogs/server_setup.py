import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from config import (
    ROLE_CONFIG, CHANNEL_CONFIG, RULES_TEXT,
    WELCOME_MESSAGE, NEXUS_PURPLE, NEXUS_BLUE, NEXUS_GREEN,
    NEXUS_ICON, STAFF_ROLES, FAQ_SECTIONS,
)
from cogs.logging import suppress_logging, resume_logging


def _nexus_footer(embed):
    embed.set_footer(text="Nexus", icon_url=NEXUS_ICON)
    embed.timestamp = discord.utils.utcnow()
    return embed


class VerifyButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Verify", style=discord.ButtonStyle.green, custom_id="nexus_verify_btn_cog", emoji="\u2705")
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
        except discord.Forbidden:
            await interaction.response.send_message("Something went wrong. Contact a moderator.", ephemeral=True)


class ServerSetup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

        await interaction.followup.send("Type `CONFIRM` in the next 30 seconds to reset the server. This deletes all bot-created channels and roles.", ephemeral=True)

        def check(m):
            return m.author == interaction.user and m.content == "CONFIRM"

        try:
            await self.bot.wait_for("message", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            try:
                await interaction.followup.send("Cancelled.", ephemeral=True)
            except discord.HTTPException:
                pass
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
        except discord.HTTPException:
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


async def setup(bot):
    await bot.add_cog(ServerSetup(bot))
