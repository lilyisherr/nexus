from flask import Blueprint, render_template, request, redirect, session, url_for, jsonify, abort, Response, current_app, stream_with_context
from functools import wraps
from datetime import datetime, timedelta
import secrets
import re
import json
import os
import zipfile
import io
admin_bp = Blueprint('admin_dashboard', __name__, url_prefix='/nx-admin')

ADMIN_CSRF_KEY = 'admin_csrf_token'


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        from app import User
        if 'user_id' not in session:
            abort(404)
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            abort(404)
        return f(*args, **kwargs)
    return decorated


def _ensure_csrf():
    if ADMIN_CSRF_KEY not in session:
        session[ADMIN_CSRF_KEY] = secrets.token_hex(32)
    return session[ADMIN_CSRF_KEY]


def _check_csrf():
    token = request.form.get('csrf_token', '')
    if not token or token != session.get(ADMIN_CSRF_KEY, ''):
        abort(403)


def db_or(*args):
    from sqlalchemy import or_
    return or_(*args)


@admin_bp.context_processor
def inject_admin_context():
    from app import User, BotContactMessage
    admin_user = None
    unread_msg_count = 0
    if session.get('user_id'):
        admin_user = User.query.get(session['user_id'])
        try:
            unread_msg_count = BotContactMessage.query.filter_by(read=False).count()
        except Exception:
            pass
    return dict(admin_user=admin_user, admin_csrf_token=_ensure_csrf(), unread_msg_count=unread_msg_count)


@admin_bp.route('/assign-admin', methods=['GET', 'POST'])
def assign_admin():
    from sqlalchemy import text
    engine = current_app.extensions['sqlalchemy'].engine
    message = None
    all_users = []
    if request.method == 'POST':
        user_id = request.form.get('user_id', '').strip()
        if user_id:
            with engine.connect() as conn:
                result = conn.execute(text('SELECT id, username, email FROM "user" WHERE id = :uid'), {'uid': int(user_id)})
                row = result.fetchone()
                if row:
                    conn.execute(text('UPDATE "user" SET is_admin = true WHERE id = :uid'), {'uid': int(user_id)})
                    conn.commit()
                    message = f'Admin granted to {row[1] or row[2]} (ID {row[0]})'
                else:
                    message = f'No user found with ID {user_id}'
    with engine.connect() as conn:
        result = conn.execute(text('SELECT id, username, email, is_admin FROM "user" ORDER BY id'))
        all_users = [{'id': r[0], 'username': r[1], 'email': r[2], 'is_admin': r[3]} for r in result.fetchall()]
    return render_template('admin/assign_admin.html', users=all_users, message=message)


@admin_bp.route('/')
@admin_required
def dashboard():
    from app import db, User, Channel, BlogPost, BotContactMessage, BotUser, ServerConfig, BotHeartbeat, ChannelBotSettings, StreamSession
    from sqlalchemy import func, distinct
    user_count = User.query.count()
    channel_count = Channel.query.count()
    blog_count = BlogPost.query.count()
    message_count = BotContactMessage.query.count()
    unread_messages = BotContactMessage.query.filter_by(read=False).count()
    bot_user_count = BotUser.query.count()
    server_count = ServerConfig.query.count()
    active_bots = ChannelBotSettings.query.filter_by(bot_enabled=True).count()
    
    # T002: Currently Live Stat
    yesterday = datetime.utcnow() - timedelta(hours=24)
    currently_live_count = db.session.query(func.count(distinct(ChannelBotSettings.channel_id)))\
        .join(StreamSession, StreamSession.channel_id == ChannelBotSettings.channel_id)\
        .filter(ChannelBotSettings.bot_enabled == True)\
        .filter(StreamSession.start_time >= yesterday).scalar() or 0

    # T002: User growth chart (7-day registration count)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    new_users_week = User.query.filter(User.created_at >= seven_days_ago).count()

    heartbeat = BotHeartbeat.query.order_by(BotHeartbeat.last_heartbeat.desc()).first()
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_messages = BotContactMessage.query.order_by(BotContactMessage.created_at.desc()).limit(5).all()
    
    # T002: Recent Streams
    recent_streams = StreamSession.query.order_by(StreamSession.start_time.desc()).limit(8).all()
    
    admin_count = User.query.filter_by(is_admin=True).count()
    return render_template('admin/dashboard.html',
        user_count=user_count, channel_count=channel_count, blog_count=blog_count,
        message_count=message_count, unread_messages=unread_messages,
        bot_user_count=bot_user_count, server_count=server_count,
        heartbeat=heartbeat, recent_users=recent_users, recent_messages=recent_messages,
        active_bots=active_bots, admin_count=admin_count,
        currently_live_count=currently_live_count, new_users_week=new_users_week,
        recent_streams=recent_streams)


