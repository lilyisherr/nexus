# Nexus Discord Server -- Publishing Guide

## Server Description (copy-paste into Discord Server Settings > Overview)

```
Nexus -- Free YouTube Bot & Analytics Platform (Beta)

Track your YouTube channel growth, get live stream notifications, view real-time analytics, and manage your community with our all-in-one bot and web dashboard.

Website: nexusbeta.vercel.app
```

---

## Bot Description (copy-paste into Discord Developer Portal > General Information > Description)

```
Nexus is a free YouTube analytics and live stream bot for content creators. Track subscribers, views, and channel growth in real time. Get live stream notifications, milestone alerts, and detailed analytics -- all from Discord.

Features:
- Real-time YouTube channel analytics
- Live stream notifications
- Subscriber milestone alerts
- Server verification system
- Moderation tools (warn, kick, ban)
- Self-assign notification and color roles
- Detailed FAQ and rules system
- Web dashboard at nexusbeta.vercel.app

Free during Beta. Invite Nexus to your server today.
```

---

## Community Server Setup (Discord Settings)

Follow these steps in your Discord server settings to enable Community and prepare for Server Discovery / publishing.

### Step 1: Enable Community

1. Go to **Server Settings > Enable Community**
2. Click **Get Started**
3. Agree to the requirements:
   - Must have a verification level (set to at least **Medium**)
   - Must have a rules or guidelines channel
   - Must have a community updates channel
4. Set the following:
   - **Rules or Guidelines Channel**: `#rules`
   - **Community Updates Channel**: `#announcements`
5. Click **Finish Setup**

### Step 2: Configure Safety Setup

1. Go to **Server Settings > Safety Setup**
2. Set **Verification Level** to **Medium** (members must be registered on Discord for at least 5 minutes)
3. Under **Default Notification Settings**, choose **Only @mentions**
4. Enable **Explicit Media Content Filter** for all members

### Step 3: Enable Server Discovery (requires 1,000+ members to appear publicly)

1. Go to **Server Settings > Discovery**
2. If eligible, toggle on **Enable Discovery**
3. Set a **Primary Category** (choose **Science & Tech** or **Entertainment**)
4. Set a **Sub Category** if available
5. Add **Discovery Description** (use the server description above)
6. Set **Server Language** to English

### Step 4: Welcome Screen

1. Go to **Server Settings > Welcome Screen**
2. Enable the welcome screen
3. Add these channels:
   - `#verify` -- "Verify your account to access the server"
   - `#rules` -- "Read the server rules"
   - `#general` -- "Chat with the community"
   - `#pick-your-roles` -- "Choose notification and color roles"
   - `#faq` -- "Frequently asked questions about Nexus"
4. Set the **Server Description** for the welcome screen to:
   ```
   Welcome to Nexus. Verify your account, read the rules, and start chatting.
   ```

### Step 5: Server Template (Optional)

Consider creating a server template under **Server Settings > Server Template** so others can clone the structure.

---

## Invite Link Setup

1. Go to **Discord Developer Portal > OAuth2 > URL Generator**
2. Select scopes: `bot`, `applications.commands`
3. Select permissions:
   - Administrator (simplest, or pick individual permissions below)
   - If not Admin: Manage Roles, Manage Channels, Kick Members, Ban Members, Send Messages, Manage Messages, Embed Links, Attach Files, Read Message History, Add Reactions, Use External Emojis, Manage Nicknames, View Channels
4. Copy the generated URL

---

## Bot Portal Settings (Discord Developer Portal)

### General Information
- **Name**: Nexus Bot
- **Description**: Use the bot description above
- **Tags**: `youtube`, `analytics`, `bot`, `streaming`, `moderation`

### Bot Settings
- **Public Bot**: Enabled (so anyone can invite it)
- **Requires OAuth2 Code Grant**: Disabled
- **Privileged Gateway Intents**: Enable all three:
  - Presence Intent
  - Server Members Intent
  - Message Content Intent

### OAuth2 > Redrects
- Add: `https://nexusbeta.vercel.app/auth/callback`

---

## After Setup Checklist

1. Run `/reset-server` then `/setup-server` in your Discord server to build all channels and roles
2. Verify the welcome screen shows the correct channels
3. Test the verification flow: join on an alt account, see only #verify, click Verify, get access
4. Check #rules, #faq, #pick-your-roles all have their embeds posted
5. Confirm the bot's status is rotating through different activities
6. Test `/help` to make sure all commands show up
7. Invite a friend to test the full join flow end-to-end
