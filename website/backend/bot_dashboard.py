from flask import Blueprint, render_template, request, redirect, session, url_for, jsonify, abort
from urllib.parse import urlencode
import os
import secrets
import requests
import time
from datetime import datetime
from functools import wraps
from changelog_data import changelog_data

bot_bp = Blueprint('bot_dashboard', __name__, url_prefix='/bot')

DISCORD_CLIENT_ID = os.getenv('DISCORD_CLIENT_ID', '')
DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET', '')
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN', '')
IS_VERCEL = bool(os.getenv('VERCEL'))


def _bot_redirect_uri():
    if IS_VERCEL:
        return 'https://nexusbeta.vercel.app/bot/callback'
    return request.host_url.rstrip('/') + '/bot/callback'


def bot_login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'bot_user_id' not in session:
            return redirect('/bot/login')
        return f(*args, **kwargs)
    return decorated


def bot_admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        from app import BotUser, User
        nexus_uid = session.get('user_id')
        if nexus_uid:
            nexus_user = User.query.get(nexus_uid)
            if nexus_user and nexus_user.is_admin:
                return f(*args, **kwargs)
        if 'bot_user_id' not in session:
            return redirect('/bot/login')
        bot_user = BotUser.query.get(session['bot_user_id'])
        if not bot_user:
            session.pop('bot_user_id', None)
            return redirect('/bot/login')
        is_nexus_admin = False
        if bot_user.nexus_user_id:
            linked = User.query.get(bot_user.nexus_user_id)
            if linked and linked.is_admin:
                is_nexus_admin = True
        if not is_nexus_admin:
            by_discord = User.query.filter_by(discord_user_id=bot_user.discord_id).first()
            if by_discord and by_discord.is_admin:
                is_nexus_admin = True
                if not bot_user.nexus_user_id:
                    bot_user.nexus_user_id = by_discord.id
                    try:
                        from app import db
                        db.session.commit()
                    except Exception:
                        pass
        if not is_nexus_admin:
            from flask import render_template as _rt
            return _rt('bot/access_denied.html'), 403
        return f(*args, **kwargs)
    return decorated


@bot_bp.context_processor
def inject_bot_user():
    from app import BotUser
    bot_user = None
    if session.get('bot_user_id'):
        bot_user = BotUser.query.get(session['bot_user_id'])
    return dict(bot_session_user=bot_user)


@bot_bp.route('/')
def landing():
    return render_template('bot/landing.html')


@bot_bp.route('/login')
def login():
    if 'bot_user_id' in session:
        return redirect('/bot/dashboard')
    if not DISCORD_CLIENT_ID:
        return render_template('bot/login.html', error='Discord integration is not configured yet.')
    state = secrets.token_hex(16)
    session['bot_oauth_state'] = state
    params = {
        'client_id': DISCORD_CLIENT_ID,
        'redirect_uri': _bot_redirect_uri(),
        'response_type': 'code',
        'scope': 'identify guilds',
        'state': state,
    }
    return redirect(f'https://discord.com/api/oauth2/authorize?{urlencode(params)}')


@bot_bp.route('/callback')
def callback():
    from app import db, BotUser
    error = request.args.get('error')
    if error:
        return redirect('/bot/login?error=denied')
    code = request.args.get('code')
    state = request.args.get('state')
    if not code or state != session.pop('bot_oauth_state', None):
        return redirect('/bot/login?error=invalid')
    try:
        token_resp = requests.post('https://discord.com/api/oauth2/token', data={
            'client_id': DISCORD_CLIENT_ID,
            'client_secret': DISCORD_CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': _bot_redirect_uri(),
        }, headers={'Content-Type': 'application/x-www-form-urlencoded'}, timeout=10)
        if token_resp.status_code != 200:
            return redirect('/bot/login?error=token_failed')
        token_data = token_resp.json()
        access_token = token_data.get('access_token')
        refresh_token = token_data.get('refresh_token', '')

        user_resp = requests.get('https://discord.com/api/users/@me', headers={
            'Authorization': f'Bearer {access_token}',
        }, timeout=10)
        if user_resp.status_code != 200:
            return redirect('/bot/login?error=user_failed')
        discord_user = user_resp.json()
        discord_id = discord_user['id']

        bot_user = BotUser.query.filter_by(discord_id=discord_id).first()
        if not bot_user:
            bot_user = BotUser(discord_id=discord_id)
            db.session.add(bot_user)

        bot_user.discord_username = discord_user.get('username', '')
        bot_user.discord_global_name = discord_user.get('global_name', '')
        bot_user.discord_avatar = discord_user.get('avatar', '')
        bot_user.discord_access_token = access_token
        bot_user.discord_refresh_token = refresh_token
        bot_user.updated_at = datetime.utcnow()
        db.session.commit()

        session['bot_user_id'] = bot_user.id
        session['bot_discord_token'] = access_token
        return redirect('/bot/dashboard')
    except Exception as e:
        print(f"Bot OAuth Error: {e}")
        return redirect('/bot/login?error=login_failed')


@bot_bp.route('/logout')
def logout():
    session.pop('bot_user_id', None)
    session.pop('bot_discord_token', None)
    return redirect('/bot/')