@admin_bp.route('/users')
@admin_required
def users():
    from app import User
    search = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20
    filter_type = request.args.get('filter', 'all')
    query = User.query
    if search:
        query = query.filter(
            db_or(User.username.ilike(f'%{search}%'), User.email.ilike(f'%{search}%'))
        )
    if filter_type == 'admin':
        query = query.filter_by(is_admin=True)
    elif filter_type == 'bot_enabled':
        query = query.filter_by(bot_enabled=True)
    users_paginated = query.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('admin/users.html', users=users_paginated, search=search, filter_type=filter_type)


@admin_bp.route('/users/<int:user_id>')
@admin_required
def user_detail(user_id):
    from app import User, Channel, ChannelBotSettings, StreamSession
    user = User.query.get_or_404(user_id)
    channels = Channel.query.filter_by(user_id=user.id).all()
    bot_settings = []
    stream_count = 0
    for ch in channels:
        bs = ChannelBotSettings.query.filter_by(channel_id=ch.id).first()
        if bs:
            bot_settings.append({'channel': ch, 'settings': bs})
        stream_count += StreamSession.query.filter_by(channel_id=ch.id).count()
    return render_template('admin/user_detail.html', user=user, channels=channels,
                           bot_settings=bot_settings, stream_count=stream_count)


@admin_bp.route('/users/<int:user_id>/toggle-admin', methods=['POST'])
@admin_required
def toggle_admin(user_id):
    from app import db, User
    _check_csrf()
    user = User.query.get_or_404(user_id)
    if user.id == session.get('user_id'):
        return redirect(url_for('admin_dashboard.users'))
    user.is_admin = not user.is_admin
    db.session.commit()
    return redirect(url_for('admin_dashboard.user_detail', user_id=user_id))


@admin_bp.route('/users/<int:user_id>/toggle-bot', methods=['POST'])
@admin_required
def toggle_user_bot(user_id):
    from app import db, User
    _check_csrf()
    user = User.query.get_or_404(user_id)
    user.bot_enabled = not user.bot_enabled
    db.session.commit()
    return redirect(url_for('admin_dashboard.user_detail', user_id=user_id))


@admin_bp.route('/view-as/<int:user_id>')
@admin_required
def view_as_user(user_id):
    from app import User
    User.query.get_or_404(user_id)
    session['view_as_user_id'] = user_id
    return redirect('/dashboard')


@admin_bp.route('/exit-view-as')
@admin_required
def exit_view_as():
    session.pop('view_as_user_id', None)
    return redirect(url_for('admin_dashboard.dashboard'))


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    from app import db, User
    _check_csrf()
    user = User.query.get_or_404(user_id)
    if user.id == session.get('user_id'):
        return redirect(url_for('admin_dashboard.users'))
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('admin_dashboard.users'))


