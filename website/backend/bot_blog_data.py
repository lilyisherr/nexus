BOT_BLOG_POSTS = [
    {
        "slug": "march-2026-changelog",
        "title": "March 2026 Changelog: Auto-Sync, Connection Status, and More",
        "date": "March 9, 2026",
        "date_short": "Mar 9, 2026",
        "tag": "announcement",
        "tag_label": "Announcement",
        "summary": "A big batch of updates this month: auto-sync for channels and roles, bot connection status on the dashboard, a Discord community server, and several bug fixes.",
        "content": """
            <p>This is a pretty significant update. Here is everything that changed:</p>
            <h3>Auto Channel and Role Sync</h3>
            <p>The dashboard now automatically detects channels and roles that the Nexus bot created during server setup. If you have channels named things like "announcements", "mod-logs", "welcome", or "suggestions", they will be pre-filled in your server settings without you having to manually pick them from dropdowns. Same goes for roles like "Admin", "Moderator", "Muted", and "Verified".</p>
            <p>This only fills in values that are currently empty, so it will never override something you already set.</p>
            <h3>Bot Connection Status</h3>
            <p>The dashboard now shows whether the Nexus bot is actually in each of your servers. If the bot is not in a server, you will see an "Invite Bot" button right on the server card instead of having to find the invite link elsewhere.</p>
            <h3>Discord Community Server</h3>
            <p>We now have a Discord server where you can chat with other users, report bugs, request features, and get help. Join at <a href="https://discord.gg/mzxHumP5nR" target="_blank">discord.gg/mzxHumP5nR</a>.</p>
            <h3>Bug Fixes</h3>
            <ul>
                <li>Fixed reaction roles not re-granting when a reaction was removed and re-added</li>
                <li>Fixed dashboard layout breaking on mobile screens</li>
                <li>Fixed channel sync failing for newly created accounts</li>
                <li>Fixed role hierarchy permissions causing 403 errors</li>
                <li>Fixed server setup wizard creating duplicate channels on re-run</li>
                <li>Reduced command response delays during peak hours</li>
            </ul>
            <h3>Other Changes</h3>
            <ul>
                <li>Added beta warning banner across all pages</li>
                <li>Removed Discord connect integration from YouTube bot account settings</li>
                <li>Improved webhook notification delivery speed</li>
            </ul>
        """
    },
    {
        "slug": "discord-community-launched",
        "title": "Join the Nexus Discord Community",
        "date": "March 9, 2026",
        "date_short": "Mar 9, 2026",
        "tag": "announcement",
        "tag_label": "Announcement",
        "summary": "We finally have an official Discord server for the Nexus community. Come hang out, report bugs, request features, and connect with other streamers.",
        "content": """
            <p>This has been requested for a while and it is finally here. The Nexus Discord server is live and open to everyone.</p>
            <p>You can join at <a href="https://discord.gg/mzxHumP5nR" target="_blank">discord.gg/mzxHumP5nR</a>.</p>
            <h3>What is the server for?</h3>
            <p>A few things:</p>
            <ul>
                <li><strong>Bug reports</strong> - Found something broken? Drop it in the bug reports channel and I will look at it.</li>
                <li><strong>Feature requests</strong> - Have an idea for something the bot should do? Let me know.</li>
                <li><strong>General chat</strong> - Talk with other streamers who use Nexus. Share tips, ask questions, whatever.</li>
                <li><strong>Announcements</strong> - Updates, new features, and maintenance notices will be posted here first.</li>
                <li><strong>Beta testing</strong> - Get early access to new features before they go live.</li>
            </ul>
            <p>The server is brand new so it is still small, but that is fine. I would rather have a small group of people who actually use the bot than a huge server full of noise.</p>
        """
    },
    {
        "slug": "dashboard-improvements-march",
        "title": "Dashboard Quality of Life Improvements",
        "date": "March 8, 2026",
        "date_short": "Mar 8, 2026",
        "tag": "feature",
        "tag_label": "Feature",
        "summary": "Several improvements to the bot dashboard including better mobile layout, smarter channel detection, and a cleaner server card design.",
        "content": """
            <p>Spent the last few days polishing the dashboard. Nothing flashy, just making things work better.</p>
            <h3>Mobile Layout Fix</h3>
            <p>Server cards were overflowing on small screens. The grid now properly collapses to a single column on mobile and the padding is adjusted so nothing gets cut off.</p>
            <h3>Smarter Channel Detection</h3>
            <p>When you open your server settings, the dashboard now looks at your channel names and automatically fills in the right dropdowns. If you have a channel called "announcements" it will be pre-selected as your announcement channel. Same for mod-logs, welcome, suggestions, and others.</p>
            <p>This only applies to empty fields. If you have already configured a channel for a specific purpose, the auto-detection will not override your choice.</p>
            <h3>Server Card Redesign</h3>
            <p>Each server card now clearly shows whether the bot is in that server. If it is not, you get an invite button right there instead of having to dig around for the invite link. Small change but it makes the onboarding flow much smoother.</p>
        """
    },
    {
        "slug": "discord-bot-beta-launch",
        "title": "The Discord Bot is in Beta",
        "date": "March 20, 2026",
        "date_short": "Mar 20, 2026",
        "tag": "announcement",
        "tag_label": "Announcement",
        "summary": "After four months of building, the Nexus Discord bot is live in beta. Here is what it can do and how to get it running on your server.",
        "content": """
            <p>The bot is finally out there. It took about four months from the first line of code to something I felt comfortable letting other people use, and even now there are rough edges. But it works, and servers are using it, so I am calling it a beta and shipping it.</p>
            <p>Right now the bot handles server setup with a guided builder, moderation tools like auto-mod and warning tracking, a logging system that records joins, leaves, message edits, and deletions, plus a welcome system with auto-role assignment. There is also a web dashboard where you can manage your server settings without touching Discord slash commands if you prefer that.</p>
            <p>The thing I am most proud of is the server builder. When you first add the bot, it walks you through setting up channels, roles, and permissions with a series of prompts. It is not perfect and it makes assumptions about what a "standard" server looks like, but the feedback so far has been that it saves a lot of tedious setup work.</p>
            <p>If you run into bugs or the bot does something unexpected, let me know. I am actively watching logs and fixing things as reports come in. This is a one-person project so I can not catch everything in testing, but I can usually push a fix the same day.</p>
        """
    },
    {
        "slug": "web-dashboard-for-discord",
        "title": "Building a Web Dashboard for the Bot",
        "date": "February 25, 2026",
        "date_short": "Feb 25, 2026",
        "tag": "devlog",
        "tag_label": "Dev Log",
        "summary": "Managing a Discord bot through slash commands alone is painful. So I built a web dashboard for server configuration, logs, and bot status.",
        "content": """
            <p>Slash commands are fine for quick actions, but trying to configure moderation rules, review logs, and manage server settings entirely through Discord is a bad experience. I knew early on that I wanted a web dashboard, but I kept pushing it off because the bot itself needed to work first.</p>
            <p>The dashboard lets server admins log in with their Discord account, see a list of servers where the bot is active, and manage everything from a browser. You can toggle features on and off, configure auto-mod thresholds, view recent logs, and check the bot status. It is basically a control panel for everything the bot does.</p>
            <p>The hardest part was syncing state between the dashboard and the bot. When someone changes a setting on the web, the bot needs to pick that up without restarting. I ended up using a shared database where both the web app and the bot read from the same tables. The bot polls for config changes every 30 seconds, which is not instant but is good enough that you do not notice the delay in practice.</p>
            <p>Authentication was another headache. Discord OAuth is straightforward for getting a user token, but figuring out which servers they have admin access to requires checking permissions through the Discord API. I cache that data for an hour so the dashboard loads fast, but it means permission changes can take up to an hour to reflect on the web side.</p>
            <p>The dashboard is not flashy. It is dark-themed to match Discord, has a clean sidebar navigation, and focuses on being functional. I would rather it be boring and reliable than pretty and broken.</p>
        """
    },
    {
        "slug": "moderation-and-logging",
        "title": "Auto-Mod, Warnings, and the Logging System",
        "date": "February 8, 2026",
        "date_short": "Feb 8, 2026",
        "tag": "feature",
        "tag_label": "Feature",
        "summary": "The moderation and logging systems are done. Here is how auto-mod works, how warnings stack up, and what the bot tracks in server logs.",
        "content": """
            <p>Moderation was the feature I spent the most time on because getting it wrong means real consequences for servers. If the bot accidentally bans someone or misses actual spam, that is a problem. So I was careful about defaults and made almost everything configurable.</p>
            <p>Auto-mod currently handles spam detection, mass mention filtering, invite link blocking, and excessive caps. Each filter can be turned on or off individually, and the thresholds are adjustable. Spam detection looks at message frequency and content repetition. If someone sends the same message three times in ten seconds, the bot catches it. Mass mention filtering triggers when a message tags more than five users at once, which is almost always spam or trolling.</p>
            <p>The warning system tracks infractions per user. Each auto-mod violation adds a warning, and admins can issue manual warnings through slash commands. Warnings stack up and you can set automatic actions at thresholds. For example, three warnings could trigger a mute, five could trigger a kick, and ten could trigger a ban. The thresholds are configurable per server.</p>
            <p>Logging was simpler to build but took a while to get the output right. The bot records member joins and leaves, message edits and deletions, role changes, channel updates, and moderation actions. All of this goes to a designated log channel that the admin picks during setup. I spent a lot of time on the embed formatting so the logs are actually readable at a glance instead of walls of text.</p>
            <p>One thing I learned: people care a lot about deleted message logging. Being able to see what someone said before they deleted it is apparently the most popular feature in any Discord bot. I did not expect that going in but it makes sense for moderation purposes.</p>
        """
    },
    {
        "slug": "welcome-system-auto-role",
        "title": "Welcome Messages and Auto-Role Assignment",
        "date": "January 28, 2026",
        "date_short": "Jan 28, 2026",
        "tag": "feature",
        "tag_label": "Feature",
        "summary": "New members now get a customizable welcome message and automatic role assignment. Sounds simple, but the edge cases were not.",
        "content": """
            <p>Welcome messages and auto-roles are two features that every Discord server wants, and they seem trivial until you actually build them. The basic version took a day. Handling all the edge cases took two weeks.</p>
            <p>The welcome system sends a message to a designated channel when a new member joins. The message is fully customizable with variables like {user} for a mention, {server} for the server name, and {count} for the current member count. You can also set a welcome DM that gets sent privately, though a lot of users have DMs from server members disabled so it fails silently more often than you would think.</p>
            <p>Auto-role assigns one or more roles to new members automatically. The obvious use case is giving everyone a "Member" role that grants access to the main channels while keeping announcement channels visible to everyone. The tricky part was role hierarchy. The bot can only assign roles that are below its own role in the Discord hierarchy, and a lot of admins do not realize this. I added a check that warns you during setup if the roles you picked are not assignable.</p>
            <p>Edge cases that bit me: members joining and immediately leaving before the bot processes the event, members rejoining a server they were previously banned from (the auto-role should not fire), servers with verification levels that delay the member join event, and Discord rate limits that throttle role assignments during raids. Each of these required specific handling.</p>
            <p>The raid scenario was the worst. If fifty people join in ten seconds, the bot tries to assign roles to all of them and Discord starts rate limiting the requests. I added a queue system that processes role assignments at a rate Discord is comfortable with, which means during a raid the assignments happen over a minute or two instead of all at once.</p>
        """
    },
    {
        "slug": "slash-commands-permissions",
        "title": "Migrating to Slash Commands",
        "date": "January 10, 2026",
        "date_short": "Jan 10, 2026",
        "tag": "devlog",
        "tag_label": "Dev Log",
        "summary": "Discord deprecated prefix commands for verified bots. Here is how I moved everything to slash commands and set up the permission system.",
        "content": """
            <p>When I started building the bot, I used prefix commands. Type !ban @user and the bot bans them. Simple, familiar, and easy to implement. Then I read the Discord developer docs more carefully and realized that verified bots can no longer read message content by default. Which means prefix commands do not work unless users explicitly grant that intent, and most will not bother.</p>
            <p>So I migrated everything to slash commands. Instead of !ban @user, it is /ban user:@someone reason:spamming. Discord handles the argument parsing, type validation, and autocomplete. It is actually a better user experience, but the migration was tedious because every command needed to be restructured.</p>
            <p>The permission system was the part I spent the most time on. Discord has its own permissions model where server admins can control which roles can use which commands. I integrated with that instead of building my own permission layer. So if an admin says only moderators can use /ban, that is enforced by Discord itself and the bot does not need to check.</p>
            <p>For settings commands, I added a /config group with subcommands: /config automod, /config welcome, /config logging, and so on. Each one opens a flow where you set options step by step. It is not as nice as a web dashboard but it works for quick changes without leaving Discord.</p>
            <p>The most annoying part of slash commands is the registration delay. When you update a command definition, it can take up to an hour for Discord to propagate the change globally. During development, I used guild-specific commands which update instantly, but for production you want global commands so you do not have to register them on every server individually.</p>
        """
    },
    {
        "slug": "server-builder-feature",
        "title": "The Server Builder: Automated Server Setup",
        "date": "December 18, 2025",
        "date_short": "Dec 18, 2025",
        "tag": "feature",
        "tag_label": "Feature",
        "summary": "The guided server setup flow that creates channels, roles, and categories based on templates. Why I built it and what it does.",
        "content": """
            <p>Setting up a Discord server from scratch is tedious. You create a bunch of channels, set up categories, make roles, configure permissions for each channel and role combination, and by the end you have spent an hour clicking through menus. I wanted the bot to handle that.</p>
            <p>The server builder is a guided process. When you add the bot to a new server and run /setup, it asks what kind of server you are building: gaming community, content creator, study group, or general. Based on your choice, it creates a channel structure with categories, text channels, and voice channels that make sense for that type of community.</p>
            <p>For a gaming community, you get categories like General, Gaming, Voice Channels, and Moderation, with channels like #general, #off-topic, #looking-for-group, #clips, a few voice channels, and a #mod-log channel. For a content creator server, the layout is different: there is a #announcements channel, #content-links, #fan-art, and so on.</p>
            <p>Roles are created with sensible permission sets. Every template includes Admin, Moderator, and Member roles with appropriate permissions. The bot also sets up channel-specific overrides so that, for example, only moderators can post in #announcements but everyone can read it.</p>
            <p>I went back and forth on whether to let people customize the templates before applying them or just apply a preset and let them modify afterward. I went with the second approach because it is simpler and faster. Most people tweak a few things after setup rather than wanting to configure every detail upfront.</p>
            <p>The biggest challenge was handling servers that already have existing channels and roles. The builder checks for name conflicts and skips anything that already exists, but it can still create a mess if someone runs it on a server that is already set up. I added a confirmation step that shows exactly what will be created before doing anything.</p>
        """
    },
    {
        "slug": "choosing-discordpy",
        "title": "Why discord.py and How the Bot is Structured",
        "date": "December 1, 2025",
        "date_short": "Dec 1, 2025",
        "tag": "devlog",
        "tag_label": "Dev Log",
        "summary": "Picking a Discord library, setting up the cog architecture, and figuring out how to structure a bot that will grow over time.",
        "content": """
            <p>There are a few Python libraries for building Discord bots. The main ones are discord.py, nextcord, disnake, and py-cord. They are all forks or derivatives of the original discord.py, which went through a period of being unmaintained but came back. I went with discord.py because it has the largest community, the most documentation, and it is actively maintained again.</p>
            <p>For the bot architecture, I used the cog system that discord.py provides. Cogs are basically modules: each one handles a specific area of functionality. I have a moderation cog, a logging cog, a server setup cog, an info cog, and a notifications cog. Each cog is its own file with its own commands and event listeners, and they all get loaded when the bot starts up.</p>
            <p>This structure means I can work on moderation features without touching the logging code, or add a new cog for a completely new feature without changing anything else. It also makes debugging easier because when something breaks, I usually know which cog is responsible just from the error message.</p>
            <p>The bot connects to the same Postgres database as the web dashboard. I use SQLAlchemy for the web side but raw asyncpg queries on the bot side because discord.py is async and SQLAlchemy's async support was more trouble than it was worth for my use case. This means I have two different database access patterns in the same project, which is not ideal, but both work reliably.</p>
            <p>Config management was something I over-thought. I ended up with a simple config.py that reads from environment variables and provides defaults. Nothing fancy, but it means I can run the bot locally with a .env file or in production with real environment variables without changing code.</p>
        """
    },
    {
        "slug": "discord-bot-concept",
        "title": "Starting a Discord Bot Project",
        "date": "November 12, 2025",
        "date_short": "Nov 12, 2025",
        "tag": "announcement",
        "tag_label": "Announcement",
        "summary": "I have been working on Nexus for YouTube for months. Now I am starting a companion Discord bot. Here is why and what I want it to do.",
        "content": """
            <p>I have been building Nexus, a YouTube streaming tool, since April. During that time, almost every streamer I talked to also had a Discord server. And almost all of them were using three or four different bots to handle things that one well-built bot could cover. That got me thinking about building a Nexus Discord bot.</p>
            <p>The idea is straightforward: a Discord bot that handles server management, moderation, and community features in one package. Not a music bot, not a meme bot, not a general-purpose bot that tries to do everything. A focused tool for running a community server.</p>
            <p>The feature list I am starting with: a guided server setup that creates channels and roles based on templates, auto-moderation with configurable filters, a warning and punishment system, comprehensive logging for server events, welcome messages with auto-role assignment, and a web dashboard for configuration. That is already a lot, but each piece is scoped well enough that I think I can ship something usable in three to four months.</p>
            <p>I am going to build it in Python since the Nexus web backend is already Python and I can share some infrastructure. discord.py seems like the right library choice but I need to evaluate it against the forks before committing.</p>
            <p>The goal is to have a working beta by March 2026. We will see if I can hold to that timeline while also maintaining the main Nexus project. Managing two codebases solo is going to be a challenge but the projects complement each other well enough that it should be worth it.</p>
        """
    },
]