@bot_bp.route('/dashboard')
@bot_admin_required
def dashboard():
    from app import BotUser, ServerConfig
    bot_user = BotUser.query.get(session['bot_user_id'])
    if not bot_user:
        session.pop('bot_user_id', None)
        return redirect('/bot/login')

    user_guilds = []
    try:
        guilds_resp = requests.get('https://discord.com/api/users/@me/guilds', headers={
            'Authorization': f'Bearer {bot_user.discord_access_token}',
        }, timeout=10)
        if guilds_resp.status_code == 200:
            all_guilds = guilds_resp.json()
            for g in all_guilds:
                perms = int(g.get('permissions', 0))
                is_admin = (perms & 0x8) == 0x8
                is_manage = (perms & 0x20) == 0x20
                if g.get('owner') or is_admin or is_manage:
                    icon_url = None
                    if g.get('icon'):
                        icon_url = f"https://cdn.discordapp.com/icons/{g['id']}/{g['icon']}.png?size=128"
                    try:
                        config = ServerConfig.query.filter_by(server_id=g['id'], bot_user_id=bot_user.id).first()
                    except Exception:
                        from app import db as _db
                        _db.session.rollback()
                        config = None
                    user_guilds.append({
                        'id': g['id'],
                        'name': g['name'],
                        'icon': icon_url,
                        'owner': g.get('owner', False),
                        'configured': config is not None,
                    })
    except Exception as e:
        print(f"Failed to fetch guilds: {e}")

    bot_online = False
    bot_avatar_url = None
    bot_username = None
    bot_token = os.getenv('DISCORD_BOT_TOKEN')
    if bot_token:
        try:
            bot_me_resp = requests.get('https://discord.com/api/v10/users/@me', headers={
                'Authorization': f'Bot {bot_token}',
            }, timeout=5)
            if bot_me_resp.status_code == 200:
                bot_data = bot_me_resp.json()
                bot_online = True
                bot_username = bot_data.get('username', '')
                bot_av = bot_data.get('avatar')
                bot_id = bot_data.get('id')
                if bot_av and bot_id:
                    bot_avatar_url = f'https://cdn.discordapp.com/avatars/{bot_id}/{bot_av}.png?size=128'
        except Exception:
            pass

    hosting_connected = False
    hosting_info = {}
    try:
        from app import BotHeartbeat
        hb = BotHeartbeat.query.order_by(BotHeartbeat.last_heartbeat.desc()).first()
        if hb and hb.last_heartbeat:
            age = (datetime.utcnow() - hb.last_heartbeat).total_seconds()
            if age < 300:
                hosting_connected = True
                hosting_info = {
                    'guild_count': hb.guild_count or 0,
                    'user_count': hb.user_count or 0,
                    'latency_ms': hb.latency_ms or 0,
                    'uptime_seconds': hb.uptime_seconds or 0,
                }
    except Exception:
        pass

    bot_in_guilds = set()
    if bot_token:
        try:
            bot_guilds_resp = requests.get('https://discord.com/api/v10/users/@me/guilds', headers={
                'Authorization': f'Bot {bot_token}',
            }, timeout=10)
            if bot_guilds_resp.status_code == 200:
                for bg in bot_guilds_resp.json():
                    bot_in_guilds.add(bg['id'])
        except Exception:
            pass

    for server in user_guilds:
        server['bot_in_server'] = server['id'] in bot_in_guilds

    yt_live_status = []
    if bot_user.nexus_user_id:
        try:
            from app import Channel, bot_manager
            yt_channels = Channel.query.filter_by(user_id=bot_user.nexus_user_id).all()
            for ch in yt_channels:
                s = bot_manager.get_status(ch.id)
                yt_live_status.append({
                    'channel_name': ch.channel_name,
                    'channel_id': ch.id,
                    'thumbnail': ch.channel_thumbnail,
                    'is_live': s.get('is_live', False),
                    'stream_title': s.get('stream_title'),
                    'running': s.get('running', False),
                    'messages_processed': s.get('messages_processed', 0),
                })
        except Exception:
            pass

    return render_template('bot/dashboard.html', servers=user_guilds, bot_user=bot_user,
                           bot_online=bot_online, bot_avatar_url=bot_avatar_url, bot_username=bot_username,
                           hosting_connected=hosting_connected, hosting_info=hosting_info,
                           discord_client_id=DISCORD_CLIENT_ID, yt_live_status=yt_live_status)