@admin_bp.route('/channels')
@admin_required
def channels():
    from app import Channel, User, ChannelBotSettings
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '').strip()
    
    # Base query joining Channel with User and ChannelBotSettings
    query = Channel.query.outerjoin(User, Channel.user_id == User.id).outerjoin(ChannelBotSettings, Channel.id == ChannelBotSettings.channel_id)
    
    if search:
        query = query.filter(Channel.channel_name.ilike(f'%{search}%'))
    
    channels_paginated = query.order_by(Channel.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    
    # We need to make sure the objects are loaded correctly for the template
    return render_template('admin/channels.html', channels=channels_paginated, search=search)


@admin_bp.route('/channels/<int:channel_id>')
@admin_required
def channel_detail(channel_id):
    from app import Channel, User, ChannelBotSettings, StreamSession
    channel = Channel.query.get_or_404(channel_id)
    owner = User.query.get(channel.user_id)
    bot_settings = ChannelBotSettings.query.filter_by(channel_id=channel.id).first()
    recent_streams = StreamSession.query.filter_by(channel_id=channel.id).order_by(StreamSession.start_time.desc()).limit(10).all()
    
    return render_template('admin/channel_detail.html', 
                           channel=channel, 
                           owner=owner, 
                           bot_settings=bot_settings,
                           recent_streams=recent_streams)


@admin_bp.route('/api/channel-live/<int:channel_id>')
def channel_live_status(channel_id):
    import os
    import requests
    from app import Channel
    
    channel = Channel.query.get_or_404(channel_id)
    api_key = os.environ.get("YOUTUBE_API_KEY")
    
    if not api_key:
        return jsonify({"error": "YouTube API key not configured"}), 500
        
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "channelId": channel.youtube_channel_id,
        "eventType": "live",
        "type": "video",
        "key": api_key
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if "items" in data and len(data["items"]) > 0:
            video_id = data["items"][0]["id"]["videoId"]
            title = data["items"][0]["snippet"]["title"]
            
            # Get viewer count
            stats_url = "https://www.googleapis.com/youtube/v3/videos"
            stats_params = {
                "part": "liveStreamingDetails",
                "id": video_id,
                "key": api_key
            }
            stats_res = requests.get(stats_url, params=stats_params)
            stats_data = stats_res.json()
            
            viewers = 0
            if "items" in stats_data and len(stats_data["items"]) > 0:
                ls_details = stats_data["items"][0].get("liveStreamingDetails", {})
                viewers = int(ls_details.get("concurrentViewers", 0))
                
            return jsonify({"live": True, "title": title, "viewers": viewers})
        else:
            return jsonify({"live": False, "title": None, "viewers": 0})
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/blogs')
@admin_required
def blogs():
    from app import BlogPost
    blog_type = request.args.get('type', 'all')
    query = BlogPost.query
    if blog_type in ('nexus', 'bot'):
        query = query.filter_by(blog_type=blog_type)
    posts = query.order_by(BlogPost.created_at.desc()).all()
    from blog_data import BLOG_POSTS
    from bot_blog_data import BOT_BLOG_POSTS
    static_nexus_count = len(BLOG_POSTS)
    static_bot_count = len(BOT_BLOG_POSTS)
    return render_template('admin/blogs.html', posts=posts, blog_type=blog_type,
                           static_nexus_count=static_nexus_count, static_bot_count=static_bot_count)


@admin_bp.route('/blogs/new')
@admin_required
def blog_new():
    return render_template('admin/blog_form.html', post=None, editing=False)


@admin_bp.route('/blogs/create', methods=['POST'])
@admin_required
def blog_create():
    from app import db, BlogPost
    _check_csrf()
    slug = request.form.get('slug', '').strip()
    slug = re.sub(r'[^a-z0-9-]', '', slug.lower().replace(' ', '-'))
    if not slug:
        slug = re.sub(r'[^a-z0-9-]', '', request.form.get('title', 'post').lower().replace(' ', '-'))
    title = request.form.get('title', '').strip()
    blog_type = request.form.get('blog_type', 'nexus')
    if blog_type not in ('nexus', 'bot'):
        blog_type = 'nexus'
    tag = request.form.get('tag', 'announcement').strip()
    tag_label = request.form.get('tag_label', 'Announcement').strip()
    summary = request.form.get('summary', '').strip()
    content = request.form.get('content', '').strip()
    is_published = request.form.get('is_published') == 'on'
    now = datetime.utcnow()
    date_display = now.strftime('%B %d, %Y')
    date_short = now.strftime('%b %d, %Y')
    if request.form.get('date_display', '').strip():
        date_display = request.form.get('date_display').strip()
    if request.form.get('date_short', '').strip():
        date_short = request.form.get('date_short').strip()
    post = BlogPost(
        blog_type=blog_type, slug=slug, title=title,
        date_display=date_display, date_short=date_short,
        tag=tag, tag_label=tag_label, summary=summary,
        content=content, is_published=is_published
    )
    db.session.add(post)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return redirect(url_for('admin_dashboard.blog_new'))
    return redirect(url_for('admin_dashboard.blogs'))


@admin_bp.route('/blogs/<int:post_id>/edit')
@admin_required
def blog_edit(post_id):
    from app import BlogPost
    post = BlogPost.query.get_or_404(post_id)
    return render_template('admin/blog_form.html', post=post, editing=True)


@admin_bp.route('/blogs/<int:post_id>/update', methods=['POST'])
@admin_required
def blog_update(post_id):
    from app import db, BlogPost
    _check_csrf()
    post = BlogPost.query.get_or_404(post_id)
    post.title = request.form.get('title', post.title).strip()
    slug = request.form.get('slug', post.slug).strip()
    post.slug = re.sub(r'[^a-z0-9-]', '', slug.lower().replace(' ', '-')) or post.slug
    post.blog_type = request.form.get('blog_type', post.blog_type)
    if post.blog_type not in ('nexus', 'bot'):
        post.blog_type = 'nexus'
    post.tag = request.form.get('tag', post.tag).strip()
    post.tag_label = request.form.get('tag_label', post.tag_label).strip()
    post.summary = request.form.get('summary', post.summary).strip()
    post.content = request.form.get('content', post.content).strip()
    post.is_published = request.form.get('is_published') == 'on'
    if request.form.get('date_display', '').strip():
        post.date_display = request.form.get('date_display').strip()
    if request.form.get('date_short', '').strip():
        post.date_short = request.form.get('date_short').strip()
    post.updated_at = datetime.utcnow()
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
    return redirect(url_for('admin_dashboard.blogs'))


@admin_bp.route('/blogs/<int:post_id>/delete', methods=['POST'])
@admin_required
def blog_delete(post_id):
    from app import db, BlogPost
    _check_csrf()
    post = BlogPost.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    return redirect(url_for('admin_dashboard.blogs'))


@admin_bp.route('/blogs/<int:post_id>/toggle-publish', methods=['POST'])
@admin_required
def blog_toggle_publish(post_id):
    from app import db, BlogPost
    _check_csrf()
    post = BlogPost.query.get_or_404(post_id)
    post.is_published = not post.is_published
    post.updated_at = datetime.utcnow()
    db.session.commit()
    return redirect(url_for('admin_dashboard.blogs'))


@admin_bp.route('/blogs/<int:post_id>/duplicate', methods=['POST'])
@admin_required
def blog_duplicate(post_id):
    from app import db, BlogPost
    _check_csrf()
    original = BlogPost.query.get_or_404(post_id)
    base_slug = original.slug + '-copy'
    slug = base_slug
    counter = 2
    while BlogPost.query.filter_by(blog_type=original.blog_type, slug=slug).first():
        slug = f'{base_slug}-{counter}'
        counter += 1
    duplicate = BlogPost(
        blog_type=original.blog_type,
        slug=slug,
        title=original.title + ' (Copy)',
        date_display=datetime.utcnow().strftime('%B %d, %Y'),
        date_short=datetime.utcnow().strftime('%b %d, %Y'),
        tag=original.tag, tag_label=original.tag_label,
        summary=original.summary, content=original.content,
        is_published=False
    )
    db.session.add(duplicate)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
    return redirect(url_for('admin_dashboard.blogs'))


@admin_bp.route('/blogs/import-static', methods=['POST'])
@admin_required
def blog_import_static():
    from app import db, BlogPost
    _check_csrf()
    import_type = request.form.get('import_type', 'nexus')
    if import_type == 'nexus':
        from blog_data import BLOG_POSTS as static_posts
    elif import_type == 'bot':
        from bot_blog_data import BOT_BLOG_POSTS as static_posts
    else:
        return redirect(url_for('admin_dashboard.blogs'))
    imported = 0
    for sp in static_posts:
        existing = BlogPost.query.filter_by(blog_type=import_type, slug=sp['slug']).first()
        if not existing:
            post = BlogPost(
                blog_type=import_type, slug=sp['slug'], title=sp['title'],
                date_display=sp.get('date', ''), date_short=sp.get('date_short', ''),
                tag=sp.get('tag', 'announcement'), tag_label=sp.get('tag_label', 'Announcement'),
                summary=sp.get('summary', ''), content=sp.get('content', ''),
                is_published=True
            )
            db.session.add(post)
            imported += 1
    db.session.commit()
    return redirect(url_for('admin_dashboard.blogs'))


@admin_bp.route('/messages')
@admin_required
def messages():
    from app import BotContactMessage
    filter_type = request.args.get('filter', 'all')
    query = BotContactMessage.query
    if filter_type == 'unread':
        query = query.filter_by(read=False)
    elif filter_type == 'read':
        query = query.filter_by(read=True)
    msgs = query.order_by(BotContactMessage.created_at.desc()).all()
    return render_template('admin/messages.html', messages=msgs, filter_type=filter_type)


@admin_bp.route('/messages/<int:msg_id>/toggle-read', methods=['POST'])
@admin_required
def toggle_message_read(msg_id):
    from app import db, BotContactMessage
    _check_csrf()
    msg = BotContactMessage.query.get_or_404(msg_id)
    msg.read = not msg.read
    db.session.commit()
    return redirect(url_for('admin_dashboard.messages'))


@admin_bp.route('/messages/<int:msg_id>/delete', methods=['POST'])
@admin_required
def delete_message(msg_id):
    from app import db, BotContactMessage
    _check_csrf()
    msg = BotContactMessage.query.get_or_404(msg_id)
    db.session.delete(msg)
    db.session.commit()
    return redirect(url_for('admin_dashboard.messages'))


@admin_bp.route('/messages/mark-all-read', methods=['POST'])
@admin_required
def mark_all_read():
    from app import db, BotContactMessage
    _check_csrf()
    BotContactMessage.query.filter_by(read=False).update({'read': True})
    db.session.commit()
    return redirect(url_for('admin_dashboard.messages'))


@admin_bp.route('/changelog/send', methods=['POST'])
@admin_required
def changelog_send():
    import requests as _req
    from changelog_data import changelog_data
    _check_csrf()
    bot_token = __import__('os').getenv('DISCORD_BOT_TOKEN', '')
    if not bot_token:
        return jsonify({'error': 'DISCORD_BOT_TOKEN is not configured'}), 400
    channel_id = request.form.get('channel_id', '').strip()
    if not channel_id:
        return jsonify({'error': 'Channel ID is required'}), 400
    try:
        idx = int(request.form.get('version_index', '0'))
        entry = changelog_data[idx]
    except (ValueError, IndexError):
        return jsonify({'error': 'Invalid version'}), 400
    type_colors = {'feature': 0x10b981, 'improvement': 0x6366f1, 'fix': 0xf59e0b}
    color = type_colors.get(entry.get('type', 'improvement'), 0x6366f1)
    type_labels = {'feature': '🟢 New Feature', 'improvement': '🟣 Improvement', 'fix': '🟡 Bug Fix'}
    type_label = type_labels.get(entry.get('type', 'improvement'), '🟣 Update')
    changes = entry.get('changes', [])
    description_text = entry.get('description', '')
    changes_text = '\n'.join(f'• {c}' for c in changes)
    embed_desc = ''
    if description_text:
        embed_desc += description_text + '\n\n'
    if changes_text:
        embed_desc += changes_text
    ping_role_id = request.form.get('ping_role_id', '').strip()
    content = f'<@&{ping_role_id}>' if ping_role_id else None
    embed = {
        'title': f'{entry["version"]} — {entry["title"]}',
        'description': embed_desc[:4096],
        'color': color,
        'url': 'https://nexusbeta.vercel.app/changelog',
        'fields': [
            {'name': 'Type', 'value': type_label, 'inline': True},
            {'name': 'Released', 'value': entry.get('date', ''), 'inline': True},
            {'name': 'Changes', 'value': str(len(changes)), 'inline': True},
        ],
        'footer': {
            'text': 'Nexus Bot • Full changelog at nexusbeta.vercel.app/changelog',
            'icon_url': 'https://nexusbeta.vercel.app/static/img/logo.png',
        },
        'timestamp': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S') + '+00:00',
    }
    payload = {'embeds': [embed]}
    if content:
        payload['content'] = content
    try:
        resp = _req.post(
            f'https://discord.com/api/v10/channels/{channel_id}/messages',
            json=payload,
            headers={'Authorization': f'Bot {bot_token}', 'Content-Type': 'application/json'},
            timeout=10,
        )
        if resp.status_code in (200, 201):
            return jsonify({'ok': True, 'version': entry['version']}), 200
        err = resp.json()
        return jsonify({'error': err.get('message', 'Discord API error'), 'discord_code': err.get('code')}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/changelog')
@admin_required
def changelog_admin():
    from changelog_data import changelog_data
    latest = changelog_data[0] if changelog_data else None
    discord_text = ""
    if latest:
        lines = [
            f"**[{latest['version']}] {latest['title']}**",
            f"*{latest['date']}*",
            "",
            latest['description'],
            "",
        ]
        if latest.get('changes'):
            for change in latest['changes']:
                lines.append(f"• {change}")
        lines.append("")
        lines.append("Full changelog: https://nexusbeta.vercel.app/changelog")
        discord_text = "\n".join(lines)
    return render_template('admin/changelog.html', changelog=changelog_data, discord_text=discord_text, latest=latest)


@admin_bp.route('/settings')
@admin_required
def settings():
    from app import SiteSetting
    all_settings = {}
    for s in SiteSetting.query.all():
        all_settings[s.key] = s.value
    return render_template('admin/settings.html', settings=all_settings)


@admin_bp.route('/settings/save', methods=['POST'])
@admin_required
def settings_save():
    from app import db, SiteSetting
    _check_csrf()
    setting_keys = [
        'maintenance_mode', 'beta_banner_enabled', 'beta_banner_text',
        'announcement_text', 'announcement_enabled',
        'registration_enabled', 'max_channels_per_user',
        'default_bot_prefix', 'discord_invite_url',
        'contact_email', 'site_description',
        'homepage_hero_title', 'homepage_hero_subtitle',
        'custom_css', 'footer_text', 'google_analytics_id',
        'primary_color', 'secondary_color',
        'twitter_url', 'github_url', 'youtube_url',
        'rate_limit_enabled', 'rate_limit_per_minute',
        'bot_auto_join', 'welcome_message',
        'blog_comments_enabled',
    ]
    for key in setting_keys:
        value = request.form.get(key, '')
        setting = SiteSetting.query.filter_by(key=key).first()
        if setting:
            setting.value = value
        else:
            db.session.add(SiteSetting(key=key, value=value))
    db.session.commit()
    return redirect(url_for('admin_dashboard.settings'))


@admin_bp.route('/servers')
@admin_required
def servers():
    from app import ServerConfig, BotUser
    search = request.args.get('q', '').strip()
    query = ServerConfig.query
    if search:
        query = query.filter(
            db_or(ServerConfig.server_name.ilike(f'%{search}%'), ServerConfig.server_id.ilike(f'%{search}%'))
        )
    configs = query.order_by(ServerConfig.created_at.desc()).all()
    return render_template('admin/servers.html', configs=configs, search=search)


@admin_bp.route('/servers/<int:config_id>')
@admin_required
def server_detail(config_id):
    from app import ServerConfig, ModLog
    config = ServerConfig.query.get_or_404(config_id)
    mod_logs = ModLog.query.filter_by(server_id=config.server_id).order_by(ModLog.created_at.desc()).limit(20).all()
    return render_template('admin/server_detail.html', config=config, mod_logs=mod_logs)


@admin_bp.route('/mod-logs')
@admin_required
def mod_logs():
    from app import ModLog
    page = request.args.get('page', 1, type=int)
    action_filter = request.args.get('action', 'all')
    server_filter = request.args.get('server', '').strip()
    query = ModLog.query
    if action_filter != 'all':
        query = query.filter_by(action_type=action_filter)
    if server_filter:
        query = query.filter_by(server_id=server_filter)
    logs_paginated = query.order_by(ModLog.created_at.desc()).paginate(page=page, per_page=30, error_out=False)
    action_types = []
    try:
        from sqlalchemy import distinct
        from app import db
        action_types = [r[0] for r in db.session.query(distinct(ModLog.action_type)).all()]
    except Exception:
        pass
    return render_template('admin/mod_logs.html', logs=logs_paginated,
                           action_filter=action_filter, server_filter=server_filter,
                           action_types=action_types)


@admin_bp.route('/analytics')
@admin_required
def analytics():
    from app import db, User, Channel, BotUser, ServerConfig, BlogPost, BotContactMessage, ChannelBotSettings
    from sqlalchemy import func
    user_count = User.query.count()
    channel_count = Channel.query.count()
    bot_user_count = BotUser.query.count()
    server_count = ServerConfig.query.count()
    blog_count = BlogPost.query.count()
    message_count = BotContactMessage.query.count()
    active_bots = ChannelBotSettings.query.filter_by(bot_enabled=True).count()
    recent_registrations = []
    try:
        rows = db.session.query(
            func.date(User.created_at).label('day'),
            func.count(User.id).label('count')
        ).group_by(func.date(User.created_at)).order_by(func.date(User.created_at).desc()).limit(30).all()
        recent_registrations = [{'day': str(r.day), 'count': r.count} for r in rows]
    except Exception:
        pass
    bot_user_registrations = []
    try:
        rows = db.session.query(
            func.date(BotUser.created_at).label('day'),
            func.count(BotUser.id).label('count')
        ).group_by(func.date(BotUser.created_at)).order_by(func.date(BotUser.created_at).desc()).limit(30).all()
        bot_user_registrations = [{'day': str(r.day), 'count': r.count} for r in rows]
    except Exception:
        pass
    return render_template('admin/analytics.html',
        user_count=user_count, channel_count=channel_count,
        bot_user_count=bot_user_count, server_count=server_count,
        blog_count=blog_count, message_count=message_count,
        active_bots=active_bots,
        recent_registrations=recent_registrations,
        bot_user_registrations=bot_user_registrations)


@admin_bp.route('/bot-status')
@admin_required
def bot_status():
    from app import BotHeartbeat, ServerConfig
    heartbeat = BotHeartbeat.query.order_by(BotHeartbeat.last_heartbeat.desc()).first()
    total_servers = ServerConfig.query.count()
    enabled_servers = ServerConfig.query.filter_by(bot_enabled=True).count()
    return render_template('admin/bot_status.html', heartbeat=heartbeat,
                           total_servers=total_servers, enabled_servers=enabled_servers)


@admin_bp.route('/system')
@admin_required
def system_info():
    import sys
    import platform
    import os
    from app import db
    info = {
        'python_version': sys.version,
        'platform': platform.platform(),
        'flask_env': os.getenv('FLASK_ENV', 'production'),
        'debug': os.getenv('FLASK_DEBUG', 'off'),
        'database_url': ('postgresql' if 'postgresql' in str(db.engine.url) else 'sqlite'),
        'secret_key_set': bool(os.getenv('SECRET_KEY')),
        'google_oauth_configured': bool(os.getenv('GOOGLE_CLIENT_ID')),
        'discord_oauth_configured': bool(os.getenv('DISCORD_CLIENT_ID')),
        'discord_bot_token_set': bool(os.getenv('DISCORD_BOT_TOKEN')),
        'youtube_api_key_set': bool(os.getenv('YOUTUBE_API_KEY')),
        'bot_access_token_set': bool(os.getenv('BOT_ACCESS_TOKEN')),
        'nexus_api_key_set': bool(os.getenv('NEXUS_API_KEY')),
        'is_vercel': bool(os.getenv('VERCEL')),
        'port': os.getenv('PORT', '5000'),
    }
    table_counts = {}
    try:
        from sqlalchemy import inspect as sa_inspect
        inspector = sa_inspect(db.engine)
        for table_name in inspector.get_table_names():
            try:
                from sqlalchemy import text
                result = db.session.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
                table_counts[table_name] = result.scalar()
            except Exception:
                table_counts[table_name] = '?'
    except Exception:
        pass
    return render_template('admin/system.html', info=info, table_counts=table_counts)


@admin_bp.route('/export/<string:export_type>')
@admin_required
def export_data(export_type):
    from app import User, Channel, BotUser, ServerConfig, BlogPost, BotContactMessage
    if export_type == 'users':
        data = [u.to_dict() for u in User.query.all()]
    elif export_type == 'channels':
        data = [c.to_dict() for c in Channel.query.all()]
    elif export_type == 'bot-users':
        data = [{'id': u.id, 'discord_id': u.discord_id, 'discord_username': u.discord_username,
                 'discord_global_name': u.discord_global_name, 'nexus_user_id': u.nexus_user_id,
                 'created_at': u.created_at.isoformat() if u.created_at else None} for u in BotUser.query.all()]
    elif export_type == 'servers':
        data = [{'id': c.id, 'server_id': c.server_id, 'server_name': c.server_name,
                 'prefix': c.prefix, 'bot_enabled': c.bot_enabled,
                 'created_at': c.created_at.isoformat() if c.created_at else None} for c in ServerConfig.query.all()]
    elif export_type == 'blogs':
        data = [{'id': p.id, 'blog_type': p.blog_type, 'slug': p.slug, 'title': p.title,
                 'tag': p.tag, 'summary': p.summary, 'is_published': p.is_published,
                 'created_at': p.created_at.isoformat() if p.created_at else None} for p in BlogPost.query.all()]
    elif export_type == 'messages':
        data = [{'id': m.id, 'name': m.name, 'discord_username': m.discord_username,
                 'category': m.category, 'subject': m.subject, 'message': m.message,
                 'read': m.read, 'created_at': m.created_at.isoformat() if m.created_at else None}
                for m in BotContactMessage.query.all()]
    else:
        abort(404)
    return Response(
        json.dumps(data, indent=2),
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment; filename=nexus_{export_type}_{datetime.utcnow().strftime("%Y%m%d")}.json'}
    )


@admin_bp.route('/project-export')
@admin_required
def project_export():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    skip_dirs = {'.git', '__pycache__', '.cache', 'node_modules', '.upm', 'flask_session'}
    skip_exts = {'.pyc', '.pyo', '.pyd'}

    hidden_files = []
    file_tree = []
    total_size = 0
    file_count = 0

    for root, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        rel_root = os.path.relpath(root, project_root)
        for fname in sorted(files):
            if fname.endswith(tuple(skip_exts)):
                continue
            rel_path = os.path.join(rel_root, fname) if rel_root != '.' else fname
            rel_path = rel_path.replace('\\', '/')
            full_path = os.path.join(root, fname)
            try:
                size = os.path.getsize(full_path)
            except OSError:
                size = 0
            total_size += size
            file_count += 1
            file_tree.append({'path': rel_path, 'size': size})
            if fname.startswith('.') and fname in ('.env', '.env.local', 'nexus_bot.env'):
                try:
                    with open(full_path, 'r', errors='replace') as f:
                        content = f.read()
                    hidden_files.append({'path': rel_path, 'content': content})
                except OSError:
                    pass

    return render_template('admin/project_export.html',
                           file_tree=file_tree, hidden_files=hidden_files,
                           file_count=file_count, total_size=total_size)


@admin_bp.route('/project-export/download')
@admin_required
def project_export_download():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    skip_dirs = {'.git', '__pycache__', '.cache', 'node_modules', '.upm', 'flask_session'}
    skip_exts = {'.pyc', '.pyo', '.pyd'}

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(project_root):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            rel_root = os.path.relpath(root, project_root)
            for fname in files:
                if fname.endswith(tuple(skip_exts)):
                    continue
                rel_path = os.path.join(rel_root, fname) if rel_root != '.' else fname
                rel_path = rel_path.replace('\\', '/')
                full_path = os.path.join(root, fname)
                try:
                    zf.write(full_path, rel_path)
                except (OSError, PermissionError):
                    pass
    buf.seek(0)
    filename = f'nexus-project-{datetime.utcnow().strftime("%Y%m%d-%H%M%S")}.zip'
    return Response(
        buf.read(),
        mimetype='application/zip',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )
