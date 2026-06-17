BLOG_POSTS = [
    {
        "slug": "admin-panel-overhaul",
        "title": "The Admin Panel Finally Does What I Need It To",
        "date": "March 14, 2026",
        "date_short": "Mar 14, 2026",
        "tag": "devlog",
        "tag_label": "Dev Log",
        "summary": "For a while the admin panel was basically useless for actually managing the platform. Here's what it looks like now.",
        "content": """
            <p>The original admin dashboard had a user list, a blog post editor, and a message inbox. That was it. Anything more complex required me to open a database client and query directly, which is fine when you're the only user but gets old fast as the platform grows.</p>
            <p>The channels section is what I needed most. I can now see every connected YouTube channel at a glance — thumbnail, subscriber count, total views, video count, whether the bot is actually active on that channel. Before this, I had no idea which channels had the bot running without running a manual query.</p>
            <p>Each channel has a detail page now. Click in and you see the full picture: owner info, when they signed up, what bot settings they have configured, their recent stream sessions (duration, peak viewers), and a live status check button that hits the YouTube API and tells you if they're currently broadcasting. That last one is useful when someone messages saying the bot isn't working — I can check immediately whether they're even live.</p>
            <p>The overview dashboard got a couple of new stat cards too. "Currently Live" counts how many connected channels are actively streaming right now (pulled from stream sessions). "New Users (7d)" is self-explanatory. And there's a recent streams table showing the last 8 stream sessions across all channels, which gives a good pulse-check on platform activity.</p>
            <p>The navigation also got rebuilt. I'm pretty happy with how it came out — it actually reflects what pages exist now instead of being a leftover from an earlier version of the site. Active pages get underlined. There's a mobile hamburger menu. Admin users get a badge. Small stuff but it adds up.</p>
        """
    },
    {
        "slug": "changelog-page-and-what-it-took",
        "title": "Why I Built a Changelog Page (And What Went Into It)",
        "date": "March 14, 2026",
        "date_short": "Mar 14, 2026",
        "tag": "devlog",
        "tag_label": "Dev Log",
        "summary": "The changelog is live at /changelog. It sounds simple but there were a few decisions that took longer than they should have.",
        "content": """
            <p>I've been meaning to add a changelog page since before launch. The problem with being a solo dev is that "I should add that" stays in your head for weeks while you're busy shipping other things.</p>
            <p>The design I landed on is a vertical timeline — version dots on the left, cards on the right showing what changed. Each entry has a badge (green for features, indigo for improvements, yellow for fixes) and a full bullet list of specific changes instead of just a vague summary sentence. The vague summary approach is what every AI-generated changelog uses and it's useless. "Improved performance and stability" tells you nothing.</p>
            <p>I went back and filled in the history from the beginning — April 2025 when I first started, through the prototype, early stable builds, the analytics rewrite, the moderation system, and up to now. It's a bit humbling seeing how far back some of this stuff goes. April to March is almost a full year.</p>
            <p>One thing I added that I don't see on many changelogs: a Discord copy section at the top. It generates a pre-formatted version of the latest update with Discord markdown (bold text, bullet points) and a copy button. The goal is to make it easy to post update announcements in the Discord server without having to reformat anything. You just hit copy and paste it in a channel.</p>
            <p>That copy button uses the Clipboard API, which works in modern browsers over HTTPS. It falls back gracefully if clipboard access is denied — the text is still there in the preview box and you can select and copy it manually.</p>
            <p>The data lives in its own Python file (changelog_data.py) rather than a database table. For something that changes infrequently and is just a list of dicts, that's simpler than a database migration every time I want to add an entry. No admin UI needed, no ORM models, just edit the file and deploy.</p>
        """
    },
    {
        "slug": "discord-bot-gets-smarter",
        "title": "Discord Bot Gets Smarter",
        "date": "March 9, 2026",
        "date_short": "Mar 9, 2026",
        "tag": "feature",
        "tag_label": "Feature",
        "summary": "New admin commands, a reaction role bug fix, and quality-of-life improvements that make the Nexus Discord bot significantly more capable.",
        "content": """
            <p>The Discord bot just got a big batch of new commands and an important bug fix. If you've been using the reaction role system, this one matters.</p>
            <p>First, the bug fix. When someone removed a reaction and then re-reacted, the bot wasn't always granting the role back. The issue was that Discord's member cache doesn't always have every user available, especially in larger servers. The bot was silently failing when it couldn't find the member in cache. I added a fallback that fetches the member directly from Discord's API when the cache misses. It's slightly slower but it's reliable now.</p>
            <p>On the new commands side, there are eleven additions: /unban, /untimeout, /role (add or remove roles from members), /nick (change nicknames), /lock and /unlock for channels, /poll for creating quick polls with reaction voting, /embed for posting custom embed messages, /avatar to show someone's profile picture, /moveall to move everyone from one voice channel to another, and /banlist to see who's currently banned.</p>
            <p>All of these work through Discord's slash command system with proper permission checks. You can't /ban someone with a higher role than yours, you can't /role yourself into admin, and /lock respects the channel permission hierarchy. The /help command has been updated to list everything.</p>
            <p>These are available in both the standalone bot and the modular cog version, so whether you're self-hosting or using the hosted version, you get the same commands.</p>
        """
    },
    {
        "slug": "seo-and-discovery",
        "title": "SEO and Discovery Improvements",
        "date": "March 7, 2026",
        "date_short": "Mar 7, 2026",
        "tag": "devlog",
        "tag_label": "Dev Log",
        "summary": "Added structured data, proper meta tags, a sitemap, and robots.txt. Making Nexus findable on search engines.",
        "content": """
            <p>SEO is one of those things I kept putting off because it felt less important than shipping features. But if nobody can find Nexus through a search engine, the features don't matter much.</p>
            <p>I spent a few days overhauling the meta tags across the entire site. Every page now has proper Open Graph tags (og:title, og:description, og:image with alt text, og:locale) and Twitter Card tags. The homepage got JSON-LD structured data using the SoftwareApplication schema, which helps Google understand what Nexus actually is instead of just seeing it as a random webpage.</p>
            <p>I also added /robots.txt and /sitemap.xml routes. The sitemap includes all the public pages -- homepage, blog posts, help center, status page -- and excludes everything that requires authentication. The authenticated pages (dashboard, settings, videos, channel pages) are all set to noindex, nofollow so they don't show up in search results.</p>
            <p>The OG image is now the Nexus logo at 1024x1024. I originally had a separate og-image.png but maintaining two images was pointless when the logo works fine for social previews. Cleaned that up.</p>
            <p>Keywords got expanded too. Instead of just "YouTube bot" I added things like "live chat moderation", "stream analytics", "YouTube live tools" and similar long-tail terms that someone might actually search for. Whether this actually moves the needle on traffic remains to be seen, but at least the foundation is there now.</p>
        """
    },
    {
        "slug": "24-features-on-the-roadmap",
        "title": "24 Features on the Roadmap",
        "date": "March 6, 2026",
        "date_short": "Mar 6, 2026",
        "tag": "announcement",
        "tag_label": "Announcement",
        "summary": "The planned features list has grown to 24 items. Here's what's coming and how I'm thinking about priorities.",
        "content": """
            <p>The "Coming Soon" section on the homepage now lists 24 planned features. That's a lot for a solo developer, so let me talk about how I'm thinking about priorities and what's likely to ship first.</p>
            <p>The original list had 16 features. I added eight more based on what people have been asking for: Watch Parties, Stream Notes, Revenue Dashboard, Multi-Language Chat, Content Scheduler, Goal Tracking, Plugin Marketplace, and Webhook Integrations. Some of these are big projects (Plugin Marketplace) and some are relatively straightforward (Stream Notes).</p>
            <p>What's closest to shipping: Loyalty Points is probably 70% done. The backend tracking is in place, I just need to finish the redemption UI and test edge cases. Clip Manager is next -- it's mostly a frontend project since YouTube already has a clips API.</p>
            <p>What's further out: Twitch and Kick integration require significant API work and testing infrastructure I don't have yet. The Plugin Marketplace is a long-term vision that won't happen until the core platform is more stable. Revenue Dashboard needs partnership with payment providers which adds complexity.</p>
            <p>I'm trying to resist the urge to work on the exciting new stuff before polishing what already exists. The moderation system, analytics, and command system all have rough edges that I should smooth out first. But sometimes you need to build something new to stay motivated, so I'll probably alternate between polish and new features.</p>
        """
    },
    {
        "slug": "nexus-beta-is-live",
        "title": "Nexus Beta is Live",
        "date": "March 5, 2026",
        "date_short": "Mar 5, 2026",
        "tag": "announcement",
        "tag_label": "Announcement",
        "summary": "After almost a year of building, Nexus is finally in public beta. Here's what's in the first release and what took so long.",
        "content": """
            <p>It's been about eleven months since I started working on Nexus, and it's finally at a point where other people can use it. That feels weird to type.</p>
            <p>The beta includes the core stuff: a chat bot that runs as nexusbetabot in your YouTube live chat, basic moderation (spam filter, link blocking, caps filter, blocked words), custom commands, timed messages, and channel analytics. You sign in with Google, connect your channel, add nexusbetabot as a moderator, and you're good to go.</p>
            <p>There's a lot I wanted to have ready for launch that didn't make it. Loyalty points, stream overlays, and a proper mobile experience are all things I started but had to cut to actually ship something. They'll come later.</p>
            <p>The biggest challenge was honestly just OAuth. Getting Google's verification process right, making sure tokens refresh properly, handling edge cases where someone revokes access mid-stream -- that stuff ate up way more time than the actual bot logic. I rewrote the auth flow three separate times.</p>
            <p>If you try it out and something breaks, please let me know. That's the whole point of a beta. I'm one person building this so I can't test every scenario, but I can fix things fast when I know about them.</p>
        """
    },
    {
        "slug": "analytics-rebuild",
        "title": "Rebuilding the Analytics from Scratch",
        "date": "February 18, 2026",
        "date_short": "Feb 18, 2026",
        "tag": "devlog",
        "tag_label": "Dev Log",
        "summary": "The original analytics were slow and inaccurate. Here's why I threw them out and started over with Chart.js and a new data pipeline.",
        "content": """
            <p>The first version of analytics in Nexus was bad. Like, actually bad. I was pulling data from the YouTube API every time someone loaded the dashboard, which meant it was slow, ate through API quota, and the numbers would change depending on when you looked at them.</p>
            <p>So I rewrote the whole thing. Now there's a background process that syncs channel data periodically and stores it in Postgres. The dashboard reads from the database instead of hitting the API directly. It's faster, the data is consistent, and I'm not burning through quota anymore.</p>
            <p>For the charts, I switched to Chart.js. I tried D3 first but it was overkill for what I needed -- subscriber trends, view counts over time, that kind of thing. Chart.js handles that well and the bundle size is way smaller.</p>
            <p>The trickiest part was figuring out what data people actually care about. I started with like fifteen different charts and metrics, which was overwhelming. I cut it down to the essentials: subscriber count, total views, video performance, and viewer activity during streams. If people want more granular stuff, I can add it later based on what they ask for.</p>
            <p>One thing I'm still not happy with is how slow the initial sync is for channels with a lot of videos. The YouTube API paginates results and each page costs quota units, so syncing a channel with 500+ videos takes a while. Working on a smarter approach that syncs recent videos first and backfills older ones gradually.</p>
        """
    },
    {
        "slug": "custom-commands-deep-dive",
        "title": "How Custom Commands Actually Work",
        "date": "January 12, 2026",
        "date_short": "Jan 12, 2026",
        "tag": "feature",
        "tag_label": "Feature",
        "summary": "A look at the command system -- how triggers work, variable substitution, cooldowns, and why I didn't just copy Nightbot.",
        "content": """
            <p>Custom commands were one of the first things people asked about when I showed early versions of Nexus. Everyone wants !discord, !socials, !schedule -- the basics. But I wanted the system to be a bit more flexible than that.</p>
            <p>Each command has a trigger (the !word), a response (what the bot says), a cooldown (so people can't spam it), and permission levels (everyone, subscribers only, or moderators only). Nothing revolutionary, but the details matter.</p>
            <p>The response supports variables like {user} for the person who typed the command, {channel} for the channel name, {uptime} for how long the stream has been live, and {count} for how many times the command has been used. So you can make a !hug command that says "{user} just hugged the chat. That's hug #{count}!" which is dumb but people like it.</p>
            <p>Cooldowns are per-command, not global. So !discord can have a 30-second cooldown while !socials has a 60-second one. I considered per-user cooldowns but decided to keep it simple for now. If the same command is triggered within the cooldown window, the bot just ignores it.</p>
            <p>I looked at how Nightbot and Streamlabs handle this and honestly, they do it well. I'm not trying to reinvent the wheel. I just wanted commands to work reliably on YouTube specifically, since both of those tools were built for Twitch first and YouTube support sometimes feels like an afterthought.</p>
        """
    },
    {
        "slug": "moderation-system",
        "title": "Building Chat Moderation That Doesn't Suck",
        "date": "November 8, 2025",
        "date_short": "Nov 8, 2025",
        "tag": "feature",
        "tag_label": "Feature",
        "summary": "Spam filters, link blocking, caps detection, and blocked words. The moderation stack and the edge cases that made it annoying to build.",
        "content": """
            <p>Moderation is one of those things that sounds simple until you try to build it. "Just block spam" -- sure, but what counts as spam?</p>
            <p>The spam filter in Nexus uses a few signals: repeated characters (like "AAAAAAAAA"), repeated words, messages that are mostly symbols, and messages that match patterns commonly used by spam bots. It's all regex-based right now, which means it's fast but not perfect. Some spam gets through, and occasionally a legitimate message gets flagged. I'm tweaking the thresholds as I see real-world usage.</p>
            <p>Link blocking was more straightforward. By default, it blocks any message containing a URL unless the sender is a moderator or subscriber (configurable). The tricky part was detecting URLs that people try to disguise -- things like "dot com" instead of ".com" or using unicode characters that look like periods. I catch the obvious ones but I'm not going to pretend it's bulletproof.</p>
            <p>The caps filter flags messages where more than 70% of the characters are uppercase and the message is longer than 8 characters. So "LOL" is fine but "THIS STREAM IS AWESOME EVERYONE SHOULD WATCH" gets caught. The threshold is configurable.</p>
            <p>Blocked words is a simple list. You add words or phrases, and any message containing them gets deleted. I store the list per-channel so different channels can have different rules. One thing I added that I think is useful: you can add regex patterns to the blocked words list, so you can catch variations of words without listing every possible spelling.</p>
        """
    },
    {
        "slug": "why-i-built-nexus",
        "title": "Why I Started Building This",
        "date": "September 22, 2025",
        "date_short": "Sep 22, 2025",
        "tag": "announcement",
        "tag_label": "Announcement",
        "summary": "The honest backstory. What I was using before, what was missing, and why I decided to build my own thing instead of complaining about it.",
        "content": """
            <p>I was using Nightbot for a while. It works fine for Twitch. On YouTube, it's okay but it always felt like a second-class citizen. The YouTube API has quirks that Nightbot doesn't always handle well -- things like how live chat polling works differently than Twitch's IRC, or how YouTube's rate limits are structured.</p>
            <p>What really bothered me was analytics. YouTube Studio gives you some data, but it's not great for live streaming specifically. I wanted to see things like peak concurrent viewers per stream, chat messages per minute, which commands were used most, and how subscriber count changed during vs. between streams. None of the existing tools gave me that in a clean way.</p>
            <p>So I started building Nexus. The plan was simple: make a chat bot that works well on YouTube, and pair it with analytics that actually show you useful streaming data. No Twitch, no multi-platform stuff -- just do YouTube well.</p>
            <p>That was April 2025. It's taken longer than I expected (everything does), but the core of what I wanted exists now. The bot moderates chat, responds to commands, and the dashboard shows you your numbers. Is it as polished as Nightbot? No. But it does the YouTube-specific stuff better, and I can add features based on what people actually need instead of what a product roadmap says.</p>
        """
    },
    {
        "slug": "first-working-prototype",
        "title": "The First Version That Actually Worked",
        "date": "July 14, 2025",
        "date_short": "Jul 14, 2025",
        "tag": "devlog",
        "tag_label": "Dev Log",
        "summary": "Three months in and the bot finally responds to commands in a real YouTube live chat. It only took rewriting the polling loop four times.",
        "content": """
            <p>Today was a good day. The bot sent its first message in a live YouTube chat. It was a response to !hello and it just said "Hey there!" but honestly it felt like landing on the moon.</p>
            <p>Getting here was painful. YouTube's Live Chat API uses polling -- you have to repeatedly ask "are there new messages?" instead of getting a real-time stream like Twitch's IRC. The polling interval matters a lot: too fast and you eat through your API quota in minutes, too slow and the bot feels laggy.</p>
            <p>I settled on polling every 5 seconds during active streams, which is a decent balance. The bot picks up new messages, checks if any of them are commands, and responds. The response has to go through the API too, so there's inherent latency. It's not instant like Nightbot on Twitch, but it's fast enough that it doesn't feel broken.</p>
            <p>The four rewrites of the polling loop were because I kept running into edge cases. What happens when the stream ends mid-poll? What if the API returns an error? What if someone sends a command while the bot is still processing the previous batch? Each of these broke something and required rethinking how the loop handles state.</p>
            <p>Next up: making the bot actually do useful things beyond saying hello. Moderation filters are first on the list.</p>
        """
    },
    {
        "slug": "choosing-the-stack",
        "title": "Flask, Postgres, and Why I Didn't Use Node",
        "date": "May 3, 2025",
        "date_short": "May 3, 2025",
        "tag": "devlog",
        "tag_label": "Dev Log",
        "summary": "The tech decisions behind Nexus. Why Python over JavaScript, why Flask over Django, and why I'll probably regret not using TypeScript.",
        "content": """
            <p>I went with Python and Flask for Nexus, which might seem like an odd choice for something that needs to handle real-time chat. Most people would reach for Node.js or Go for this kind of thing. Here's my reasoning.</p>
            <p>I know Python well. I've built things with it before and I can move fast in it. For a solo project where shipping matters more than theoretical performance, that counts for a lot. Flask is lightweight and doesn't force you into patterns you might not need. Django has more built-in stuff but it also has more opinions, and I wanted to structure things my own way.</p>
            <p>For the database, I started with SQLite because it's zero-config and fine for development. But I knew I'd need Postgres eventually for concurrent access and better performance with analytics queries. I made the switch around month three and it was mostly painless thanks to SQLAlchemy.</p>
            <p>The frontend is server-rendered HTML with Jinja2 templates. No React, no Vue, no build step. The dashboard has some Chart.js for graphs and a few fetch calls for things like toggling the bot, but 95% of the pages are just HTML that the server renders. This keeps things simple and means the site works fine without JavaScript for most functionality.</p>
            <p>Will I regret not using TypeScript? Probably, once the codebase gets bigger and I start losing track of what data structures look like. But for now, Python with type hints in the important places is working fine.</p>
        """
    },
    {
        "slug": "project-kickoff",
        "title": "Starting Something New",
        "date": "April 11, 2025",
        "date_short": "Apr 11, 2025",
        "tag": "announcement",
        "tag_label": "Announcement",
        "summary": "Day one. Setting up the repo, sketching out what this thing should do, and trying not to scope creep myself into oblivion.",
        "content": """
            <p>I registered the domain, set up the repo, and spent most of today sketching out what Nexus should actually be. The core idea: a YouTube-focused chat bot with built-in analytics. Not a Twitch bot that also supports YouTube. A YouTube bot, period.</p>
            <p>The initial feature list I wrote down was way too long. Loyalty points, custom overlays, song requests, multi-language support, a mobile app -- all things that would be cool but would take years to build as a solo developer. I crossed most of them off and kept the essentials: chat moderation, custom commands, timed messages, and basic channel analytics.</p>
            <p>My goal is to have something usable by the end of the year. Not polished, not feature-complete, just functional enough that a streamer could use it on a real stream and it would work. We'll see if that timeline holds up.</p>
            <p>Tech stack decision is Flask + Postgres + vanilla frontend. I know React would look better on a resume but I don't want to deal with a build pipeline for a project I'm building alone. Keep it simple, ship it, iterate.</p>
        """
    },
    {
        "slug": "bot-identity-fix",
        "title": "Fixing the Bot Identity Problem",
        "date": "February 28, 2026",
        "date_short": "Feb 28, 2026",
        "tag": "devlog",
        "tag_label": "Dev Log",
        "summary": "The bot was posting messages as the user's account instead of as nexusbetabot. Here's what went wrong and how I fixed it.",
        "content": """
            <p>Got a report that really confused me at first: someone said the bot was posting chat messages under their name instead of as nexusbetabot. Turns out this is exactly what was happening, and it's because of how I originally set up the OAuth flow.</p>
            <p>When a user signs in with Google, Nexus gets an access token for their YouTube account. I was using that same token to post bot messages. So when the bot said "Welcome to the stream!" it showed up as the channel owner saying it, not as the bot. Oops.</p>
            <p>The fix was to give nexusbetabot its own separate OAuth tokens. I added BOT_ACCESS_TOKEN and BOT_REFRESH_TOKEN as environment variables, and created a one-time setup route to generate them. Now the bot uses its own credentials to post messages, and falls back to the user's tokens only if the bot tokens aren't configured.</p>
            <p>This is one of those bugs that seems obvious in hindsight but took a while to notice because I was testing with my own account and didn't pay attention to which name appeared on the messages. Lesson learned: test with multiple accounts.</p>
        """
    },
    {
        "slug": "webhook-integrations",
        "title": "Adding Webhook Support",
        "date": "January 25, 2026",
        "date_short": "Jan 25, 2026",
        "tag": "feature",
        "tag_label": "Feature",
        "summary": "You can now send notifications to Discord when you go live or when things happen in chat. Here's how webhooks work in Nexus.",
        "content": """
            <p>Webhooks were one of the most requested features during early testing. People wanted to automatically post in their Discord server when they went live, or get notified when someone used a specific command.</p>
            <p>The implementation is pretty straightforward. You give Nexus a webhook URL (Discord, Slack, or any service that accepts POST requests), choose which events should trigger it, and Nexus sends a JSON payload when those events happen.</p>
            <p>Right now the supported events are: stream started, stream ended, new subscriber, and custom triggers (tied to specific commands). I kept the event list short on purpose -- it's easy to add more later, but hard to remove them once people are using them.</p>
            <p>The biggest challenge was reliability. Webhook endpoints can be slow, down, or rate-limited. I added a simple retry system: if a webhook fails, Nexus retries up to 3 times with exponential backoff. If it still fails, it logs the failure and moves on. I didn't want a broken webhook URL to slow down the bot's main loop.</p>
            <p>Discord webhooks are by far the most popular use case so I added a "Discord" preset that formats the payload as a Discord embed with the stream title, thumbnail, and a link. Makes it look nice in a server without any extra configuration.</p>
        """
    },
    {
        "slug": "youtube-quota-nightmares",
        "title": "YouTube API Quota is a Nightmare",
        "date": "August 19, 2025",
        "date_short": "Aug 19, 2025",
        "tag": "devlog",
        "tag_label": "Dev Log",
        "summary": "I burned through my entire daily API quota in 3 hours. Here's what I learned about YouTube's rate limits the hard way.",
        "content": """
            <p>YouTube gives you 10,000 quota units per day by default. That sounds like a lot until you realize that a single search request costs 100 units, listing videos costs 1 unit per page, and inserting a chat message costs 50 units. If you have a bot that's actively moderating a busy chat, you can blow through your daily quota before lunch.</p>
            <p>This happened to me during testing. I had the polling interval set to 2 seconds (way too fast) and the bot was checking for new messages, fetching user details for each message, and responding to commands. With a test chat that had moderate activity, I hit the quota limit in about 3 hours. The bot just stopped working mid-stream with a 403 error.</p>
            <p>The fix was a combination of things. First, I increased the polling interval to 5 seconds. Second, I started caching user details so I'm not re-fetching them every time someone sends a message. Third, I batch operations where possible -- instead of deleting spam messages one at a time, I queue them and delete in batches.</p>
            <p>I also applied for a quota increase through Google Cloud Console. The default 10,000 is really only suitable for testing. For a real application serving multiple users, you need more. Google approved an increase after a few days of review, but the process was annoying and poorly documented.</p>
            <p>The lesson here is to treat quota like money. Every API call has a cost, and you need to budget carefully. I now have a quota tracker in the dashboard that shows how many units have been used today, which helps me and users understand the limits.</p>
        """
    },
    {
        "slug": "oauth-verification-saga",
        "title": "The OAuth Verification Process is Wild",
        "date": "October 15, 2025",
        "date_short": "Oct 15, 2025",
        "tag": "devlog",
        "tag_label": "Dev Log",
        "summary": "Trying to get Google to verify the OAuth consent screen. Rejected twice, approved on the third try. Here's what they want.",
        "content": """
            <p>If your app uses Google OAuth and accesses sensitive scopes (which anything YouTube-related does), you need to go through Google's verification process. This means submitting your app for review, providing a privacy policy and terms of service, demonstrating that you actually need the scopes you're requesting, and sometimes recording a video walkthrough of your app.</p>
            <p>My first submission was rejected because my privacy policy wasn't specific enough about what YouTube data I access. Fair enough. My second submission was rejected because I was requesting the youtube.force-ssl scope but Google wanted me to explain why the regular youtube scope wasn't sufficient. The answer is that you need force-ssl to post messages via the Live Chat API, but apparently that wasn't obvious to the reviewer.</p>
            <p>Third time was the charm. I rewrote the privacy policy to explicitly list every piece of data Nexus reads and writes, added a detailed scope justification document, and recorded a 5-minute video showing the app in action. Approved in about a week.</p>
            <p>Until verification is complete, only "test users" you manually add in the Google Cloud Console can use your app. This caps out at 100 users, which is fine for a beta but would be a problem at scale. Getting verified removes that limit.</p>
            <p>The whole process took about a month from first submission to approval. If you're building something that uses Google APIs, start the verification process early. Don't wait until you're ready to launch.</p>
        """
    },
    {
        "slug": "timed-messages-and-welcome",
        "title": "Timed Messages and Welcome Greetings",
        "date": "December 5, 2025",
        "date_short": "Dec 5, 2025",
        "tag": "feature",
        "tag_label": "Feature",
        "summary": "Two small features that streamers kept asking for: automatic timed messages and greeting new viewers when they first chat.",
        "content": """
            <p>Timed messages are exactly what they sound like. You write a message, set an interval (say, every 15 minutes), and the bot posts it in chat automatically. Most streamers use this for things like "Follow the channel!" or "Join the Discord: discord.gg/whatever" -- stuff they'd say manually anyway but keep forgetting to.</p>
            <p>The implementation has a few guardrails. There's a minimum interval of 5 minutes so the bot doesn't flood chat. You can set a "minimum chat messages" threshold -- the timer only fires if there have been at least X messages since the last one, so the bot doesn't talk to an empty room. And you can have multiple timers running at different intervals.</p>
            <p>Welcome messages greet new viewers the first time they send a message in chat. Not every stream, just literally the first time they've ever chatted on your channel. Nexus tracks who's chatted before and only triggers the welcome for genuinely new people.</p>
            <p>I was on the fence about this feature because welcome bots can be annoying. But enough people asked for it that I added it with some sensible defaults: there's a cooldown so the bot doesn't fire twenty welcome messages in a row if a bunch of new people show up at once, and the message is customizable so you can make it feel natural instead of robotic.</p>
            <p>Both features can be toggled on and off independently per channel, which is important if you run multiple channels with different vibes.</p>
        """
    },
    {
        "slug": "video-cards-redesign",
        "title": "Redesigning Video Cards to Match YouTube",
        "date": "March 12, 2026",
        "date_short": "Mar 12, 2026",
        "tag": "feature",
        "tag_label": "Feature",
        "summary": "I spent way too much time getting video cards to look right. Here's what I changed and why the details matter.",
        "content": """
            <p>The video cards on the dashboard were kind of an afterthought. Just a basic grid with thumbnails and titles. Nothing wrong with it functionally, but it didn't match the rest of Nexus and it definitely didn't look like what people expect from YouTube.</p>
            <p>So I redesigned them to match YouTube's actual card layout. 16:9 thumbnails, channel avatar in the bottom left, title below the card, view count and upload timestamp in that "1.2K views * 3 days ago" format. The spacing is tighter, the fonts are smaller, the whole thing feels more like browsing YouTube than browsing a dashboard.</p>
            <p>The trickiest part was getting the timestamp format right. "3 days ago" sounds simple but the logic is annoying: is it "1 minute ago" or "1 hour ago" or "1 day ago" or "3 weeks ago"? I ended up writing a utility function that converts timedeltas into human-readable strings with the right boundaries.</p>
            <p>View counts also needed special formatting. 1000 becomes "1K", 1200000 becomes "1.2M". The logic has to handle edge cases like 999 (still shows as "999" not "1K"). Again, more annoying than it should be but it's the kind of detail that makes the interface feel polished.</p>
            <p>The cards now have a subtle hover effect that darkens the thumbnail slightly and makes the title stand out. Nothing fancy, just enough to feel interactive without being distracting.</p>
        """
    },
    {
        "slug": "discord-integration",
        "title": "Adding Discord Integration",
        "date": "March 18, 2026",
        "date_short": "Mar 18, 2026",
        "tag": "feature",
        "tag_label": "Feature",
        "summary": "You can now send live notifications to Discord when you go live or when certain events happen. No OAuth, just paste a webhook URL.",
        "content": """
            <p>One of the most common requests I got after launch was "can Nexus post to Discord when I go live?" Most streamers have a Discord community and they want to let their members know when streams are happening. Before, they had to either use a separate service or manually post in Discord.</p>
            <p>The implementation is straightforward. In the bot settings, there's a new Discord section where you paste your Discord webhook URL. That's it. Nexus detects when you go live and sends a message to that Discord channel automatically.</p>
            <p>The tricky part was making the Discord message look good. A raw JSON payload would be ugly. So I format it as a Discord embed with the stream title, your channel avatar as the thumbnail, view count, and a direct link to the stream. It looks polished and clickable without any extra setup from the user.</p>
            <p>The webhooks work even if Nexus is down (as long as the bot detected that you went live before it crashed). I store the channel status and check it periodically, so if Nexus restarts, it knows whether you're live and can resend the Discord notification if needed.</p>
            <p>I didn't go with full OAuth integration because that would require me to request additional Discord permissions and go through their verification process. Webhooks are simpler, more secure (the user controls what Nexus can post to), and easier to set up. You just copy a URL.</p>
        """
    },
    {
        "slug": "nightbot-import",
        "title": "Import Commands from Nightbot",
        "date": "March 24, 2026",
        "date_short": "Mar 24, 2026",
        "tag": "feature",
        "tag_label": "Feature",
        "summary": "Migrating from Nightbot? You can now import all your commands at once instead of recreating them manually.",
        "content": """
            <p>A few users switched to Nexus from Nightbot and immediately asked if there was a way to import their existing commands. They had dozens of them and didn't want to recreate everything from scratch. Fair point.</p>
            <p>I built a simple import feature. You go to the bot settings, click "Import from Nightbot," paste your command list (you can export it from Nightbot's dashboard as a JSON list), and Nexus parses it and creates all the commands in your channel.</p>
            <p>The Nightbot format has most of the same fields as Nexus: trigger, response, cooldown, permissions. The mapping is pretty direct. The only things that don't transfer cleanly are Nightbot-specific variables like $(twitch) substitution -- those need to be remapped to Nexus equivalents or removed. The importer handles the common cases and alerts you if it skips anything.</p>
            <p>One thing I added that Nightbot doesn't have: bulk actions. Once commands are imported, you can select multiple commands and edit them together or delete them in bulk. This is useful if you realize you need to update all your commands with a new Discord link or something.</p>
            <p>The import process is intentionally not automatic. Nexus doesn't connect to your Nightbot account directly (no need to share credentials). You export, you paste, Nexus imports. More steps, but more secure and more transparent about what's happening.</p>
        """
    },
    {
        "slug": "performance-optimization",
        "title": "Making the Bot 10x Faster",
        "date": "April 2, 2026",
        "date_short": "Apr 2, 2026",
        "tag": "devlog",
        "tag_label": "Dev Log",
        "summary": "The bot was getting slow with lots of users. Here's how I profiled it, found the bottlenecks, and made it snappy again.",
        "content": """
            <p>As more people started using Nexus, I started getting complaints that the bot felt sluggish. Responses to commands were delayed, the dashboard was slow to load, analytics updates weren't keeping up. Time to profile and optimize.</p>
            <p>I used Python's cProfile to identify where the CPU was actually spending time. Turns out the bot was making way too many YouTube API calls for stuff it should have been caching. Every time someone viewed the dashboard, it would fetch the channel info from YouTube instead of using a cached version. Every message the bot processed would fetch subscriber details to check permissions. Obvious in hindsight, stupid not to have cached from the start.</p>
            <p>So I added caching. Channel info gets cached for 5 minutes. User permission levels get cached for 30 seconds. Message data gets cached until the stream ends. This cut API usage in half and made everything feel instant.</p>
            <p>The database queries were also slow because I wasn't indexing properly. The commands table had millions of rows across all users and queries were doing full table scans. Added indexes on user_id, channel_id, and created_at. Query times went from 2-3 seconds to 50-100ms.</p>
            <p>I also optimized the polling loop. Instead of checking for new messages every 5 seconds, I'm now smarter about it. If there haven't been recent messages, I back off to 10 second intervals. If chat is active, I tighten it to 3 seconds. This keeps the bot responsive when people are chatting without burning API quota when chat is quiet.</p>
            <p>The whole optimization took about a week and the improvements are huge. Dashboard load time went from 3-4 seconds to 500ms. Bot response latency is imperceptible now. It's the kind of work that doesn't add features but makes the whole experience better.</p>
        """
    },
    {
        "slug": "spam-detection-improvements",
        "title": "Smarter Spam Detection",
        "date": "April 10, 2026",
        "date_short": "Apr 10, 2026",
        "tag": "devlog",
        "tag_label": "Dev Log",
        "summary": "The spam filter kept missing obvious spam and flagging legitimate messages. I rewrote it with better heuristics.",
        "content": """
            <p>Spam detection is hard. The original system had a bunch of regex patterns that worked okay but missed a lot of edge cases. People would use leetspeak or unicode characters to get around filters. Or they'd space out the characters: "A P O L O 2000" to dodge the repeated character detection.</p>
            <p>I rewrote it with better logic. Now it checks for patterns that are genuinely suspicious: repetitive content across multiple messages from the same user in a short time, messages that are 90% URLs, obvious promotional phrases that show up in spam (things like "check my channel" or "follow for follow"). It's less about rigid rules and more about spotting patterns that only spammers follow.</p>
            <p>The biggest improvement was adding user context. If someone has been chatting normally for weeks and then posts something that might be borderline spam, it's probably fine. If someone joins the stream and immediately posts the same promotional message three times, it's definitely spam. Context matters.</p>
            <p>I also added a way for users to report false positives and help train the filter. If a message was wrongly flagged, the channel owner can mark it as "not spam" and Nexus learns from it. This is way better than me guessing at heuristics.</p>
            <p>The result is way fewer false positives (legitimate messages getting deleted) while still catching real spam. It's never going to be perfect, but it's good enough that channel owners aren't spending half their stream un-deleting legitimate chat.</p>
        """
    },
    {
        "slug": "dashboard-stats-overhaul",
        "title": "Rebuilding the Dashboard Stats Section",
        "date": "April 18, 2026",
        "date_short": "Apr 18, 2026",
        "tag": "devlog",
        "tag_label": "Dev Log",
        "summary": "The dashboard stats were confusing and hard to scan. I simplified them and focused on what actually matters.",
        "content": """
            <p>The first version of the dashboard had way too many stats. Total views, average views per video, subscriber growth rate, engagement ratio, peak concurrent viewers, average session length -- on and on. Most users just looked at the big subscriber count and moved on.</p>
            <p>I did some user testing (chatting with streamers in Discord) and realized people care about three things: how many subscribers they have, how many views they've gotten, and how many views their most recent stream got. Everything else is noise.</p>
            <p>So I redesigned it. The main section now has three big numbers: total subscribers, total views (all-time), and last stream viewer peak. Below that is a simple chart showing subscriber growth over the past 30 days. That's it. Simple, scannable, actually useful.</p>
            <p>I moved the detailed analytics into a separate "Analytics" page for people who want to dig deeper. That page has all the granular data: views per video, upload dates, engagement trends, all of it. But the dashboard isn't cluttered anymore.</p>
            <p>The design is also better. Bigger fonts, more whitespace, better color contrast. The kind of thing that seems obvious once it's done but I probably wouldn't have noticed without user feedback. Building for yourself and building for other people are two very different things.</p>
        """
    },
    {
        "slug": "monitoring-and-alerting",
        "title": "Actually Monitoring What's Happening",
        "date": "April 25, 2026",
        "date_short": "Apr 25, 2026",
        "tag": "devlog",
        "tag_label": "Dev Log",
        "summary": "I had no idea when the bot crashed or when something went wrong. Now I do. Here's the monitoring setup.",
        "content": """
            <p>For a long time, I just... didn't know when stuff broke. If the bot crashed mid-stream, I'd only find out when someone mentioned it in Discord or left a bad review. The API quota warnings were silent. Database issues were silent. It was a mess.</p>
            <p>I set up proper monitoring. Sentry for error tracking, so I instantly see when the bot crashes and can see the full stack trace. Datadog for application metrics so I can watch CPU, memory, request latency, API quota usage in real-time. And simple email alerts for critical issues.</p>
            <p>The key insight is that I need to know about problems before my users do. If the bot stops responding to commands, I want to know that within seconds, not hours. If the YouTube API is slow, I want to see it. If someone's quota is about to run out, I want to alert them proactively.</p>
            <p>Setting this up probably saved me hours of debugging and a lot of frustrated users. The tools cost money but they're worth it for operational peace of mind. You can't run a production service without visibility into what's happening.</p>
        """
    },
]