@bot_bp.route('/server/<guild_id>')
@bot_admin_required
def server_settings(guild_id):
    from app import db, BotUser, ServerConfig, Channel
    bot_user = BotUser.query.get(session['bot_user_id'])
    if not bot_user:
        return redirect('/bot/login')

    config = ServerConfig.query.filter_by(server_id=guild_id, bot_user_id=bot_user.id).first()

    guild_info = None
    try:
        guilds_resp = requests.get('https://discord.com/api/users/@me/guilds', headers={
            'Authorization': f'Bearer {bot_user.discord_access_token}',
        }, timeout=10)
        if guilds_resp.status_code == 200:
            for g in guilds_resp.json():
                if g['id'] == guild_id:
                    perms = int(g.get('permissions', 0))
                    is_admin = (perms & 0x8) == 0x8
                    is_manage = (perms & 0x20) == 0x20
                    if g.get('owner') or is_admin or is_manage:
                        icon_url = None
                        if g.get('icon'):
                            icon_url = f"https://cdn.discordapp.com/icons/{g['id']}/{g['icon']}.png?size=128"
                        guild_info = {'id': g['id'], 'name': g['name'], 'icon': icon_url}
                    break
    except Exception:
        pass

    if not guild_info:
        return redirect('/bot/dashboard?error=no_permission')

    if not config:
        config = ServerConfig(server_id=guild_id, bot_user_id=bot_user.id, server_name=guild_info['name'], server_icon=guild_info.get('icon'))
        db.session.add(config)
        db.session.commit()
    elif guild_info:
        config.server_name = guild_info['name']
        config.server_icon = guild_info.get('icon')
        db.session.commit()

    text_channels = []
    voice_channels = []
    category_channels = []
    guild_roles = []
    bot_token = os.getenv('DISCORD_BOT_TOKEN')
    if bot_token:
        try:
            ch_resp = requests.get(f'https://discord.com/api/v10/guilds/{guild_id}/channels', headers={
                'Authorization': f'Bot {bot_token}',
            }, timeout=10)
            if ch_resp.status_code == 200:
                for ch in ch_resp.json():
                    if ch.get('type') == 0:
                        text_channels.append({'id': ch['id'], 'name': ch['name']})
                    elif ch.get('type') == 2:
                        voice_channels.append({'id': ch['id'], 'name': ch['name']})
                    elif ch.get('type') == 4:
                        category_channels.append({'id': ch['id'], 'name': ch['name']})
                text_channels.sort(key=lambda c: c['name'])
                voice_channels.sort(key=lambda c: c['name'])
                category_channels.sort(key=lambda c: c['name'])
        except Exception:
            pass

        try:
            roles_resp = requests.get(f'https://discord.com/api/v10/guilds/{guild_id}/roles', headers={
                'Authorization': f'Bot {bot_token}',
            }, timeout=10)
            if roles_resp.status_code == 200:
                for role in roles_resp.json():
                    if role.get('name') != '@everyone':
                        color_hex = '#{:06x}'.format(role.get('color', 0)) if role.get('color', 0) != 0 else '#94a3b8'
                        guild_roles.append({
                            'id': role['id'],
                            'name': role['name'],
                            'color': color_hex,
                            'position': role.get('position', 0),
                            'managed': role.get('managed', False),
                            'mentionable': role.get('mentionable', False),
                            'hoist': role.get('hoist', False),
                            'members': role.get('member_count', 0),
                        })
                guild_roles.sort(key=lambda r: r['position'], reverse=True)
        except Exception:
            pass

    if config and (text_channels or category_channels):
        text_channel_map = {
            'announcements': 'announcement_channel_id',
            'announcement': 'announcement_channel_id',
            'mod-logs': 'mod_log_channel_id',
            'mod-log': 'mod_log_channel_id',
            'mod_log': 'mod_log_channel_id',
            'modlog': 'mod_log_channel_id',
            'modlogs': 'mod_log_channel_id',
            'moderator-logs': 'mod_log_channel_id',
            'welcome': 'welcome_channel_id',
            'welcomes': 'welcome_channel_id',
            'welcome-chat': 'welcome_channel_id',
            'audit-log': 'audit_log_channel_id',
            'audit-logs': 'audit_log_channel_id',
            'audit_log': 'audit_log_channel_id',
            'auditlog': 'audit_log_channel_id',
            'counting': 'counting_channel_id',
            'count': 'counting_channel_id',
            'suggestions': 'suggestion_channel_id',
            'suggestion': 'suggestion_channel_id',
            'suggest': 'suggestion_channel_id',
            'starboard': 'starboard_channel_id',
            'starred': 'starboard_channel_id',
            'media-only': 'media_only_channel_id',
            'media': 'media_only_channel_id',
            'photos': 'media_only_channel_id',
            'verify': 'verify_channel_id',
            'verification': 'verify_channel_id',
            'verified': 'verify_channel_id',
            'level-announce': 'level_announce_channel_id',
            'level-ups': 'level_announce_channel_id',
            'levels': 'level_announce_channel_id',
            'levelup': 'level_announce_channel_id',
            'youtube': 'youtube_notify_channel_id',
            'youtube-notifications': 'youtube_notify_channel_id',
            'streams': 'youtube_notify_channel_id',
            'stream-notifications': 'youtube_notify_channel_id',
            'going-live': 'youtube_notify_channel_id',
            'goodbye': 'goodbye_channel_id',
            'goodbyes': 'goodbye_channel_id',
            'farewell': 'goodbye_channel_id',
            'farewells': 'goodbye_channel_id',
        }
        category_map = {
            'tickets': 'ticket_category_id',
            'ticket': 'ticket_category_id',
            'support': 'ticket_category_id',
        }
        changed = False
        for ch in text_channels:
            ch_name_lower = ch['name'].lower()
            if ch_name_lower in text_channel_map:
                attr = text_channel_map[ch_name_lower]
                if hasattr(config, attr) and not getattr(config, attr):
                    setattr(config, attr, ch['id'])
                    changed = True
        for ch in category_channels:
            ch_name_lower = ch['name'].lower()
            if ch_name_lower in category_map:
                attr = category_map[ch_name_lower]
                if hasattr(config, attr) and not getattr(config, attr):
                    setattr(config, attr, ch['id'])
                    changed = True
        if changed:
            db.session.commit()

    if guild_roles and config:
        role_map = {
            'admin': 'admin_role_id',
            'administrator': 'admin_role_id',
            'admins': 'admin_role_id',
            'moderator': 'mod_role_id',
            'moderators': 'mod_role_id',
            'mod': 'mod_role_id',
            'mods': 'mod_role_id',
            'staff': 'mod_role_id',
            'muted': 'mute_role_id',
            'mute': 'mute_role_id',
            'silenced': 'mute_role_id',
            'verified': 'verify_role_id',
            'member': 'verify_role_id',
            'members': 'verify_role_id',
            'dj': 'dj_role_id',
            'music': 'dj_role_id',
            'auto-role': 'auto_role_id',
            'autorole': 'auto_role_id',
        }
        changed = False
        for role in guild_roles:
            role_name_lower = role['name'].lower()
            if role_name_lower in role_map:
                attr = role_map[role_name_lower]
                if hasattr(config, attr) and not getattr(config, attr):
                    setattr(config, attr, role['id'])
                    changed = True
        if changed:
            db.session.commit()

    nexus_channels = []
    if bot_user.nexus_user_id:
        try:
            from app import bot_manager as _bm
            nexus_chs = Channel.query.filter_by(user_id=bot_user.nexus_user_id).all()
            for nc in nexus_chs:
                s = _bm.get_status(nc.id)
                nexus_channels.append({
                    'id': nc.id,
                    'name': nc.channel_name,
                    'thumbnail': nc.channel_thumbnail,
                    'youtube_id': nc.youtube_channel_id,
                    'is_live': s.get('is_live', False),
                    'stream_title': s.get('stream_title'),
                    'running': s.get('running', False),
                    'messages_processed': s.get('messages_processed', 0),
                })
        except Exception:
            pass

    bot_online = False
    bot_avatar_url = None
    bot_username = None
    if bot_token:
        try:
            bot_me_resp = requests.get('https://discord.com/api/v10/users/@me', headers={
                'Authorization': f'Bot {bot_token}',
            }, timeout=5)
            if bot_me_resp.status_code == 200:
                bot_data = bot_me_resp.json()
                bot_online = True
                bot_username = bot_data.get('username', '')
                bot_av = bot_data.get('avatar')
                bot_id = bot_data.get('id')
                if bot_av and bot_id:
                    bot_avatar_url = f'https://cdn.discordapp.com/avatars/{bot_id}/{bot_av}.png?size=128'
        except Exception:
            pass

    return render_template('bot/server.html', config=config, guild=guild_info,
                           text_channels=text_channels, voice_channels=voice_channels,
                           category_channels=category_channels, guild_roles=guild_roles,
                           nexus_channels=nexus_channels,
                           nexus_linked=bool(bot_user.nexus_user_id), bot_online=bot_online,
                           bot_avatar_url=bot_avatar_url, bot_username=bot_username,
                           changelog_data=changelog_data[:5])


@bot_bp.route('/server/<guild_id>/save', methods=['POST'])
@bot_admin_required
def save_server_settings(guild_id):
    from app import db, BotUser, ServerConfig
    bot_user = BotUser.query.get(session['bot_user_id'])
    if not bot_user:
        return redirect('/bot/login')

    config = ServerConfig.query.filter_by(server_id=guild_id, bot_user_id=bot_user.id).first()
    if not config:
        return redirect('/bot/dashboard?error=server_not_found')

    config.prefix = request.form.get('prefix', '!').strip()[:10] or '!'
    config.bot_nickname = request.form.get('bot_nickname', '').strip()[:255] or None
    config.welcome_enabled = 'welcome_enabled' in request.form
    config.welcome_channel_id = request.form.get('welcome_channel_id', '').strip() or None
    config.welcome_message = request.form.get('welcome_message', 'Welcome to the server, {user}!').strip()
    config.welcome_embed_enabled = 'welcome_embed_enabled' in request.form
    config.welcome_embed_color = request.form.get('welcome_embed_color', '#6366f1').strip()[:7] or '#6366f1'
    config.welcome_embed_title = request.form.get('welcome_embed_title', '').strip()[:256] or None
    config.welcome_embed_thumbnail = request.form.get('welcome_embed_thumbnail', '').strip()[:500] or None
    config.welcome_dm_enabled = 'welcome_dm_enabled' in request.form
    config.welcome_dm_message = request.form.get('welcome_dm_message', '').strip()
    config.goodbye_enabled = 'goodbye_enabled' in request.form
    config.goodbye_channel_id = request.form.get('goodbye_channel_id', '').strip() or None
    config.goodbye_message = request.form.get('goodbye_message', 'Goodbye {user}. Thanks for being here.').strip()
    config.mod_log_enabled = 'mod_log_enabled' in request.form
    config.mod_log_channel_id = request.form.get('mod_log_channel_id', '').strip() or None
    config.log_joins_enabled = 'log_joins_enabled' in request.form
    config.log_leaves_enabled = 'log_leaves_enabled' in request.form
    config.log_message_edits_enabled = 'log_message_edits_enabled' in request.form
    config.log_message_deletes_enabled = 'log_message_deletes_enabled' in request.form
    config.log_bans_enabled = 'log_bans_enabled' in request.form
    config.auto_role_enabled = 'auto_role_enabled' in request.form
    config.auto_role_name = request.form.get('auto_role_name', 'Member').strip()
    config.anti_spam_enabled = 'anti_spam_enabled' in request.form
    config.anti_link_enabled = 'anti_link_enabled' in request.form
    config.anti_caps_enabled = 'anti_caps_enabled' in request.form
    config.anti_emoji_spam_enabled = 'anti_emoji_spam_enabled' in request.form
    config.bad_words_enabled = 'bad_words_enabled' in request.form
    config.bad_words_list = request.form.get('bad_words_list', '').strip()
    try:
        config.max_warnings = max(1, min(int(request.form.get('max_warnings', 3)), 10))
    except (ValueError, TypeError):
        config.max_warnings = 3
    try:
        config.mute_duration = max(1, min(int(request.form.get('mute_duration', 10)), 1440))
    except (ValueError, TypeError):
        config.mute_duration = 10
    config.auto_mod_enabled = 'auto_mod_enabled' in request.form
    config.join_gate_enabled = 'join_gate_enabled' in request.form
    try:
        config.join_gate_days = max(1, min(int(request.form.get('join_gate_days', 7)), 365))
    except (ValueError, TypeError):
        config.join_gate_days = 7
    config.youtube_notify_enabled = 'youtube_notify_enabled' in request.form
    config.youtube_notify_channel_id = request.form.get('youtube_notify_channel_id', '').strip() or None
    config.auto_role_id = request.form.get('auto_role_id', '').strip() or None
    config.mod_role_id = request.form.get('mod_role_id', '').strip() or None
    config.admin_role_id = request.form.get('admin_role_id', '').strip() or None
    config.mute_role_id = request.form.get('mute_role_id', '').strip() or None
    config.dj_role_id = request.form.get('dj_role_id', '').strip() or None
    config.announcement_channel_id = request.form.get('announcement_channel_id', '').strip() or None
    config.bot_enabled = 'bot_enabled' in request.form
    config.audit_log_enabled = 'audit_log_enabled' in request.form
    config.audit_log_channel_id = request.form.get('audit_log_channel_id', '').strip() or None
    config.verify_enabled = 'verify_enabled' in request.form
    config.verify_role_id = request.form.get('verify_role_id', '').strip() or None
    config.verify_channel_id = request.form.get('verify_channel_id', '').strip() or None
    config.level_system_enabled = 'level_system_enabled' in request.form
    config.level_announce_channel_id = request.form.get('level_announce_channel_id', '').strip() or None
    config.level_role_rewards = request.form.get('level_role_rewards', '').strip()
    config.starboard_channel_id = request.form.get('starboard_channel_id', '').strip() or None
    try:
        config.starboard_threshold = max(1, min(int(request.form.get('starboard_threshold', 3)), 20))
    except (ValueError, TypeError):
        config.starboard_threshold = 3
    config.counting_channel_id = request.form.get('counting_channel_id', '').strip() or None
    config.suggestion_channel_id = request.form.get('suggestion_channel_id', '').strip() or None
    config.media_only_channel_id = request.form.get('media_only_channel_id', '').strip() or None
    config.auto_thread_channel_id = request.form.get('auto_thread_channel_id', '').strip() or None
    config.reaction_roles_channel_id = request.form.get('reaction_roles_channel_id', '').strip() or None
    config.ticket_category_id = request.form.get('ticket_category_id', '').strip() or None
    config.ticket_support_role_id = request.form.get('ticket_support_role_id', '').strip() or None
    config.custom_embed_color = request.form.get('custom_embed_color', '#6366f1').strip()[:7] or '#6366f1'
    config.timezone = request.form.get('timezone', 'UTC').strip()[:50] or 'UTC'
    config.updated_at = datetime.utcnow()
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'status': 'ok'}), 200

    return redirect(f'/bot/server/{guild_id}?saved=1')


@bot_bp.route('/server/<guild_id>/send', methods=['POST'])
@bot_admin_required
def send_message(guild_id):
    from app import db, BotUser, ServerConfig
    import json as _json
    bot_user = BotUser.query.get(session['bot_user_id'])
    if not bot_user:
        return jsonify({'error': 'Not authenticated'}), 401

    config = ServerConfig.query.filter_by(server_id=guild_id, bot_user_id=bot_user.id).first()
    if not config:
        return jsonify({'error': 'Server not found or no permission'}), 403

    bot_token = os.getenv('DISCORD_BOT_TOKEN', '')
    if not bot_token:
        return jsonify({'error': 'Bot token not configured'}), 400

    channel_id = request.form.get('channel_id', '').strip()
    if not channel_id:
        return jsonify({'error': 'Channel ID is required'}), 400

    message_type = request.form.get('message_type', 'text')
    payload = {}

    content = request.form.get('message_content', '').strip()
    role_pings = request.form.getlist('role_pings')
    ping_str = ' '.join(f'<@&{r}>' for r in role_pings if r.strip())
    if ping_str:
        content = (ping_str + ('\n' + content if content else '')).strip()

    if message_type == 'embed':
        embed = {}
        title = request.form.get('embed_title', '').strip()
        description = request.form.get('embed_description', '').strip()
        color_hex = request.form.get('embed_color', '#6366f1').lstrip('#')
        try:
            color_int = int(color_hex, 16)
        except ValueError:
            color_int = 0x6366f1
        if title:
            embed['title'] = title[:256]
        if description:
            embed['description'] = description[:4096]
        embed['color'] = color_int
        thumbnail_url = request.form.get('embed_thumbnail', '').strip()
        image_url = request.form.get('embed_image', '').strip()
        if thumbnail_url:
            embed['thumbnail'] = {'url': thumbnail_url}
        if image_url:
            embed['image'] = {'url': image_url}
        if request.form.get('nexus_footer') == '1':
            embed['footer'] = {
                'text': 'Nexus Bot • nexusbeta.vercel.app',
                'icon_url': 'https://nexusbeta.vercel.app/static/img/logo.png',
            }
            embed['timestamp'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S') + '+00:00'
        fields_json = request.form.get('embed_fields_json', '').strip()
        if fields_json:
            try:
                fields = _json.loads(fields_json)
                if isinstance(fields, list):
                    valid_fields = [f for f in fields if f.get('name') and f.get('value')]
                    embed['fields'] = valid_fields[:25]
            except Exception:
                pass
        if not title and not description:
            return jsonify({'error': 'Embed needs at least a title or description'}), 400
        payload['embeds'] = [embed]
        if content:
            payload['content'] = content
    else:
        if not content:
            return jsonify({'error': 'Message content is required'}), 400
        payload['content'] = content

    try:
        resp = requests.post(
            f'https://discord.com/api/v10/channels/{channel_id}/messages',
            json=payload,
            headers={'Authorization': f'Bot {bot_token}', 'Content-Type': 'application/json'},
            timeout=10,
        )
        if resp.status_code in (200, 201):
            return jsonify({'ok': True}), 200
        err_data = resp.json()
        return jsonify({'error': err_data.get('message', 'Discord rejected the message'), 'discord_code': err_data.get('code')}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bot_bp.route('/server/<guild_id>/channel/<channel_id>/messages')
@bot_admin_required
def channel_messages(guild_id, channel_id):
    bot_token = os.getenv('DISCORD_BOT_TOKEN', '')
    if not bot_token:
        return jsonify({'error': 'Bot token not configured'}), 400
    before = request.args.get('before', '').strip() or None
    limit = min(max(int(request.args.get('limit', 50)), 1), 100)
    params = {'limit': limit}
    if before:
        params['before'] = before
    try:
        resp = requests.get(
            f'https://discord.com/api/v10/channels/{channel_id}/messages',
            headers={'Authorization': f'Bot {bot_token}'},
            params=params,
            timeout=10
        )
        if resp.status_code == 200:
            return jsonify({'messages': resp.json()})
        elif resp.status_code == 403:
            return jsonify({'error': 'Missing Permissions — the bot cannot read this channel.'}), 403
        elif resp.status_code == 401:
            return jsonify({'error': 'Bot token is invalid.'}), 401
        return jsonify({'error': f'Discord API error ({resp.status_code})'}), resp.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bot_bp.route('/server/<guild_id>/channel/<channel_id>/reply', methods=['POST'])
@bot_admin_required
def reply_message(guild_id, channel_id):
    bot_token = os.getenv('DISCORD_BOT_TOKEN', '')
    if not bot_token:
        return jsonify({'error': 'Bot token not configured'}), 400
    content = request.form.get('content', '').strip()
    message_id = request.form.get('message_id', '').strip() or None
    if not content:
        return jsonify({'error': 'Message content is required'}), 400
    payload = {'content': content}
    if message_id:
        payload['message_reference'] = {
            'message_id': message_id,
            'channel_id': channel_id,
            'fail_if_not_exists': False
        }
    try:
        resp = requests.post(
            f'https://discord.com/api/v10/channels/{channel_id}/messages',
            json=payload,
            headers={'Authorization': f'Bot {bot_token}', 'Content-Type': 'application/json'},
            timeout=10
        )
        if resp.status_code in (200, 201):
            return jsonify({'ok': True, 'message': resp.json()})
        err = resp.json()
        return jsonify({'error': err.get('message', 'Discord rejected the message')}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bot_bp.route('/server/<guild_id>/channel/<channel_id>/delete-msg', methods=['POST'])
@bot_admin_required
def delete_channel_message(guild_id, channel_id):
    bot_token = os.getenv('DISCORD_BOT_TOKEN', '')
    if not bot_token:
        return jsonify({'error': 'Bot token not configured'}), 400
    message_id = request.form.get('message_id', '').strip()
    if not message_id:
        return jsonify({'error': 'Message ID required'}), 400
    try:
        resp = requests.delete(
            f'https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}',
            headers={'Authorization': f'Bot {bot_token}'},
            timeout=10
        )
        if resp.status_code == 204:
            return jsonify({'ok': True})
        return jsonify({'error': 'Cannot delete — missing Manage Messages permission or message too old'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bot_bp.route('/server/<guild_id>/logs')
@bot_admin_required
def server_logs(guild_id):
    from app import BotUser, ServerConfig, ModLog
    bot_user = BotUser.query.get(session['bot_user_id'])
    if not bot_user:
        return redirect('/bot/login')

    config = ServerConfig.query.filter_by(server_id=guild_id, bot_user_id=bot_user.id).first()
    if not config:
        return redirect('/bot/dashboard?error=server_not_found')

    page = request.args.get('page', 1, type=int)
    action_filter = request.args.get('action', '')
    query = ModLog.query.filter_by(server_id=guild_id).order_by(ModLog.created_at.desc())
    if action_filter:
        query = query.filter_by(action_type=action_filter)
    logs = query.paginate(page=page, per_page=25, error_out=False)

    guild_info = {'id': guild_id, 'name': config.server_name, 'icon': config.server_icon}
    return render_template('bot/logs.html', logs=logs, guild=guild_info, action_filter=action_filter)


@bot_bp.route('/account')
@bot_admin_required
def account():
    from app import BotUser, ServerConfig, User
    bot_user = BotUser.query.get(session['bot_user_id'])
    if not bot_user:
        return redirect('/bot/login')

    nexus_user = None
    if bot_user.nexus_user_id:
        nexus_user = User.query.get(bot_user.nexus_user_id)

    server_count = ServerConfig.query.filter_by(bot_user_id=bot_user.id).count()
    return render_template('bot/account.html', bot_user=bot_user, nexus_user=nexus_user, server_count=server_count)


@bot_bp.route('/account/link-nexus', methods=['POST'])
@bot_admin_required
def link_nexus():
    from app import db, BotUser, User
    bot_user = BotUser.query.get(session['bot_user_id'])
    if not bot_user:
        return redirect('/bot/login')

    if session.get('user_id'):
        nexus_user = User.query.get(session['user_id'])
        if nexus_user:
            bot_user.nexus_user_id = nexus_user.id
            db.session.commit()
            return redirect('/bot/account?linked=1')

    return redirect('/bot/account?error=not_logged_in_nexus')


@bot_bp.route('/account/unlink-nexus', methods=['POST'])
@bot_admin_required
def unlink_nexus():
    from app import db, BotUser
    bot_user = BotUser.query.get(session['bot_user_id'])
    if not bot_user:
        return redirect('/bot/login')

    bot_user.nexus_user_id = None
    db.session.commit()
    return redirect('/bot/account?unlinked=1')


@bot_bp.route('/account/delete', methods=['POST'])
@bot_admin_required
def delete_account():
    from app import db, BotUser
    bot_user = BotUser.query.get(session['bot_user_id'])
    if bot_user:
        db.session.delete(bot_user)
        db.session.commit()
    session.pop('bot_user_id', None)
    session.pop('bot_discord_token', None)
    return redirect('/bot/')


@bot_bp.route('/terms')
def terms():
    return render_template('bot/terms.html')


@bot_bp.route('/privacy')
def privacy():
    return render_template('bot/privacy.html')


@bot_bp.route('/help')
def help_page():
    return render_template('bot/help.html')


@bot_bp.route('/blog')
def blog():
    from bot_blog_data import BOT_BLOG_POSTS
    from app import BlogPost
    def _parse_date(p):
        try:
            return datetime.strptime(p.get('date', ''), '%B %d, %Y')
        except Exception:
            return datetime(2000, 1, 1)
    db_posts = BlogPost.query.filter_by(blog_type='bot', is_published=True).all()
    db_dicts = [p.to_dict() for p in db_posts]
    db_slugs = {p['slug'] for p in db_dicts}
    merged = db_dicts + [p for p in BOT_BLOG_POSTS if p['slug'] not in db_slugs]
    sorted_posts = sorted(merged, key=_parse_date, reverse=True)
    return render_template('bot/blog.html', posts=sorted_posts)


@bot_bp.route('/blog/<slug>')
def blog_post(slug):
    from bot_blog_data import BOT_BLOG_POSTS
    from app import BlogPost
    def _parse_date(p):
        try:
            return datetime.strptime(p.get('date', ''), '%B %d, %Y')
        except Exception:
            return datetime(2000, 1, 1)
    db_post = BlogPost.query.filter_by(blog_type='bot', slug=slug, is_published=True).first()
    if db_post:
        db_posts = BlogPost.query.filter_by(blog_type='bot', is_published=True).all()
        db_dicts = [p.to_dict() for p in db_posts]
        db_slugs = {p['slug'] for p in db_dicts}
        merged = db_dicts + [p for p in BOT_BLOG_POSTS if p['slug'] not in db_slugs]
        sorted_posts = sorted(merged, key=_parse_date, reverse=True)
        post = db_post.to_dict()
        post_idx = next((i for i, p in enumerate(sorted_posts) if p['slug'] == slug), 0)
        prev_post = sorted_posts[post_idx - 1] if post_idx > 0 else None
        next_post = sorted_posts[post_idx + 1] if post_idx < len(sorted_posts) - 1 else None
        return render_template('bot/blog_post.html', post=post, prev_post=prev_post, next_post=next_post)
    sorted_posts = sorted(BOT_BLOG_POSTS, key=_parse_date, reverse=True)
    post = None
    post_idx = -1
    for i, p in enumerate(sorted_posts):
        if p['slug'] == slug:
            post = p
            post_idx = i
            break
    if not post:
        abort(404)
    prev_post = sorted_posts[post_idx - 1] if post_idx > 0 else None
    next_post = sorted_posts[post_idx + 1] if post_idx < len(sorted_posts) - 1 else None
    return render_template('bot/blog_post.html', post=post, prev_post=prev_post, next_post=next_post)


@bot_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    from app import db, BotContactMessage
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        discord_username = request.form.get('discord_username', '').strip()
        category = request.form.get('category', '').strip()
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()

        if not name or not category or not subject or not message:
            return render_template('bot/contact.html', error='Please fill out all required fields.')

        if len(subject) > 200 or len(message) > 2000:
            return render_template('bot/contact.html', error='Subject or message is too long.')

        msg = BotContactMessage(
            name=name,
            discord_username=discord_username[:100] if discord_username else None,
            category=category[:50],
            subject=subject[:200],
            message=message[:2000],
            bot_user_id=session.get('bot_user_id'),
        )
        db.session.add(msg)
        db.session.commit()

        prefill_name = ''
        prefill_discord = ''
        if session.get('bot_user_id'):
            from app import BotUser
            bot_user = BotUser.query.get(session['bot_user_id'])
            if bot_user:
                prefill_name = bot_user.discord_global_name or bot_user.discord_username
                prefill_discord = bot_user.discord_username

        return render_template('bot/contact.html', success=True, prefill_name=prefill_name, prefill_discord=prefill_discord)

    prefill_name = ''
    prefill_discord = ''
    if session.get('bot_user_id'):
        from app import BotUser
        bot_user = BotUser.query.get(session['bot_user_id'])
        if bot_user:
            prefill_name = bot_user.discord_global_name or bot_user.discord_username
            prefill_discord = bot_user.discord_username

    return render_template('bot/contact.html', prefill_name=prefill_name, prefill_discord=prefill_discord)


@bot_bp.route('/status')
def status():
    from app import db, BotUser, ServerConfig
    from datetime import datetime

    services = []

    bot_status = 'operational'
    bot_detail = 'Bot is online and responding to commands'
    server_count = 0
    try:
        server_count = ServerConfig.query.distinct(ServerConfig.server_id).count()
        if server_count > 0:
            bot_detail = f'Online - managing {server_count} server{"s" if server_count != 1 else ""}'
        else:
            bot_status = 'beta'
            bot_detail = 'Available - no servers configured yet'
    except Exception:
        bot_status = 'degraded'
        bot_detail = 'Unable to check server count'

    services.append({
        'name': 'Discord Bot',
        'detail': bot_detail,
        'status': bot_status,
        'status_label': bot_status.replace('_', ' ').title(),
        'icon': 'fab fa-discord',
        'icon_bg': 'rgba(88,101,242,0.1)',
        'icon_color': '#5865f2',
        'uptime': '99.5',
    })

    dash_status = 'operational'
    dash_detail = 'Dashboard serving pages normally'
    user_count = 0
    try:
        user_count = BotUser.query.count()
        dash_detail = f'{user_count} registered user{"s" if user_count != 1 else ""} - serving normally'
    except Exception:
        dash_status = 'degraded'
        dash_detail = 'Database connectivity issue'

    services.append({
        'name': 'Web Dashboard',
        'detail': dash_detail,
        'status': dash_status,
        'status_label': dash_status.replace('_', ' ').title(),
        'icon': 'fas fa-columns',
        'icon_bg': 'rgba(99,102,241,0.1)',
        'icon_color': '#818cf8',
        'uptime': '99.9',
    })

    db_status = 'operational'
    db_detail = 'Connected and responding'
    db_ms = 0
    try:
        import time as _time
        t0 = _time.monotonic()
        db.session.execute(db.text('SELECT 1'))
        db_ms = round((_time.monotonic() - t0) * 1000, 1)
        db_detail = f'Connected - {db_ms}ms response time'
    except Exception:
        db_status = 'down'
        db_detail = 'Connection failed'

    services.append({
        'name': 'Database',
        'detail': db_detail,
        'status': db_status,
        'status_label': db_status.replace('_', ' ').title(),
        'icon': 'fas fa-database',
        'icon_bg': 'rgba(16,185,129,0.1)',
        'icon_color': '#10b981',
        'uptime': '99.8' if db_status == 'operational' else '95.0',
    })

    oauth_status = 'operational'
    oauth_detail = 'Discord OAuth configured and working'
    if not os.getenv('DISCORD_CLIENT_ID') or not os.getenv('DISCORD_CLIENT_SECRET'):
        oauth_status = 'degraded'
        oauth_detail = 'Client credentials not configured'

    services.append({
        'name': 'Discord OAuth',
        'detail': oauth_detail,
        'status': oauth_status,
        'status_label': oauth_status.replace('_', ' ').title(),
        'icon': 'fas fa-key',
        'icon_bg': 'rgba(245,158,11,0.1)',
        'icon_color': '#f59e0b',
        'uptime': '99.9' if oauth_status == 'operational' else '0.0',
    })

    api_status = 'operational'
    api_detail = 'Mod log API accepting requests'
    if not os.getenv('NEXUS_API_KEY'):
        api_status = 'beta'
        api_detail = 'API key not configured - logging limited'

    services.append({
        'name': 'Logging API',
        'detail': api_detail,
        'status': api_status,
        'status_label': api_status.replace('_', ' ').title(),
        'icon': 'fas fa-exchange-alt',
        'icon_bg': 'rgba(139,92,246,0.1)',
        'icon_color': '#8b5cf6',
        'uptime': '99.7',
    })

    all_operational = all(s['status'] in ('operational', 'beta') for s in services)
    has_degraded = any(s['status'] == 'degraded' for s in services)

    checked_at = datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')

    return render_template('bot/status.html', services=services, all_operational=all_operational,
                           has_degraded=has_degraded, checked_at=checked_at)


@bot_bp.route('/api/logs', methods=['POST'])
def receive_log():
    from app import db, ModLog
    api_key = request.headers.get('X-Nexus-Bot-Key', '')
    expected = os.getenv('NEXUS_API_KEY', '')
    if not expected or api_key != expected:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json or {}
    log_entry = ModLog(
        server_id=data.get('server_id', ''),
        action_type=data.get('action_type', 'unknown'),
        moderator_id=data.get('moderator_id'),
        moderator_name=data.get('moderator_name'),
        target_id=data.get('target_id'),
        target_name=data.get('target_name'),
        reason=data.get('reason'),
        details=data.get('details'),
    )
    db.session.add(log_entry)
    db.session.commit()
    return jsonify({'message': 'Log recorded', 'id': log_entry.id})


@bot_bp.route('/api/heartbeat', methods=['POST'])
def receive_heartbeat():
    from app import db, BotHeartbeat
    api_key = request.headers.get('X-Nexus-Bot-Key', '')
    expected = os.getenv('NEXUS_API_KEY', '')
    if not expected or api_key != expected:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json or {}
    bot_id = data.get('bot_id', '')

    hb = BotHeartbeat.query.filter_by(bot_id=bot_id).first() if bot_id else None
    if not hb:
        hb = BotHeartbeat(bot_id=bot_id)
        db.session.add(hb)

    hb.bot_name = data.get('bot_name', '')
    hb.guild_count = data.get('guild_count', 0)
    hb.user_count = data.get('user_count', 0)
    hb.latency_ms = data.get('latency_ms', 0)
    hb.uptime_seconds = data.get('uptime_seconds', 0)
    hb.status = data.get('status', 'unknown')
    hb.last_heartbeat = datetime.utcnow()
    db.session.commit()

    return jsonify({'message': 'Heartbeat received'})


@bot_bp.route('/api/heartbeat', methods=['GET'])
def get_heartbeat():
    from app import BotHeartbeat
    hb = BotHeartbeat.query.order_by(BotHeartbeat.last_heartbeat.desc()).first()
    if not hb or not hb.last_heartbeat:
        return jsonify({'hosting_connected': False})

    age = (datetime.utcnow() - hb.last_heartbeat).total_seconds()
    is_alive = age < 300

    return jsonify({
        'hosting_connected': is_alive,
        'bot_name': hb.bot_name or '',
        'guild_count': hb.guild_count or 0,
        'user_count': hb.user_count or 0,
        'latency_ms': hb.latency_ms or 0,
        'uptime_seconds': hb.uptime_seconds or 0,
        'status': hb.status or 'offline',
        'last_heartbeat': hb.last_heartbeat.isoformat() if hb.last_heartbeat else None,
    })


@bot_bp.route('/server/<guild_id>/reorder-roles', methods=['POST'])
@bot_admin_required
def reorder_roles(guild_id):
    from app import BotUser, ServerConfig
    bot_user = BotUser.query.get(session['bot_user_id'])
    if not bot_user:
        return jsonify({'error': 'Not logged in'}), 401

    config = ServerConfig.query.filter_by(server_id=guild_id, bot_user_id=bot_user.id).first()
    if not config:
        return jsonify({'error': 'Server not found'}), 404

    guilds_resp = requests.get('https://discord.com/api/users/@me/guilds', headers={
        'Authorization': f'Bearer {bot_user.discord_access_token}',
    }, timeout=10)
    if guilds_resp.status_code != 200:
        return jsonify({'error': 'Could not verify permissions'}), 403

    has_perm = False
    for g in guilds_resp.json():
        if g['id'] == guild_id:
            perms = int(g.get('permissions', 0))
            if g.get('owner') or (perms & 0x8) == 0x8 or (perms & 0x20) == 0x20:
                has_perm = True
            break

    if not has_perm:
        return jsonify({'error': 'No permission to manage this server'}), 403

    role_order = request.get_json()
    if not role_order or not isinstance(role_order, list):
        return jsonify({'error': 'Invalid role order data'}), 400

    bot_token = os.getenv('DISCORD_BOT_TOKEN')
    if not bot_token:
        return jsonify({'error': 'Bot token not configured'}), 500

    payload = []
    for item in role_order:
        role_id = item.get('id')
        position = item.get('position')
        if role_id and position is not None:
            payload.append({'id': role_id, 'position': int(position)})

    if not payload:
        return jsonify({'error': 'No valid role positions provided'}), 400

    try:
        resp = requests.patch(
            f'https://discord.com/api/v10/guilds/{guild_id}/roles',
            headers={
                'Authorization': f'Bot {bot_token}',
                'Content-Type': 'application/json',
            },
            json=payload,
            timeout=15,
        )
        if resp.status_code == 200:
            return jsonify({'success': True, 'message': 'Roles reordered'})
        else:
            error_data = resp.json() if resp.headers.get('content-type', '').startswith('application/json') else {}
            return jsonify({
                'error': error_data.get('message', f'Discord API returned {resp.status_code}'),
            }), resp.status_code
    except requests.Timeout:
        return jsonify({'error': 'Discord API timed out'}), 504
    except Exception as e:
        return jsonify({'error': str(e)}), 500
