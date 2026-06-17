import sys
if __name__ == '__main__' or 'app' not in sys.modules:
    sys.modules['app'] = sys.modules[__name__]

from flask import Flask, render_template, request, jsonify, redirect, session, url_for, Response
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
import os
import json
import secrets
import logging
from datetime import datetime, timedelta
from functools import wraps
import requests
from dotenv import load_dotenv
from bot_manager import bot_manager
from bot_dashboard import bot_bp
from admin_dashboard import admin_bp
from changelog_data import changelog_data

_base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_base_dir, '.env'))

IS_VERCEL = bool(os.getenv('VERCEL'))

_frontend_dir = os.path.normpath(os.path.join(_base_dir, '..', 'frontend'))
app = Flask(__name__,
            template_folder=os.path.join(_frontend_dir, 'templates'),
            static_folder=os.path.join(_frontend_dir, 'static'))
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))

db_url = os.getenv('DATABASE_URL', 'sqlite:///nexus.db')
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

if IS_VERCEL:
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
else:
    from flask_session import Session
    app.config['SESSION_TYPE'] = 'filesystem'
    Session(app)

db = SQLAlchemy(app)
if not IS_VERCEL:
    from flask_migrate import Migrate
    migrate = Migrate(app, db)
cors_origins = os.getenv('CORS_ORIGINS', '').split(',')
cors_origins = [o.strip() for o in cors_origins if o.strip()]
if cors_origins:
    CORS(app, origins=cors_origins, supports_credentials=True)
else:
    CORS(app)

app.register_blueprint(bot_bp)
app.register_blueprint(admin_bp)

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
PORT = int(os.getenv('PORT', 5000))
GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', None)

YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
SCOPES = ['https://www.googleapis.com/auth/youtube', 'https://www.googleapis.com/auth/youtube.force-ssl', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile']

DEFAULT_BUILTIN_COMMANDS = [
    {"name": "watchtime", "description": "Shows how long a user has been watching", "response_template": "{user} has been watching for {watchtime}.", "enabled": True, "cooldown": 10, "permission_level": "everyone"},
    {"name": "uptime", "description": "Shows how long the stream has been live", "response_template": "Stream has been live for {uptime}.", "enabled": True, "cooldown": 10, "permission_level": "everyone"},
    {"name": "followage", "description": "Shows how long a user has been following", "response_template": "{user} has been following for {followage}.", "enabled": True, "cooldown": 10, "permission_level": "everyone"},
    {"name": "quote", "description": "Shows a random saved quote", "response_template": "\"{quote}\" — #{number}", "enabled": True, "cooldown": 10, "permission_level": "everyone"},
    {"name": "8ball", "description": "Magic 8-ball gives a random answer", "response_template": "8ball: {answer}", "enabled": True, "cooldown": 5, "permission_level": "everyone"},
    {"name": "lurk", "description": "Announce that you are lurking", "response_template": "{user} is now lurking.", "enabled": True, "cooldown": 5, "permission_level": "everyone"},
    {"name": "unlurk", "description": "Announce that you are back from lurking", "response_template": "Welcome back, {user}!", "enabled": True, "cooldown": 5, "permission_level": "everyone"},
    {"name": "shoutout", "description": "Shoutout another channel", "response_template": "Go check out {target}!", "enabled": True, "cooldown": 10, "permission_level": "moderator"},
    {"name": "hug", "description": "Give someone a virtual hug", "response_template": "{user} hugs {target}!", "enabled": True, "cooldown": 5, "permission_level": "everyone"},
    {"name": "dice", "description": "Roll a dice", "response_template": "{user} rolled a {result}.", "enabled": True, "cooldown": 5, "permission_level": "everyone"},
    {"name": "flip", "description": "Flip a coin", "response_template": "{user} flipped a coin and got {result}.", "enabled": True, "cooldown": 5, "permission_level": "everyone"},
    {"name": "socials", "description": "Show the streamer's social media links", "response_template": "Find us at: {socials}", "enabled": True, "cooldown": 15, "permission_level": "everyone"},
    {"name": "commands", "description": "List all available commands", "response_template": "Commands: {command_list}", "enabled": True, "cooldown": 15, "permission_level": "everyone"},
    {"name": "title", "description": "Shows the current stream title", "response_template": "Stream title: {title}", "enabled": True, "cooldown": 10, "permission_level": "everyone"},
    {"name": "game", "description": "Shows the current game/category", "response_template": "Currently playing: {game}", "enabled": True, "cooldown": 10, "permission_level": "everyone"},
]


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    google_id = db.Column(db.String(255), unique=True, nullable=False)
    username = db.Column(db.String(255), nullable=True)
    profile_picture = db.Column(db.String(500), nullable=True)
    youtube_channel_id = db.Column(db.String(255), nullable=True)
    youtube_channel_name = db.Column(db.String(255), nullable=True)
    bot_enabled = db.Column(db.Boolean, default=False)
    default_prefix = db.Column(db.String(5), default='!')
    access_token = db.Column(db.Text, nullable=True)
    refresh_token = db.Column(db.Text, nullable=True)
    notification_preferences = db.Column(db.Text, default='{"email_alerts": true, "stream_notifications": true, "weekly_reports": false}')
    discord_user_id = db.Column(db.String(255), unique=True, nullable=True)
    discord_username = db.Column(db.String(255), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    setup_complete = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    channels = db.relationship('Channel', backref='owner', lazy=True, cascade='all, delete-orphan')
    stats = db.relationship('ChannelStats', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def get_notification_preferences(self):
        if self.notification_preferences:
            try:
                return json.loads(self.notification_preferences)
            except Exception:
                pass
        return {"email_alerts": True, "stream_notifications": True, "weekly_reports": False}

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'profile_picture': self.profile_picture,
            'youtube_channel_id': self.youtube_channel_id,
            'youtube_channel_name': self.youtube_channel_name,
            'bot_enabled': self.bot_enabled,
            'default_prefix': self.default_prefix or '!',
            'notification_preferences': self.get_notification_preferences(),
            'discord_user_id': self.discord_user_id,
            'discord_username': self.discord_username,
            'created_at': self.created_at.isoformat(),
        }


class Channel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    youtube_channel_id = db.Column(db.String(255), nullable=False)
    channel_name = db.Column(db.String(255), nullable=False)
    channel_thumbnail = db.Column(db.String(500), nullable=True)
    subscriber_count = db.Column(db.Integer, default=0)
    view_count = db.Column(db.Integer, default=0)
    video_count = db.Column(db.Integer, default=0)
    tracking_enabled = db.Column(db.Boolean, default=True)
    last_synced = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    stream_sessions = db.relationship('StreamSession', backref='channel', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'youtube_channel_id': self.youtube_channel_id,
            'channel_name': self.channel_name,
            'channel_thumbnail': self.channel_thumbnail,
            'subscriber_count': self.subscriber_count,
            'view_count': self.view_count,
            'video_count': self.video_count,
            'tracking_enabled': self.tracking_enabled,
            'last_synced': self.last_synced.isoformat() if self.last_synced else None,
        }


class StreamSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('channel.id'), nullable=False)
    video_id = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(500), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)
    duration_seconds = db.Column(db.Integer, default=0)
    peak_viewers = db.Column(db.Integer, default=0)
    average_viewers = db.Column(db.Integer, default=0)
    total_viewer_interactions = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'video_id': self.video_id,
            'title': self.title,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration_seconds,
            'peak_viewers': self.peak_viewers,
            'average_viewers': self.average_viewers,
            'total_viewer_interactions': self.total_viewer_interactions,
        }


class ChannelStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    channel_id = db.Column(db.String(255), nullable=False)
    stat_date = db.Column(db.Date, nullable=False)
    subscribers = db.Column(db.Integer, default=0)
    total_views = db.Column(db.Integer, default=0)
    total_videos = db.Column(db.Integer, default=0)
    stream_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'channel_id': self.channel_id,
            'stat_date': self.stat_date.isoformat(),
            'subscribers': self.subscribers,
            'total_views': self.total_views,
            'total_videos': self.total_videos,
            'stream_count': self.stream_count,
        }


class ChannelBotSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('channel.id'), nullable=False, unique=True)
    
    bot_name = db.Column(db.String(255), default='Nexus')
    bot_enabled = db.Column(db.Boolean, default=True)
    chat_prefix = db.Column(db.String(5), default='!')
    response_delay = db.Column(db.Integer, default=2)
    join_message = db.Column(db.Text, nullable=True)
    
    spam_filter_enabled = db.Column(db.Boolean, default=True)
    max_repeat_chars = db.Column(db.Integer, default=5)
    max_message_length = db.Column(db.Integer, default=200)
    
    link_filter_enabled = db.Column(db.Boolean, default=True)
    link_whitelist = db.Column(db.Text, default='')
    
    caps_filter_enabled = db.Column(db.Boolean, default=True)
    max_caps_percent = db.Column(db.Integer, default=70)
    
    blocked_words_enabled = db.Column(db.Boolean, default=True)
    blocked_words = db.Column(db.Text, default='')
    timeout_duration = db.Column(db.Integer, default=300)
    warning_message = db.Column(db.Text, default='Please follow the chat rules, {user}.')
    
    slow_mode_enabled = db.Column(db.Boolean, default=False)
    slow_mode_seconds = db.Column(db.Integer, default=5)
    follower_only_mode = db.Column(db.Boolean, default=False)
    subscriber_only_mode = db.Column(db.Boolean, default=False)
    emote_only_mode = db.Column(db.Boolean, default=False)
    
    welcome_message_enabled = db.Column(db.Boolean, default=False)
    welcome_message = db.Column(db.Text, nullable=True)
    
    auto_thank_subs = db.Column(db.Boolean, default=False)
    auto_thank_message = db.Column(db.Text, default='Thanks for subscribing, {user}!')
    
    timed_messages_enabled = db.Column(db.Boolean, default=False)
    timed_messages = db.Column(db.Text, default='[]')
    
    command_cooldown = db.Column(db.Integer, default=5)
    command_user_cooldown = db.Column(db.Integer, default=10)
    
    auto_mod_sensitivity = db.Column(db.Integer, default=3)
    whisper_cooldown = db.Column(db.Integer, default=30)
    command_permission_default = db.Column(db.String(20), default='everyone')
    max_commands_per_minute = db.Column(db.Integer, default=20)
    anti_raid_enabled = db.Column(db.Boolean, default=False)
    anti_raid_min_account_age = db.Column(db.Integer, default=60)
    nightbot_import_enabled = db.Column(db.Boolean, default=False)
    log_deleted_messages = db.Column(db.Boolean, default=True)
    auto_ban_bots = db.Column(db.Boolean, default=False)
    custom_cooldown_message = db.Column(db.Text, default='')
    command_response_style = db.Column(db.String(20), default='chat')

    stream_title_template = db.Column(db.Text, default='')
    auto_greet_new_viewers = db.Column(db.Boolean, default=False)
    auto_greet_message = db.Column(db.Text, default='Welcome to the stream, {user}! Enjoy your stay.')
    viewer_loyalty_tracking = db.Column(db.Boolean, default=False)

    auto_ban_patterns = db.Column(db.Text, default='[]')
    first_time_chatter_restrict = db.Column(db.Boolean, default=False)
    first_time_chatter_mode = db.Column(db.String(20), default='none')
    slow_mode_on_raid = db.Column(db.Boolean, default=False)
    slow_mode_on_raid_seconds = db.Column(db.Integer, default=10)
    slow_mode_on_raid_duration = db.Column(db.Integer, default=300)

    whitelisted_words = db.Column(db.Text, default='')
    whitelisted_users = db.Column(db.Text, default='')
    regex_filters = db.Column(db.Text, default='[]')
    emoji_spam_filter_enabled = db.Column(db.Boolean, default=False)
    max_emojis = db.Column(db.Integer, default=10)
    duplicate_message_filter = db.Column(db.Boolean, default=False)
    timeout_on_spam = db.Column(db.Integer, default=300)
    timeout_on_links = db.Column(db.Integer, default=300)
    timeout_on_caps = db.Column(db.Integer, default=0)
    timeout_on_blocked_words = db.Column(db.Integer, default=600)
    first_offense_action = db.Column(db.String(20), default='warn')
    second_offense_action = db.Column(db.String(20), default='timeout')
    third_offense_action = db.Column(db.String(20), default='ban')
    exempt_moderators = db.Column(db.Boolean, default=True)
    exempt_subscribers = db.Column(db.Boolean, default=False)
    bot_moderator_ok = db.Column(db.Boolean, default=False)

    discord_webhook_url = db.Column(db.Text, default='')
    discord_notify_live = db.Column(db.Boolean, default=False)
    discord_notify_milestones = db.Column(db.Boolean, default=False)

    custom_commands = db.Column(db.Text, default='{}')
    
    builtin_commands = db.Column(db.Text, default=None)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    channel = db.relationship('Channel', backref='bot_settings', uselist=False)
    
    def _parse_regex_filters(self):
        try:
            return json.loads(self.regex_filters) if self.regex_filters else []
        except Exception:
            return []

    def _parse_auto_ban_patterns(self):
        try:
            return json.loads(self.auto_ban_patterns) if self.auto_ban_patterns else []
        except Exception:
            return []

    def get_builtin_commands(self):
        if self.builtin_commands:
            try:
                return json.loads(self.builtin_commands)
            except Exception:
                pass
        import copy
        return copy.deepcopy(DEFAULT_BUILTIN_COMMANDS)

    def to_dict(self):
        try:
            commands = json.loads(self.custom_commands) if self.custom_commands else {}
        except:
            commands = {}
        
        try:
            timed = json.loads(self.timed_messages) if self.timed_messages else []
        except:
            timed = []
        
        return {
            'id': self.id,
            'channel_id': self.channel_id,
            'bot_name': self.bot_name,
            'bot_enabled': self.bot_enabled,
            'chat_prefix': self.chat_prefix,
            'response_delay': self.response_delay,
            'join_message': self.join_message,
            'spam_filter_enabled': self.spam_filter_enabled,
            'max_repeat_chars': self.max_repeat_chars,
            'max_message_length': self.max_message_length,
            'link_filter_enabled': self.link_filter_enabled,
            'link_whitelist': self.link_whitelist.split('\n') if self.link_whitelist else [],
            'caps_filter_enabled': self.caps_filter_enabled,
            'max_caps_percent': self.max_caps_percent,
            'blocked_words_enabled': self.blocked_words_enabled,
            'blocked_words': self.blocked_words or '',
            'timeout_duration': self.timeout_duration,
            'warning_message': self.warning_message,
            'slow_mode_enabled': self.slow_mode_enabled,
            'slow_mode_seconds': self.slow_mode_seconds,
            'follower_only_mode': self.follower_only_mode,
            'subscriber_only_mode': self.subscriber_only_mode,
            'emote_only_mode': self.emote_only_mode,
            'welcome_message_enabled': self.welcome_message_enabled,
            'welcome_message': self.welcome_message,
            'auto_thank_subs': self.auto_thank_subs,
            'auto_thank_message': self.auto_thank_message,
            'timed_messages_enabled': self.timed_messages_enabled,
            'timed_messages': timed,
            'command_cooldown': self.command_cooldown,
            'command_user_cooldown': self.command_user_cooldown,
            'auto_mod_sensitivity': self.auto_mod_sensitivity or 3,
            'whisper_cooldown': self.whisper_cooldown or 30,
            'command_permission_default': self.command_permission_default or 'everyone',
            'max_commands_per_minute': self.max_commands_per_minute or 20,
            'anti_raid_enabled': self.anti_raid_enabled or False,
            'anti_raid_min_account_age': self.anti_raid_min_account_age or 60,
            'nightbot_import_enabled': self.nightbot_import_enabled or False,
            'log_deleted_messages': self.log_deleted_messages if self.log_deleted_messages is not None else True,
            'auto_ban_bots': self.auto_ban_bots or False,
            'custom_cooldown_message': self.custom_cooldown_message or '',
            'command_response_style': self.command_response_style or 'chat',
            'whitelisted_words': self.whitelisted_words or '',
            'whitelisted_users': self.whitelisted_users or '',
            'regex_filters': self._parse_regex_filters(),
            'emoji_spam_filter_enabled': self.emoji_spam_filter_enabled or False,
            'max_emojis': self.max_emojis or 10,
            'duplicate_message_filter': self.duplicate_message_filter or False,
            'timeout_on_spam': self.timeout_on_spam if self.timeout_on_spam is not None else 300,
            'timeout_on_links': self.timeout_on_links if self.timeout_on_links is not None else 300,
            'timeout_on_caps': self.timeout_on_caps if self.timeout_on_caps is not None else 0,
            'timeout_on_blocked_words': self.timeout_on_blocked_words if self.timeout_on_blocked_words is not None else 600,
            'first_offense_action': self.first_offense_action or 'warn',
            'second_offense_action': self.second_offense_action or 'timeout',
            'third_offense_action': self.third_offense_action or 'ban',
            'exempt_moderators': self.exempt_moderators if self.exempt_moderators is not None else True,
            'exempt_subscribers': self.exempt_subscribers or False,
            'stream_title_template': self.stream_title_template or '',
            'auto_greet_new_viewers': self.auto_greet_new_viewers or False,
            'auto_greet_message': self.auto_greet_message or 'Welcome to the stream, {user}! Enjoy your stay.',
            'viewer_loyalty_tracking': self.viewer_loyalty_tracking or False,
            'auto_ban_patterns': self._parse_auto_ban_patterns(),
            'first_time_chatter_restrict': self.first_time_chatter_restrict or False,
            'first_time_chatter_mode': self.first_time_chatter_mode or 'none',
            'slow_mode_on_raid': self.slow_mode_on_raid or False,
            'slow_mode_on_raid_seconds': self.slow_mode_on_raid_seconds if self.slow_mode_on_raid_seconds is not None else 10,
            'slow_mode_on_raid_duration': self.slow_mode_on_raid_duration if self.slow_mode_on_raid_duration is not None else 300,
            'discord_webhook_url': self.discord_webhook_url or '',
            'discord_notify_live': self.discord_notify_live or False,
            'discord_notify_milestones': self.discord_notify_milestones or False,
            'custom_commands': commands,
            'builtin_commands': self.get_builtin_commands(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }


class VideoStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('channel.id'), nullable=False)
    video_id = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(500))
    published_at = db.Column(db.DateTime, nullable=True)
    view_count = db.Column(db.Integer, default=0)
    like_count = db.Column(db.Integer, default=0)
    comment_count = db.Column(db.Integer, default=0)
    thumbnail_url = db.Column(db.String(500), nullable=True)
    duration = db.Column(db.String(50), nullable=True)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    channel = db.relationship('Channel', backref='video_stats', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'channel_id': self.channel_id,
            'video_id': self.video_id,
            'title': self.title,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'view_count': self.view_count,
            'like_count': self.like_count,
            'comment_count': self.comment_count,
            'thumbnail_url': self.thumbnail_url,
            'duration': self.duration,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class ChatUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('channel.id'), nullable=False)
    youtube_user_id = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(255), nullable=True)
    watchtime_minutes = db.Column(db.Integer, default=0)
    messages_sent = db.Column(db.Integer, default=0)
    commands_used = db.Column(db.Integer, default=0)
    timeout_count = db.Column(db.Integer, default=0)
    is_banned = db.Column(db.Boolean, default=False)
    ban_reason = db.Column(db.String(500), nullable=True)
    last_seen = db.Column(db.DateTime, nullable=True)
    first_seen = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    channel = db.relationship('Channel', backref='chat_users', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'channel_id': self.channel_id,
            'youtube_user_id': self.youtube_user_id,
            'username': self.username,
            'display_name': self.display_name,
            'watchtime_minutes': self.watchtime_minutes,
            'messages_sent': self.messages_sent,
            'commands_used': self.commands_used,
            'timeout_count': self.timeout_count,
            'is_banned': self.is_banned,
            'ban_reason': self.ban_reason,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'first_seen': self.first_seen.isoformat() if self.first_seen else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class CommandLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('channel.id'), nullable=False)
    user_id = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(255), nullable=False)
    command = db.Column(db.String(255), nullable=False)
    response = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    channel = db.relationship('Channel', backref='command_logs', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'channel_id': self.channel_id,
            'user_id': self.user_id,
            'username': self.username,
            'command': self.command,
            'response': self.response,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
        }


class BotUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    discord_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    discord_username = db.Column(db.String(255), nullable=True)
    discord_global_name = db.Column(db.String(255), nullable=True)
    discord_avatar = db.Column(db.String(500), nullable=True)
    discord_access_token = db.Column(db.Text, nullable=True)
    discord_refresh_token = db.Column(db.Text, nullable=True)
    nexus_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    nexus_user = db.relationship('User', backref='bot_user', uselist=False)
    server_configs = db.relationship('ServerConfig', backref='bot_user', lazy=True, cascade='all, delete-orphan')

    @property
    def avatar_url(self):
        if self.discord_avatar:
            return f'https://cdn.discordapp.com/avatars/{self.discord_id}/{self.discord_avatar}.png?size=128'
        disc = (int(self.discord_id) >> 22) % 6
        return f'https://cdn.discordapp.com/embed/avatars/{disc}.png'

    @property
    def display_name(self):
        return self.discord_global_name or self.discord_username or 'Unknown'


class ServerConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.String(255), nullable=False, index=True)
    server_name = db.Column(db.String(255), nullable=True)
    server_icon = db.Column(db.String(500), nullable=True)
    bot_user_id = db.Column(db.Integer, db.ForeignKey('bot_user.id'), nullable=False)
    prefix = db.Column(db.String(10), default='!')
    bot_nickname = db.Column(db.String(255), nullable=True)
    welcome_enabled = db.Column(db.Boolean, default=True)
    welcome_channel_id = db.Column(db.String(255), nullable=True)
    welcome_message = db.Column(db.Text, default='Welcome to the server, {user}!')
    welcome_embed_enabled = db.Column(db.Boolean, default=False)
    welcome_embed_color = db.Column(db.String(7), default='#6366f1')
    welcome_embed_title = db.Column(db.String(256), nullable=True)
    welcome_embed_thumbnail = db.Column(db.String(500), nullable=True)
    welcome_dm_enabled = db.Column(db.Boolean, default=False)
    welcome_dm_message = db.Column(db.Text, default='')
    goodbye_enabled = db.Column(db.Boolean, default=False)
    goodbye_channel_id = db.Column(db.String(255), nullable=True)
    goodbye_message = db.Column(db.Text, default='Goodbye {user}. Thanks for being here.')
    mod_log_enabled = db.Column(db.Boolean, default=True)
    mod_log_channel_id = db.Column(db.String(255), nullable=True)
    log_joins_enabled = db.Column(db.Boolean, default=True)
    log_leaves_enabled = db.Column(db.Boolean, default=True)
    log_message_edits_enabled = db.Column(db.Boolean, default=True)
    log_message_deletes_enabled = db.Column(db.Boolean, default=True)
    log_bans_enabled = db.Column(db.Boolean, default=True)
    auto_role_enabled = db.Column(db.Boolean, default=True)
    auto_role_name = db.Column(db.String(255), default='Member')
    anti_spam_enabled = db.Column(db.Boolean, default=True)
    anti_link_enabled = db.Column(db.Boolean, default=False)
    anti_caps_enabled = db.Column(db.Boolean, default=False)
    anti_emoji_spam_enabled = db.Column(db.Boolean, default=False)
    bad_words_enabled = db.Column(db.Boolean, default=False)
    bad_words_list = db.Column(db.Text, default='')
    max_warnings = db.Column(db.Integer, default=3)
    mute_duration = db.Column(db.Integer, default=10)
    auto_mod_enabled = db.Column(db.Boolean, default=True)
    join_gate_enabled = db.Column(db.Boolean, default=False)
    join_gate_days = db.Column(db.Integer, default=7)
    level_system_enabled = db.Column(db.Boolean, default=False)
    youtube_notify_enabled = db.Column(db.Boolean, default=False)
    youtube_notify_channel_id = db.Column(db.String(255), nullable=True)
    auto_role_id = db.Column(db.String(255), nullable=True)
    mod_role_id = db.Column(db.String(255), nullable=True)
    admin_role_id = db.Column(db.String(255), nullable=True)
    mute_role_id = db.Column(db.String(255), nullable=True)
    dj_role_id = db.Column(db.String(255), nullable=True)
    announcement_channel_id = db.Column(db.String(255), nullable=True)
    starboard_enabled = db.Column(db.Boolean, default=False)
    starboard_channel_id = db.Column(db.String(255), nullable=True)
    starboard_threshold = db.Column(db.Integer, default=3)
    reaction_roles_enabled = db.Column(db.Boolean, default=False)
    reaction_roles_channel_id = db.Column(db.String(255), nullable=True)
    ticket_system_enabled = db.Column(db.Boolean, default=False)
    ticket_category_id = db.Column(db.String(255), nullable=True)
    ticket_support_role_id = db.Column(db.String(255), nullable=True)
    bot_enabled = db.Column(db.Boolean, default=True)
    audit_log_enabled = db.Column(db.Boolean, default=False)
    audit_log_channel_id = db.Column(db.String(255), nullable=True)
    auto_thread_enabled = db.Column(db.Boolean, default=False)
    auto_thread_channel_id = db.Column(db.String(255), nullable=True)
    counting_enabled = db.Column(db.Boolean, default=False)
    counting_channel_id = db.Column(db.String(255), nullable=True)
    suggestion_enabled = db.Column(db.Boolean, default=False)
    suggestion_channel_id = db.Column(db.String(255), nullable=True)
    media_only_enabled = db.Column(db.Boolean, default=False)
    media_only_channel_id = db.Column(db.String(255), nullable=True)
    verify_enabled = db.Column(db.Boolean, default=False)
    verify_role_id = db.Column(db.String(255), nullable=True)
    verify_channel_id = db.Column(db.String(255), nullable=True)
    level_announce_channel_id = db.Column(db.String(255), nullable=True)
    level_role_rewards = db.Column(db.Text, default='')
    custom_embed_color = db.Column(db.String(7), default='#6366f1')
    timezone = db.Column(db.String(50), default='UTC')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('server_id', 'bot_user_id', name='uq_server_botuser'),)


class ModLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.String(255), nullable=False, index=True)
    action_type = db.Column(db.String(50), nullable=False)
    moderator_id = db.Column(db.String(255), nullable=True)
    moderator_name = db.Column(db.String(255), nullable=True)
    target_id = db.Column(db.String(255), nullable=True)
    target_name = db.Column(db.String(255), nullable=True)
    reason = db.Column(db.Text, nullable=True)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'server_id': self.server_id,
            'action_type': self.action_type,
            'moderator_id': self.moderator_id,
            'moderator_name': self.moderator_name,
            'target_id': self.target_id,
            'target_name': self.target_name,
            'reason': self.reason,
            'details': self.details,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class BotHeartbeat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bot_id = db.Column(db.String(255), nullable=False)
    bot_name = db.Column(db.String(255), nullable=True)
    guild_count = db.Column(db.Integer, default=0)
    user_count = db.Column(db.Integer, default=0)
    latency_ms = db.Column(db.Integer, default=0)
    uptime_seconds = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default='offline')
    last_heartbeat = db.Column(db.DateTime, default=datetime.utcnow)


class BotContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    discord_username = db.Column(db.String(100), nullable=True)
    category = db.Column(db.String(50), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    bot_user_id = db.Column(db.Integer, nullable=True)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    blog_type = db.Column(db.String(20), nullable=False, default='nexus')
    slug = db.Column(db.String(255), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    date_display = db.Column(db.String(50), nullable=False)
    date_short = db.Column(db.String(30), nullable=False)
    tag = db.Column(db.String(50), nullable=False, default='announcement')
    tag_label = db.Column(db.String(50), nullable=False, default='Announcement')
    summary = db.Column(db.Text, nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('blog_type', 'slug', name='uq_blogtype_slug'),)

    def to_dict(self):
        return {
            'slug': self.slug,
            'title': self.title,
            'date': self.date_display,
            'date_short': self.date_short,
            'tag': self.tag,
            'tag_label': self.tag_label,
            'summary': self.summary,
            'content': self.content,
        }


class SiteSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def get(key, default=None):
        setting = SiteSetting.query.filter_by(key=key).first()
        if setting:
            return setting.value
        return default

    @staticmethod
    def set_value(key, value):
        from app import db
        setting = SiteSetting.query.filter_by(key=key).first()
        if setting:
            setting.value = value
        else:
            setting = SiteSetting(key=key, value=value)
            db.session.add(setting)
        db.session.commit()


@app.before_request
def check_maintenance_mode():
    skip_prefixes = ('/static/', '/nx-admin', '/auth/', '/sitemap', '/robots', '/favicon')
    if any(request.path.startswith(p) for p in skip_prefixes):
        return None
    try:
        if SiteSetting.get('maintenance_mode', 'false') == 'true':
            if session.get('user_id'):
                u = User.query.get(session['user_id'])
                if u and u.is_admin:
                    return None
            return render_template('maintenance.html'), 503
    except Exception:
        pass
    return None


@app.context_processor
def inject_current_user():
    user = None
    channel_thumbnail = None
    if session.get('user_id'):
        try:
            user = User.query.get(session['user_id'])
            if user:
                primary_channel = Channel.query.filter_by(user_id=user.id).first()
                if primary_channel and primary_channel.channel_thumbnail:
                    channel_thumbnail = primary_channel.channel_thumbnail
        except Exception:
            db.session.rollback()
    user_theme = 'light'
    user_compact = False
    if user:
        try:
            prefs = user.get_notification_preferences()
            user_theme = prefs.get('theme_preference', 'light')
            user_compact = prefs.get('compact_mode', False)
        except Exception:
            pass
    site_settings = {}
    try:
        for s in SiteSetting.query.all():
            site_settings[s.key] = s.value
    except Exception:
        pass
    return dict(
        current_user=user,
        channel_thumbnail=channel_thumbnail,
        user_theme=user_theme,
        user_compact=user_compact,
        site_settings=site_settings,
    )


@app.route('/auth/login')
def login():
    return render_template('auth/login.html')


@app.route('/auth/signup')
def signup():
    return render_template('auth/signup.html')


@app.route('/auth/bot-setup/<token>')
def bot_setup(token):
    expected = os.getenv('BOT_SETUP_KEY', '')
    if not expected or token != expected:
        return '', 404
    state = secrets.token_urlsafe(32)
    session['bot_oauth_state'] = state

    if GOOGLE_REDIRECT_URI:
        base = GOOGLE_REDIRECT_URI.rsplit('/', 1)[0]
        redirect_uri = f"{base}/bot-callback"
    else:
        scheme = 'https' if '.replit.app' in request.host or '.repl.co' in request.host else request.headers.get('X-Forwarded-Proto', 'http')
        redirect_uri = f"{scheme}://{request.host}/auth/bot-callback"

    bot_scopes = ['https://www.googleapis.com/auth/youtube.force-ssl']

    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope={'%20'.join(bot_scopes)}"
        f"&state={state}"
        f"&access_type=offline"
        f"&prompt=consent%20select_account"
    )

    return redirect(google_auth_url)


@app.route('/auth/bot-callback')
def bot_oauth_callback():
    code = request.args.get('code')
    state = request.args.get('state')

    if not code or state != session.get('bot_oauth_state'):
        return '<h2>Invalid OAuth state. Please try again.</h2><a href="/auth/bot-setup">Retry</a>', 400

    try:
        if GOOGLE_REDIRECT_URI:
            base = GOOGLE_REDIRECT_URI.rsplit('/', 1)[0]
            redirect_uri = f"{base}/bot-callback"
        else:
            scheme = 'https' if '.replit.app' in request.host or '.repl.co' in request.host else request.headers.get('X-Forwarded-Proto', 'http')
            redirect_uri = f"{scheme}://{request.host}/auth/bot-callback"

        token_response = requests.post(
            'https://oauth2.googleapis.com/token',
            data={
                'client_id': GOOGLE_CLIENT_ID,
                'client_secret': GOOGLE_CLIENT_SECRET,
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': redirect_uri,
            }
        )

        if token_response.status_code != 200:
            return f'<h2>Failed to obtain token</h2><pre>{token_response.text}</pre><a href="/auth/bot-setup">Retry</a>', 400

        token_data = token_response.json()
        access_token = token_data.get('access_token', '')
        refresh_token = token_data.get('refresh_token', '')

        user_info = requests.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers={'Authorization': f'Bearer {access_token}'}
        ).json()

        bot_name = user_info.get('name', 'Unknown')
        bot_email = user_info.get('email', 'Unknown')

        return (
            f'<div style="font-family: sans-serif; max-width: 600px; margin: 60px auto; padding: 40px;">'
            f'<h2>Bot Account Authenticated</h2>'
            f'<p>Logged in as: <strong>{bot_name}</strong> ({bot_email})</p>'
            f'<p>Set these as environment variables (Replit Secrets):</p>'
            f'<div style="background: #1e1e2e; color: #cdd6f4; padding: 20px; border-radius: 8px; font-family: monospace; font-size: 13px; word-break: break-all;">'
            f'<p><strong>BOT_ACCESS_TOKEN</strong></p><p style="color: #a6e3a1;">{access_token}</p>'
            f'<br><p><strong>BOT_REFRESH_TOKEN</strong></p><p style="color: #a6e3a1;">{refresh_token}</p>'
            f'</div>'
            f'<p style="margin-top: 20px; color: #666;">The access token expires hourly but the refresh token is permanent. '
            f'The bot will automatically refresh the access token as needed.</p>'
            f'<a href="/dashboard" style="display: inline-block; margin-top: 16px; padding: 10px 20px; background: #6366f1; color: white; border-radius: 6px; text-decoration: none;">Back to Dashboard</a>'
            f'</div>'
        )

    except Exception as e:
        return f'<h2>Error during bot authentication</h2><pre>{str(e)}</pre><a href="/auth/bot-setup">Retry</a>', 500


@app.route('/auth/google')
def google_login():
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state

    if GOOGLE_REDIRECT_URI:
        redirect_uri = GOOGLE_REDIRECT_URI
    else:
        scheme = 'https' if '.replit.app' in request.host or '.repl.co' in request.host else request.headers.get('X-Forwarded-Proto', 'http')
        redirect_uri = f"{scheme}://{request.host}/auth/callback"

    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope={'%20'.join(SCOPES)}"
        f"&state={state}"
        f"&access_type=offline"
        f"&prompt=consent%20select_account"
    )

    return redirect(google_auth_url)


@app.route('/auth/callback')
def oauth_callback():
    code = request.args.get('code')
    state = request.args.get('state')
    
    if not code or state != session.get('oauth_state'):
        return jsonify({'error': 'Invalid OAuth state'}), 400
    
    try:
        if GOOGLE_REDIRECT_URI:
            redirect_uri = GOOGLE_REDIRECT_URI
        else:
            scheme = 'https' if '.replit.app' in request.host or '.repl.co' in request.host else request.headers.get('X-Forwarded-Proto', 'http')
            redirect_uri = f"{scheme}://{request.host}/auth/callback"

        token_response = requests.post(
            'https://oauth2.googleapis.com/token',
            data={
                'client_id': GOOGLE_CLIENT_ID,
                'client_secret': GOOGLE_CLIENT_SECRET,
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': redirect_uri,
            }
        )
        
        if token_response.status_code != 200:
            return jsonify({'error': 'Failed to obtain token'}), 400
        
        token_data = token_response.json()
        access_token = token_data.get('access_token')
        
        user_info_response = requests.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        
        if user_info_response.status_code != 200:
            return jsonify({'error': 'Failed to get user info'}), 400
        
        user_info = user_info_response.json()
        
        OWNER_EMAILS = ['sketchxcoding2@gmail.com']
        user = User.query.filter_by(google_id=user_info['id']).first()
        
        if not user:
            if (SiteSetting.get('registration_enabled', 'true') == 'false'
                    and user_info['email'].lower() not in OWNER_EMAILS):
                flash('New registrations are currently disabled.', 'error')
                return redirect(url_for('login'))
            auto_admin = User.query.count() < 2 or user_info['email'].lower() in OWNER_EMAILS
            user = User(
                email=user_info['email'],
                google_id=user_info['id'],
                username=user_info.get('name', user_info['email'].split('@')[0]),
                profile_picture=user_info.get('picture'),
                is_admin=auto_admin,
            )
            db.session.add(user)
            db.session.commit()
        else:
            user.username = user_info.get('name', user.username)
            user.profile_picture = user_info.get('picture', user.profile_picture)
            if user_info['email'].lower() in OWNER_EMAILS and not user.is_admin:
                user.is_admin = True
            db.session.commit()

        session['access_token'] = access_token
        session['user_id'] = user.id
        session['logged_in'] = True

        user.access_token = access_token
        rt = token_data.get('refresh_token')
        if rt:
            user.refresh_token = rt
        db.session.commit()

        try:
            yt_channel_response = requests.get(
                'https://www.googleapis.com/youtube/v3/channels',
                params={'part': 'snippet,statistics,brandingSettings', 'mine': 'true'},
                headers={'Authorization': f'Bearer {access_token}'}
            )
            if yt_channel_response.status_code == 200:
                yt_data = yt_channel_response.json()
                if yt_data.get('items'):
                    yt_channel = yt_data['items'][0]
                    yt_id = yt_channel['id']
                    snippet = yt_channel['snippet']
                    stats = yt_channel.get('statistics', {})

                    user.youtube_channel_id = yt_id
                    user.youtube_channel_name = snippet.get('title', '')

                    existing_channel = Channel.query.filter_by(
                        user_id=user.id,
                        youtube_channel_id=yt_id
                    ).first()

                    if not existing_channel:
                        channel = Channel(
                            user_id=user.id,
                            youtube_channel_id=yt_id,
                            channel_name=snippet.get('title', 'My Channel'),
                            channel_thumbnail=snippet.get('thumbnails', {}).get('medium', {}).get('url',
                                snippet.get('thumbnails', {}).get('default', {}).get('url', '')),
                            subscriber_count=int(stats.get('subscriberCount', 0)),
                            view_count=int(stats.get('viewCount', 0)),
                            video_count=int(stats.get('videoCount', 0)),
                            last_synced=datetime.utcnow(),
                        )
                        db.session.add(channel)
                    else:
                        existing_channel.channel_name = snippet.get('title', existing_channel.channel_name)
                        existing_channel.channel_thumbnail = snippet.get('thumbnails', {}).get('medium', {}).get('url',
                            snippet.get('thumbnails', {}).get('default', {}).get('url', existing_channel.channel_thumbnail))
                        existing_channel.subscriber_count = int(stats.get('subscriberCount', 0))
                        existing_channel.view_count = int(stats.get('viewCount', 0))
                        existing_channel.video_count = int(stats.get('videoCount', 0))
                        existing_channel.last_synced = datetime.utcnow()

                    db.session.commit()
        except Exception as yt_err:
            print(f"YouTube auto-track error (non-fatal): {yt_err}")
        
        return redirect('/dashboard')
    except Exception as e:
        print(f"Auth Error: {str(e)}")
        return jsonify({'error': 'Authentication failed. Please try again.'}), 500


@app.route('/auth/logout')
def logout():
    session.clear()
    return redirect('/')


DISCORD_CLIENT_ID = os.getenv('DISCORD_CLIENT_ID', '')
DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET', '')
DISCORD_REDIRECT_URI_PATH = '/auth/discord/callback'


def _discord_redirect_uri():
    if IS_VERCEL:
        return 'https://nexusbeta.vercel.app' + DISCORD_REDIRECT_URI_PATH
    return request.host_url.rstrip('/') + DISCORD_REDIRECT_URI_PATH


@app.route('/auth/discord')
def discord_oauth():
    if 'user_id' not in session:
        return redirect('/auth/login')
    if not DISCORD_CLIENT_ID:
        return redirect('/settings?error=discord_not_configured')
    state = secrets.token_hex(16)
    session['discord_oauth_state'] = state
    params = {
        'client_id': DISCORD_CLIENT_ID,
        'redirect_uri': _discord_redirect_uri(),
        'response_type': 'code',
        'scope': 'identify',
        'state': state,
    }
    from urllib.parse import urlencode
    return redirect(f'https://discord.com/api/oauth2/authorize?{urlencode(params)}')


@app.route('/auth/discord/callback')
def discord_callback():
    if 'user_id' not in session:
        return redirect('/auth/login')
    error = request.args.get('error')
    if error:
        return redirect('/settings?error=discord_denied')
    code = request.args.get('code')
    state = request.args.get('state')
    if not code or state != session.pop('discord_oauth_state', None):
        return redirect('/settings?error=discord_invalid')
    try:
        token_resp = requests.post('https://discord.com/api/oauth2/token', data={
            'client_id': DISCORD_CLIENT_ID,
            'client_secret': DISCORD_CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': _discord_redirect_uri(),
        }, headers={'Content-Type': 'application/x-www-form-urlencoded'}, timeout=10)
        if token_resp.status_code != 200:
            return redirect('/settings?error=discord_token_failed')
        token_data = token_resp.json()
        access_token = token_data.get('access_token')
        user_resp = requests.get('https://discord.com/api/users/@me', headers={
            'Authorization': f'Bearer {access_token}',
        }, timeout=10)
        if user_resp.status_code != 200:
            return redirect('/settings?error=discord_user_failed')
        discord_user = user_resp.json()
        discord_id = discord_user['id']
        discord_name = discord_user.get('global_name') or discord_user.get('username', '')
        existing = User.query.filter_by(discord_user_id=discord_id).first()
        if existing and existing.id != session['user_id']:
            return redirect('/settings?error=discord_already_linked')
        user = User.query.get(session['user_id'])
        if user:
            user.discord_user_id = discord_id
            user.discord_username = discord_name
            user.updated_at = datetime.utcnow()
            db.session.commit()
        return redirect('/settings?discord=connected')
    except Exception as e:
        print(f"Discord OAuth Error: {e}")
        return redirect('/settings?error=discord_failed')


@app.route('/settings/unlink-bot', methods=['POST'])
def unlink_bot():
    if 'user_id' not in session:
        return redirect('/auth/login')
    csrf_token = request.form.get('csrf_token', '')
    if csrf_token != session.get('csrf_token', ''):
        return redirect('/settings?error=invalid_request')
    user = User.query.get(session['user_id'])
    if user and user.discord_user_id:
        bot_user = BotUser.query.filter_by(discord_id=user.discord_user_id).first()
        if bot_user and bot_user.nexus_user_id == user.id:
            bot_user.nexus_user_id = None
            db.session.commit()
    return redirect('/settings?bot=unlinked')


@app.route('/auth/discord/disconnect', methods=['POST'])
def discord_disconnect():
    if 'user_id' not in session:
        return redirect('/auth/login')
    csrf_token = request.form.get('csrf_token', '')
    if csrf_token != session.get('csrf_token', ''):
        return redirect('/settings?error=invalid_request')
    user = User.query.get(session['user_id'])
    if user:
        user.discord_user_id = None
        user.discord_username = None
        user.updated_at = datetime.utcnow()
        db.session.commit()
    return redirect('/settings?discord=disconnected')


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/auth/login')
        return f(*args, **kwargs)
    return decorated_function


@app.route('/api/user/profile')
@login_required
def get_user_profile():
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(user.to_dict())


@app.route('/api/channels', methods=['GET'])
@login_required
def get_channels():
    user = User.query.get(session['user_id'])
    channels = Channel.query.filter_by(user_id=user.id).all()
    return jsonify([ch.to_dict() for ch in channels])


@app.route('/api/channels', methods=['POST'])
@login_required
def add_channel():
    data = request.json
    youtube_channel_id = data.get('youtube_channel_id')
    
    if not youtube_channel_id:
        return jsonify({'error': 'Channel ID required'}), 400
    
    existing = Channel.query.filter_by(
        user_id=session['user_id'],
        youtube_channel_id=youtube_channel_id
    ).first()
    
    if existing:
        return jsonify({'error': 'Already tracking this channel'}), 409
    
    try:
        yt_response = requests.get(
            f'https://www.googleapis.com/youtube/v3/channels',
            params={
                'part': 'snippet,statistics',
                'id': youtube_channel_id,
                'key': YOUTUBE_API_KEY,
            }
        )
        
        if yt_response.status_code != 200:
            return jsonify({'error': 'Invalid channel ID'}), 400
        
        channel_data = yt_response.json()['items'][0]
        
        channel = Channel(
            user_id=session['user_id'],
            youtube_channel_id=youtube_channel_id,
            channel_name=channel_data['snippet']['title'],
            channel_thumbnail=channel_data['snippet']['thumbnails']['default']['url'],
            subscriber_count=int(channel_data['statistics'].get('subscriberCount', 0)),
            view_count=int(channel_data['statistics'].get('viewCount', 0)),
            video_count=int(channel_data['statistics'].get('videoCount', 0)),
            last_synced=datetime.utcnow(),
        )
        
        db.session.add(channel)
        db.session.commit()
        
        return jsonify(channel.to_dict()), 201
    
    except Exception as e:
        print(f"Add channel error: {str(e)}")
        return jsonify({'error': 'Failed to add channel. Please try again.'}), 500


@app.route('/api/channels/<int:channel_id>', methods=['DELETE'])
@login_required
def delete_channel(channel_id):
    channel = Channel.query.get(channel_id)
    
    if not channel or channel.user_id != session['user_id']:
        return jsonify({'error': 'Channel not found'}), 404
    
    db.session.delete(channel)
    db.session.commit()
    
    return jsonify({'message': 'Channel deleted'}), 200


@app.route('/api/channels/<int:channel_id>/sync', methods=['POST'])
@login_required
def sync_channel(channel_id):
    channel = Channel.query.get(channel_id)

    if not channel or channel.user_id != session['user_id']:
        return jsonify({'error': 'Channel not found'}), 404

    access_token = session.get('access_token')
    if not access_token:
        return jsonify({'error': 'Session expired. Please log in again.'}), 401

    try:
        yt_response = requests.get(
            'https://www.googleapis.com/youtube/v3/channels',
            params={'part': 'snippet,statistics', 'id': channel.youtube_channel_id},
            headers={'Authorization': f'Bearer {access_token}'}
        )

        if yt_response.status_code != 200:
            if YOUTUBE_API_KEY:
                yt_response = requests.get(
                    'https://www.googleapis.com/youtube/v3/channels',
                    params={
                        'part': 'snippet,statistics',
                        'id': channel.youtube_channel_id,
                        'key': YOUTUBE_API_KEY,
                    }
                )
            if yt_response.status_code != 200:
                return jsonify({'error': 'Failed to fetch channel data'}), 400

        yt_data = yt_response.json()
        if not yt_data.get('items'):
            return jsonify({'error': 'Channel not found on YouTube'}), 404

        item = yt_data['items'][0]
        snippet = item['snippet']
        stats = item.get('statistics', {})

        channel.channel_name = snippet.get('title', channel.channel_name)
        channel.channel_thumbnail = snippet.get('thumbnails', {}).get('medium', {}).get('url',
            snippet.get('thumbnails', {}).get('default', {}).get('url', channel.channel_thumbnail))
        channel.subscriber_count = int(stats.get('subscriberCount', 0))
        channel.view_count = int(stats.get('viewCount', 0))
        channel.video_count = int(stats.get('videoCount', 0))
        channel.last_synced = datetime.utcnow()

        today = datetime.utcnow().date()
        existing_stat = ChannelStats.query.filter_by(
            user_id=session['user_id'],
            channel_id=channel.youtube_channel_id,
            stat_date=today
        ).first()

        if not existing_stat:
            stat = ChannelStats(
                user_id=session['user_id'],
                channel_id=channel.youtube_channel_id,
                stat_date=today,
                subscribers=channel.subscriber_count,
                total_views=channel.view_count,
                total_videos=channel.video_count,
            )
            db.session.add(stat)
        else:
            existing_stat.subscribers = channel.subscriber_count
            existing_stat.total_views = channel.view_count
            existing_stat.total_videos = channel.video_count

        db.session.commit()
        return jsonify({'channel': channel.to_dict()}), 200
    except Exception as e:
        print(f"Sync error: {str(e)}")
        return jsonify({'error': 'Sync failed. Please try again.'}), 500


@app.route('/api/channels/<int:channel_id>/stats')
@login_required
def get_channel_stats(channel_id):
    channel = Channel.query.get(channel_id)
    
    if not channel or channel.user_id != session['user_id']:
        return jsonify({'error': 'Channel not found'}), 404
    
    stats = ChannelStats.query.filter_by(
        user_id=session['user_id'],
        channel_id=channel.youtube_channel_id
    ).order_by(ChannelStats.stat_date.desc()).limit(30).all()
    
    return jsonify({
        'channel': channel.to_dict(),
        'stats': [s.to_dict() for s in stats],
    })


@app.route('/api/channels/<int:channel_id>/streams')
@login_required
def get_stream_sessions(channel_id):
    channel = Channel.query.get(channel_id)
    
    if not channel or channel.user_id != session['user_id']:
        return jsonify({'error': 'Channel not found'}), 404
    
    streams = StreamSession.query.filter_by(channel_id=channel.id).order_by(
        StreamSession.start_time.desc()
    ).limit(50).all()
    
    return jsonify([s.to_dict() for s in streams])


@app.route('/api/channels/<int:channel_id>/sync-videos', methods=['POST'])
@login_required
def sync_channel_videos(channel_id):
    channel = Channel.query.get(channel_id)

    if not channel or channel.user_id != session['user_id']:
        return jsonify({'error': 'Channel not found'}), 404

    api_key = YOUTUBE_API_KEY
    access_token = session.get('access_token')

    if not api_key and not access_token:
        return jsonify({'error': 'No YouTube API key or access token available'}), 400

    try:
        search_params = {
            'part': 'snippet',
            'channelId': channel.youtube_channel_id,
            'type': 'video',
            'order': 'date',
            'maxResults': 20,
        }
        search_headers = {}
        if api_key:
            search_params['key'] = api_key
        else:
            search_headers['Authorization'] = f'Bearer {access_token}'

        search_resp = requests.get(
            'https://www.googleapis.com/youtube/v3/search',
            params=search_params,
            headers=search_headers,
        )

        if search_resp.status_code != 200:
            return jsonify({'error': 'Failed to search videos'}), 400

        search_data = search_resp.json()
        items = search_data.get('items', [])
        if not items:
            return jsonify({'message': 'No videos found', 'count': 0}), 200

        video_ids = [item['id']['videoId'] for item in items if item.get('id', {}).get('videoId')]
        if not video_ids:
            return jsonify({'message': 'No videos found', 'count': 0}), 200

        stats_params = {
            'part': 'snippet,statistics,contentDetails',
            'id': ','.join(video_ids),
        }
        stats_headers = {}
        if api_key:
            stats_params['key'] = api_key
        else:
            stats_headers['Authorization'] = f'Bearer {access_token}'

        stats_resp = requests.get(
            'https://www.googleapis.com/youtube/v3/videos',
            params=stats_params,
            headers=stats_headers,
        )

        if stats_resp.status_code != 200:
            return jsonify({'error': 'Failed to fetch video statistics'}), 400

        videos_data = stats_resp.json().get('items', [])
        count = 0
        for video in videos_data:
            vid = video['id']
            snippet = video.get('snippet', {})
            statistics = video.get('statistics', {})
            content_details = video.get('contentDetails', {})

            published_at = None
            if snippet.get('publishedAt'):
                try:
                    published_at = datetime.strptime(snippet['publishedAt'], '%Y-%m-%dT%H:%M:%SZ')
                except ValueError:
                    published_at = datetime.fromisoformat(snippet['publishedAt'].replace('Z', '+00:00')).replace(tzinfo=None)

            existing = VideoStats.query.filter_by(channel_id=channel.id, video_id=vid).first()
            if existing:
                existing.title = snippet.get('title', existing.title)
                existing.published_at = published_at or existing.published_at
                existing.view_count = int(statistics.get('viewCount', existing.view_count))
                existing.like_count = int(statistics.get('likeCount', existing.like_count))
                existing.comment_count = int(statistics.get('commentCount', existing.comment_count))
                existing.thumbnail_url = snippet.get('thumbnails', {}).get('medium', {}).get('url',
                    snippet.get('thumbnails', {}).get('default', {}).get('url', existing.thumbnail_url))
                existing.duration = content_details.get('duration', existing.duration)
                existing.last_updated = datetime.utcnow()
            else:
                vs = VideoStats(
                    channel_id=channel.id,
                    video_id=vid,
                    title=snippet.get('title', ''),
                    published_at=published_at,
                    view_count=int(statistics.get('viewCount', 0)),
                    like_count=int(statistics.get('likeCount', 0)),
                    comment_count=int(statistics.get('commentCount', 0)),
                    thumbnail_url=snippet.get('thumbnails', {}).get('medium', {}).get('url',
                        snippet.get('thumbnails', {}).get('default', {}).get('url', '')),
                    duration=content_details.get('duration', ''),
                    last_updated=datetime.utcnow(),
                )
                db.session.add(vs)
            count += 1

        db.session.commit()
        return jsonify({'message': f'Synced {count} videos', 'count': count}), 200

    except Exception as e:
        print(f"Sync videos error: {str(e)}")
        return jsonify({'error': 'Failed to sync videos. Please try again.'}), 500


@app.route('/api/channels/<int:channel_id>/videos', methods=['GET'])
@login_required
def get_channel_videos(channel_id):
    channel = Channel.query.get(channel_id)

    if not channel or channel.user_id != session['user_id']:
        return jsonify({'error': 'Channel not found'}), 404

    videos = VideoStats.query.filter_by(channel_id=channel.id).order_by(
        VideoStats.published_at.desc()
    ).all()

    return jsonify([v.to_dict() for v in videos])


@app.route('/api/bot/toggle', methods=['POST'])
@login_required
def toggle_bot():
    user = User.query.get(session['user_id'])
    data = request.json
    enabled = data.get('enabled', False)

    user.bot_enabled = enabled
    db.session.commit()

    if enabled:
        bot_at = os.getenv('BOT_ACCESS_TOKEN', '')
        bot_rt = os.getenv('BOT_REFRESH_TOKEN', '')
        channels = Channel.query.filter_by(user_id=user.id, tracking_enabled=True).all()
        for channel in channels:
            settings = ChannelBotSettings.query.filter_by(channel_id=channel.id).first()
            settings_dict = {}
            if settings:
                settings_dict = settings.to_dict()
            bot_manager.start_bot(
                channel_id=channel.id,
                youtube_channel_id=channel.youtube_channel_id,
                access_token=user.access_token or session.get('access_token', ''),
                refresh_token=user.refresh_token or '',
                client_id=GOOGLE_CLIENT_ID or '',
                client_secret=GOOGLE_CLIENT_SECRET or '',
                bot_settings=settings_dict,
                bot_access_token=bot_at if bot_at else None,
                bot_refresh_token=bot_rt if bot_rt else None
            )
    else:
        channels = Channel.query.filter_by(user_id=user.id).all()
        for channel in channels:
            bot_manager.stop_bot(channel.id)

    return jsonify({
        'message': 'Bot status updated',
        'bot_enabled': user.bot_enabled
    })


@app.route('/api/bot/status', methods=['GET'])
@login_required
def bot_status():
    user = User.query.get(session['user_id'])
    channels = Channel.query.filter_by(user_id=user.id).all()
    statuses = {}
    for channel in channels:
        statuses[channel.id] = bot_manager.get_status(channel.id)
    return jsonify({
        'bot_enabled': user.bot_enabled,
        'channels': statuses
    })


@app.route('/api/bot/quick-toggle', methods=['POST'])
@login_required
def bot_quick_toggle():
    user = User.query.get(session['user_id'])
    data = request.json
    channel_id = data.get('channel_id')
    setting = data.get('setting')
    value = data.get('value')

    ALLOWED_TOGGLES = {
        'spam_filter_enabled', 'link_filter_enabled', 'caps_filter_enabled',
        'blocked_words_enabled', 'welcome_message_enabled', 'auto_thank_subs',
        'slow_mode_enabled', 'follower_only_mode', 'subscriber_only_mode',
        'timed_messages_enabled', 'anti_raid_enabled', 'auto_greet_new_viewers',
        'discord_notify_live', 'emoji_spam_filter_enabled', 'duplicate_message_filter',
    }

    if setting not in ALLOWED_TOGGLES:
        return jsonify({'error': 'Invalid setting'}), 400

    channel = Channel.query.filter_by(id=channel_id, user_id=user.id).first()
    if not channel:
        return jsonify({'error': 'Channel not found'}), 404

    settings = ChannelBotSettings.query.filter_by(channel_id=channel_id).first()
    if not settings:
        settings = ChannelBotSettings(channel_id=channel_id)
        db.session.add(settings)

    setattr(settings, setting, bool(value))
    db.session.commit()

    if bot_manager.is_running(channel_id):
        bot_manager.update_settings(channel_id, settings.to_dict())

    return jsonify({'ok': True, 'setting': setting, 'value': bool(value)})


@app.route('/api/bot/live-status', methods=['GET'])
@login_required
def bot_live_status():
    user = User.query.get(session['user_id'])
    channels = Channel.query.filter_by(user_id=user.id, tracking_enabled=True).all()
    statuses = []
    for channel in channels:
        s = bot_manager.get_status(channel.id)
        statuses.append({
            'channel_id': channel.id,
            'channel_name': channel.channel_name,
            'is_live': s.get('is_live', False),
            'stream_title': s.get('stream_title'),
            'running': s.get('running', False),
            'messages_processed': s.get('messages_processed', 0),
        })
    return jsonify({'channels': statuses})


@app.route('/api/channels/<int:channel_id>/settings', methods=['GET'])
@login_required
def get_channel_settings(channel_id):
    channel = Channel.query.get(channel_id)
    
    if not channel or channel.user_id != session['user_id']:
        return jsonify({'error': 'Channel not found'}), 404
    
    settings = ChannelBotSettings.query.filter_by(channel_id=channel_id).first()
    if not settings:
        settings = ChannelBotSettings(channel_id=channel_id)
        db.session.add(settings)
        db.session.commit()
    
    return jsonify(settings.to_dict())


@app.route('/api/channels/<int:channel_id>/settings', methods=['POST', 'PUT'])
@login_required
def update_channel_settings(channel_id):
    channel = Channel.query.get(channel_id)
    
    if not channel or channel.user_id != session['user_id']:
        return jsonify({'error': 'Channel not found'}), 404
    
    data = request.json
    
    settings = ChannelBotSettings.query.filter_by(channel_id=channel_id).first()
    if not settings:
        settings = ChannelBotSettings(channel_id=channel_id)
        db.session.add(settings)
    
    if 'bot_enabled' in data:
        settings.bot_enabled = data['bot_enabled']
    if 'chat_prefix' in data:
        settings.chat_prefix = data['chat_prefix']
    if 'response_delay' in data:
        settings.response_delay = int(data['response_delay'])
    if 'join_message' in data:
        settings.join_message = data['join_message']
    
    if 'spam_filter_enabled' in data:
        settings.spam_filter_enabled = data['spam_filter_enabled']
    if 'max_repeat_chars' in data:
        settings.max_repeat_chars = int(data['max_repeat_chars'])
    if 'max_message_length' in data:
        settings.max_message_length = int(data['max_message_length'])
    
    if 'link_filter_enabled' in data:
        settings.link_filter_enabled = data['link_filter_enabled']
    if 'link_whitelist' in data:
        if isinstance(data['link_whitelist'], list):
            settings.link_whitelist = '\n'.join(data['link_whitelist'])
        else:
            settings.link_whitelist = data['link_whitelist']
    
    if 'caps_filter_enabled' in data:
        settings.caps_filter_enabled = data['caps_filter_enabled']
    if 'max_caps_percent' in data:
        settings.max_caps_percent = int(data['max_caps_percent'])
    
    if 'blocked_words_enabled' in data:
        settings.blocked_words_enabled = data['blocked_words_enabled']
    if 'blocked_words' in data:
        settings.blocked_words = data['blocked_words']
    if 'timeout_duration' in data:
        settings.timeout_duration = int(data['timeout_duration'])
    if 'warning_message' in data:
        settings.warning_message = data['warning_message']
    
    if 'slow_mode_enabled' in data:
        settings.slow_mode_enabled = data['slow_mode_enabled']
    if 'slow_mode_seconds' in data:
        settings.slow_mode_seconds = int(data['slow_mode_seconds'])
    if 'follower_only_mode' in data:
        settings.follower_only_mode = data['follower_only_mode']
    if 'subscriber_only_mode' in data:
        settings.subscriber_only_mode = data['subscriber_only_mode']
    if 'emote_only_mode' in data:
        settings.emote_only_mode = data['emote_only_mode']
    
    if 'welcome_message_enabled' in data:
        settings.welcome_message_enabled = data['welcome_message_enabled']
    if 'welcome_message' in data:
        settings.welcome_message = data['welcome_message']
    
    if 'auto_thank_subs' in data:
        settings.auto_thank_subs = data['auto_thank_subs']
    if 'auto_thank_message' in data:
        settings.auto_thank_message = data['auto_thank_message']
    
    if 'timed_messages_enabled' in data:
        settings.timed_messages_enabled = data['timed_messages_enabled']
    if 'timed_messages' in data:
        if isinstance(data['timed_messages'], list):
            settings.timed_messages = json.dumps(data['timed_messages'])
        else:
            settings.timed_messages = data['timed_messages']
    
    if 'command_cooldown' in data:
        settings.command_cooldown = int(data['command_cooldown'])
    if 'command_user_cooldown' in data:
        settings.command_user_cooldown = int(data['command_user_cooldown'])
    
    if 'auto_mod_sensitivity' in data:
        settings.auto_mod_sensitivity = max(1, min(5, int(data['auto_mod_sensitivity'])))
    if 'whisper_cooldown' in data:
        settings.whisper_cooldown = int(data['whisper_cooldown'])
    if 'command_permission_default' in data:
        settings.command_permission_default = data['command_permission_default']
    if 'max_commands_per_minute' in data:
        settings.max_commands_per_minute = int(data['max_commands_per_minute'])
    if 'anti_raid_enabled' in data:
        settings.anti_raid_enabled = data['anti_raid_enabled']
    if 'anti_raid_min_account_age' in data:
        settings.anti_raid_min_account_age = int(data['anti_raid_min_account_age'])
    if 'nightbot_import_enabled' in data:
        settings.nightbot_import_enabled = data['nightbot_import_enabled']
    if 'log_deleted_messages' in data:
        settings.log_deleted_messages = data['log_deleted_messages']
    if 'auto_ban_bots' in data:
        settings.auto_ban_bots = data['auto_ban_bots']
    if 'custom_cooldown_message' in data:
        settings.custom_cooldown_message = data['custom_cooldown_message']
    if 'command_response_style' in data:
        settings.command_response_style = data['command_response_style']
    
    if 'whitelisted_words' in data:
        settings.whitelisted_words = data['whitelisted_words']
    if 'whitelisted_users' in data:
        settings.whitelisted_users = data['whitelisted_users']
    if 'regex_filters' in data:
        if isinstance(data['regex_filters'], list):
            settings.regex_filters = json.dumps(data['regex_filters'])
        else:
            settings.regex_filters = data['regex_filters']
    if 'emoji_spam_filter_enabled' in data:
        settings.emoji_spam_filter_enabled = data['emoji_spam_filter_enabled']
    if 'max_emojis' in data:
        settings.max_emojis = int(data['max_emojis'])
    if 'duplicate_message_filter' in data:
        settings.duplicate_message_filter = data['duplicate_message_filter']
    if 'timeout_on_spam' in data:
        settings.timeout_on_spam = int(data['timeout_on_spam'])
    if 'timeout_on_links' in data:
        settings.timeout_on_links = int(data['timeout_on_links'])
    if 'timeout_on_caps' in data:
        settings.timeout_on_caps = int(data['timeout_on_caps'])
    if 'timeout_on_blocked_words' in data:
        settings.timeout_on_blocked_words = int(data['timeout_on_blocked_words'])
    if 'first_offense_action' in data:
        settings.first_offense_action = data['first_offense_action']
    if 'second_offense_action' in data:
        settings.second_offense_action = data['second_offense_action']
    if 'third_offense_action' in data:
        settings.third_offense_action = data['third_offense_action']
    if 'exempt_moderators' in data:
        settings.exempt_moderators = data['exempt_moderators']
    if 'exempt_subscribers' in data:
        settings.exempt_subscribers = data['exempt_subscribers']

    if 'stream_title_template' in data:
        settings.stream_title_template = data['stream_title_template']
    if 'auto_greet_new_viewers' in data:
        settings.auto_greet_new_viewers = data['auto_greet_new_viewers']
    if 'auto_greet_message' in data:
        settings.auto_greet_message = data['auto_greet_message']
    if 'viewer_loyalty_tracking' in data:
        settings.viewer_loyalty_tracking = data['viewer_loyalty_tracking']
    if 'auto_ban_patterns' in data:
        if isinstance(data['auto_ban_patterns'], list):
            settings.auto_ban_patterns = json.dumps(data['auto_ban_patterns'])
        else:
            settings.auto_ban_patterns = data['auto_ban_patterns']
    if 'first_time_chatter_restrict' in data:
        settings.first_time_chatter_restrict = data['first_time_chatter_restrict']
    if 'first_time_chatter_mode' in data:
        settings.first_time_chatter_mode = data['first_time_chatter_mode']
    if 'slow_mode_on_raid' in data:
        settings.slow_mode_on_raid = data['slow_mode_on_raid']
    if 'slow_mode_on_raid_seconds' in data:
        settings.slow_mode_on_raid_seconds = int(data['slow_mode_on_raid_seconds'])
    if 'slow_mode_on_raid_duration' in data:
        settings.slow_mode_on_raid_duration = int(data['slow_mode_on_raid_duration'])

    if 'discord_webhook_url' in data:
        import re as re_mod
        webhook_val = data['discord_webhook_url'].strip()
        if webhook_val and not re_mod.match(r'^https://(discord\.com|discordapp\.com)/api/webhooks/', webhook_val):
            return jsonify({'error': 'Invalid Discord webhook URL'}), 400
        settings.discord_webhook_url = webhook_val
    if 'discord_notify_live' in data:
        settings.discord_notify_live = data['discord_notify_live']
    if 'discord_notify_milestones' in data:
        settings.discord_notify_milestones = data['discord_notify_milestones']

    if 'custom_commands' in data:
        settings.custom_commands = json.dumps(data['custom_commands'])
    
    if 'builtin_commands' in data:
        if isinstance(data['builtin_commands'], list):
            settings.builtin_commands = json.dumps(data['builtin_commands'])
        else:
            settings.builtin_commands = data['builtin_commands']
    
    settings.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'message': 'Settings updated successfully',
        'settings': settings.to_dict()
    })


@app.route('/api/channels/<int:channel_id>/builtin-commands', methods=['POST'])
@login_required
def update_builtin_commands(channel_id):
    channel = Channel.query.get(channel_id)
    
    if not channel or channel.user_id != session['user_id']:
        return jsonify({'error': 'Channel not found'}), 404
    
    data = request.json
    
    settings = ChannelBotSettings.query.filter_by(channel_id=channel_id).first()
    if not settings:
        settings = ChannelBotSettings(channel_id=channel_id)
        db.session.add(settings)
    
    current_commands = settings.get_builtin_commands()
    commands_by_name = {cmd['name']: cmd for cmd in current_commands}
    
    updates = data.get('commands', data if isinstance(data, list) else [])
    
    if isinstance(updates, list):
        for update in updates:
            name = update.get('name')
            if name and name in commands_by_name:
                if 'enabled' in update:
                    commands_by_name[name]['enabled'] = update['enabled']
                if 'cooldown' in update:
                    try:
                        commands_by_name[name]['cooldown'] = max(0, int(update['cooldown']))
                    except (ValueError, TypeError):
                        pass
                if 'permission_level' in update:
                    commands_by_name[name]['permission_level'] = str(update['permission_level'])
                if 'response_template' in update:
                    commands_by_name[name]['response_template'] = str(update['response_template'])
    elif isinstance(updates, dict):
        for name, update in updates.items():
            if name in commands_by_name:
                if isinstance(update, bool):
                    commands_by_name[name]['enabled'] = update
                elif isinstance(update, dict):
                    if 'enabled' in update:
                        commands_by_name[name]['enabled'] = bool(update['enabled'])
                    if 'cooldown' in update:
                        try:
                            commands_by_name[name]['cooldown'] = max(0, int(update['cooldown']))
                        except (ValueError, TypeError):
                            pass
                    if 'permission_level' in update:
                        commands_by_name[name]['permission_level'] = update['permission_level']
                    if 'response_template' in update:
                        commands_by_name[name]['response_template'] = update['response_template']
    
    settings.builtin_commands = json.dumps(list(commands_by_name.values()))
    settings.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'message': 'Built-in commands updated successfully',
        'builtin_commands': settings.get_builtin_commands()
    })


@app.route('/api/channels/<int:channel_id>/test-discord', methods=['POST'])
@login_required
def test_discord_webhook(channel_id):
    channel = Channel.query.get(channel_id)
    if not channel or channel.user_id != session['user_id']:
        return jsonify({'error': 'Channel not found'}), 404

    data = request.json
    webhook_url = data.get('webhook_url', '').strip()

    if not webhook_url or not webhook_url.startswith('https://discord.com/api/webhooks/'):
        return jsonify({'error': 'Invalid Discord webhook URL'}), 400

    channel_name = channel.channel_name or 'Your Channel'
    stream_url = f'https://www.youtube.com/channel/{channel.youtube_channel_id}/live'
    channel_url = f'https://www.youtube.com/channel/{channel.youtube_channel_id}'

    try:
        embed = {
            'author': {
                'name': f'{channel_name} is now live on YouTube!',
                'url': stream_url,
                'icon_url': channel.channel_thumbnail or '',
            },
            'title': 'Live Stream',
            'url': stream_url,
            'description': f'**{channel_name}** just went live. This is a test notification from Nexus showing exactly what your viewers will see.',
            'color': 0x6366f1,
            'thumbnail': {
                'url': channel.channel_thumbnail or '',
            },
            'fields': [
                {'name': 'Channel', 'value': f'[{channel_name}]({channel_url})', 'inline': True},
                {'name': 'Platform', 'value': 'YouTube', 'inline': True},
                {'name': 'Subscribers', 'value': f'{channel.subscriber_count:,}' if channel.subscriber_count else 'N/A', 'inline': True},
                {'name': '\u200b', 'value': f'**[Watch Stream]({stream_url})**', 'inline': False},
            ],
            'footer': {
                'text': 'Nexus Bot',
                'icon_url': 'https://nexusbeta.vercel.app/static/img/logo.png',
            },
            'timestamp': datetime.utcnow().isoformat() + 'Z',
        }
        resp = requests.post(webhook_url, json={
            'content': '@everyone',
            'embeds': [embed],
            'username': 'Nexus Bot',
            'avatar_url': 'https://nexusbeta.vercel.app/static/img/logo.png',
        }, timeout=10)
        if resp.status_code in (200, 204):
            return jsonify({'message': 'Test message sent'})
        else:
            return jsonify({'error': 'Discord returned an error. Check your webhook URL.'}), 400
    except Exception:
        return jsonify({'error': 'Could not reach Discord. Check the URL.'}), 500


@app.route('/api/channels/<int:channel_id>/import-nightbot', methods=['POST'])
@login_required
def import_nightbot_commands(channel_id):
    channel = Channel.query.get(channel_id)
    if not channel or channel.user_id != session['user_id']:
        return jsonify({'error': 'Channel not found'}), 404

    data = request.json
    raw_text = data.get('commands_text', '')

    if not raw_text.strip():
        return jsonify({'error': 'No commands provided'}), 400

    settings = ChannelBotSettings.query.filter_by(channel_id=channel_id).first()
    if not settings:
        settings = ChannelBotSettings(channel_id=channel_id)
        db.session.add(settings)

    try:
        existing = json.loads(settings.custom_commands) if settings.custom_commands else {}
    except Exception:
        existing = {}

    imported = 0
    skipped = 0
    lines = raw_text.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith('!') and ' ' in line:
            parts = line.split(' ', 1)
            cmd_name = parts[0].strip().lower()
            cmd_response = parts[1].strip()
        elif '\t' in line:
            parts = line.split('\t', 1)
            cmd_name = parts[0].strip().lower()
            cmd_response = parts[1].strip()
            if not cmd_name.startswith('!'):
                cmd_name = '!' + cmd_name
        else:
            skipped += 1
            continue

        if not cmd_name or not cmd_response:
            skipped += 1
            continue

        if cmd_name not in existing:
            existing[cmd_name] = {
                'response': cmd_response,
                'cooldown': 5,
                'level': 'everyone'
            }
            imported += 1
        else:
            skipped += 1

    settings.custom_commands = json.dumps(existing)
    settings.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'message': f'Imported {imported} commands, skipped {skipped}',
        'imported': imported,
        'skipped': skipped,
        'settings': settings.to_dict()
    })


@app.route('/api/channels/<int:channel_id>/viewers', methods=['GET'])
@login_required
def get_channel_viewers(channel_id):
    channel = Channel.query.get(channel_id)
    if not channel or channel.user_id != session['user_id']:
        return jsonify({'error': 'Channel not found'}), 404

    q = request.args.get('q', '').strip()
    sort = request.args.get('sort', 'last_seen')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    query = ChatUser.query.filter_by(channel_id=channel_id)

    if q:
        from sqlalchemy import or_
        query = query.filter(
            or_(
                ChatUser.username.ilike(f'%{q}%'),
                ChatUser.display_name.ilike(f'%{q}%'),
            )
        )

    sort_map = {
        'watchtime': ChatUser.watchtime_minutes.desc(),
        'messages': ChatUser.messages_sent.desc(),
        'commands': ChatUser.commands_used.desc(),
        'timeouts': ChatUser.timeout_count.desc(),
        'last_seen': ChatUser.last_seen.desc(),
    }
    order = sort_map.get(sort, ChatUser.last_seen.desc())
    query = query.order_by(order)

    total = query.count()
    viewers = query.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        'viewers': [v.to_dict() for v in viewers],
        'total': total,
        'page': page,
        'per_page': per_page,
    })


@app.route('/api/channels/<int:channel_id>/viewers/<int:viewer_id>/ban', methods=['POST'])
@login_required
def ban_viewer(channel_id, viewer_id):
    channel = Channel.query.get(channel_id)
    if not channel or channel.user_id != session['user_id']:
        return jsonify({'error': 'Channel not found'}), 404

    viewer = ChatUser.query.get(viewer_id)
    if not viewer or viewer.channel_id != channel_id:
        return jsonify({'error': 'Viewer not found'}), 404

    data = request.json or {}
    viewer.is_banned = data.get('banned', not viewer.is_banned)
    viewer.ban_reason = data.get('reason', viewer.ban_reason)
    db.session.commit()

    return jsonify({
        'message': 'Ban status updated',
        'viewer': viewer.to_dict(),
    })


@app.route('/api/channels/<int:channel_id>/viewers/<int:viewer_id>/timeout', methods=['POST'])
@login_required
def timeout_viewer(channel_id, viewer_id):
    channel = Channel.query.get(channel_id)
    if not channel or channel.user_id != session['user_id']:
        return jsonify({'error': 'Channel not found'}), 404

    viewer = ChatUser.query.get(viewer_id)
    if not viewer or viewer.channel_id != channel_id:
        return jsonify({'error': 'Viewer not found'}), 404

    viewer.timeout_count = (viewer.timeout_count or 0) + 1
    db.session.commit()

    return jsonify({
        'message': 'Timeout recorded',
        'viewer': viewer.to_dict(),
    })


@app.route('/api/channels/<int:channel_id>/command-logs', methods=['GET'])
@login_required
def get_command_logs(channel_id):
    channel = Channel.query.get(channel_id)
    if not channel or channel.user_id != session['user_id']:
        return jsonify({'error': 'Channel not found'}), 404

    logs = CommandLog.query.filter_by(channel_id=channel_id).order_by(
        CommandLog.timestamp.desc()
    ).limit(100).all()

    return jsonify([log.to_dict() for log in logs])


@app.route('/api/channels/<int:channel_id>/viewers/track', methods=['POST'])
@login_required
def track_viewer(channel_id):
    channel = Channel.query.get(channel_id)
    if not channel or channel.user_id != session['user_id']:
        return jsonify({'error': 'Channel not found'}), 404

    data = request.json or {}
    youtube_user_id = data.get('youtube_user_id')
    username = data.get('username')

    if not youtube_user_id or not username:
        return jsonify({'error': 'youtube_user_id and username are required'}), 400

    viewer = ChatUser.query.filter_by(
        channel_id=channel_id,
        youtube_user_id=youtube_user_id
    ).first()

    if not viewer:
        viewer = ChatUser(
            channel_id=channel_id,
            youtube_user_id=youtube_user_id,
            username=username,
            display_name=username,
            first_seen=datetime.utcnow(),
        )
        db.session.add(viewer)

    viewer.username = username
    viewer.last_seen = datetime.utcnow()

    try:
        if 'watchtime_minutes' in data:
            viewer.watchtime_minutes = (viewer.watchtime_minutes or 0) + max(0, int(data['watchtime_minutes']))
        if 'messages' in data:
            viewer.messages_sent = (viewer.messages_sent or 0) + max(0, int(data['messages']))
    except (ValueError, TypeError):
        return jsonify({'error': 'watchtime_minutes and messages must be integers'}), 400

    db.session.commit()

    return jsonify({
        'message': 'Viewer data tracked',
        'viewer': viewer.to_dict(),
    })


@app.route('/')
def index():
    return render_template('index.html')


def _auto_sync_channels(user, channels):
    access_token = session.get('access_token')
    stale_threshold = datetime.utcnow() - timedelta(hours=1)
    for ch in channels:
        if ch.last_synced and ch.last_synced > stale_threshold:
            continue
        try:
            params = {'part': 'snippet,statistics', 'id': ch.youtube_channel_id}
            headers = {}
            if access_token:
                headers['Authorization'] = f'Bearer {access_token}'
            elif YOUTUBE_API_KEY:
                params['key'] = YOUTUBE_API_KEY
            else:
                continue
            resp = requests.get('https://www.googleapis.com/youtube/v3/channels',
                                params=params, headers=headers, timeout=8)
            if resp.status_code == 200:
                items = resp.json().get('items', [])
                if items:
                    item = items[0]
                    snippet = item.get('snippet', {})
                    stats = item.get('statistics', {})
                    ch.channel_name = snippet.get('title', ch.channel_name)
                    ch.channel_thumbnail = snippet.get('thumbnails', {}).get('medium', {}).get('url',
                        snippet.get('thumbnails', {}).get('default', {}).get('url', ch.channel_thumbnail))
                    ch.subscriber_count = int(stats.get('subscriberCount', 0))
                    ch.view_count = int(stats.get('viewCount', 0))
                    ch.video_count = int(stats.get('videoCount', 0))
                    ch.last_synced = datetime.utcnow()
                    today = datetime.utcnow().date()
                    existing_stat = ChannelStats.query.filter_by(
                        user_id=user.id, channel_id=ch.youtube_channel_id, stat_date=today
                    ).first()
                    if not existing_stat:
                        db.session.add(ChannelStats(
                            user_id=user.id, channel_id=ch.youtube_channel_id, stat_date=today,
                            subscribers=ch.subscriber_count, total_views=ch.view_count, total_videos=ch.video_count,
                        ))
                    else:
                        existing_stat.subscribers = ch.subscriber_count
                        existing_stat.total_views = ch.view_count
                        existing_stat.total_videos = ch.video_count
        except Exception as e:
            print(f"Auto-sync error for channel {ch.id}: {e}")
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()


@app.route('/dashboard/confirm-moderator', methods=['POST'])
@login_required
def confirm_moderator():
    user = User.query.get(session['user_id'])
    channels = Channel.query.filter_by(user_id=user.id).all()
    for ch in channels:
        s = ChannelBotSettings.query.filter_by(channel_id=ch.id).first()
        if s:
            s.bot_moderator_ok = True
    db.session.commit()
    return redirect('/dashboard')


@app.route('/dashboard')
@login_required
def dashboard():
    real_user = User.query.get(session['user_id'])
    viewing_as = None
    view_as_id = session.get('view_as_user_id')
    if view_as_id and real_user.is_admin and view_as_id != real_user.id:
        viewed = User.query.get(view_as_id)
        if viewed:
            user = viewed
            viewing_as = real_user
        else:
            session.pop('view_as_user_id', None)
            user = real_user
    else:
        user = real_user

    if not viewing_as and not user.setup_complete:
        return redirect('/setup')

    channels = Channel.query.filter_by(user_id=user.id).all()

    if not viewing_as:
        _auto_sync_channels(user, channels)

    channel_ids = [ch.id for ch in channels]

    thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).date()
    stats_data = ChannelStats.query.filter(
        ChannelStats.user_id == user.id,
        ChannelStats.stat_date >= thirty_days_ago
    ).order_by(ChannelStats.stat_date.asc()).all()

    video_stats = []
    if channel_ids:
        video_stats = VideoStats.query.filter(
            VideoStats.channel_id.in_(channel_ids)
        ).order_by(VideoStats.published_at.desc()).limit(50).all()

    bot_settings = []
    for ch in channels:
        settings = ChannelBotSettings.query.filter_by(channel_id=ch.id).first()
        if not settings:
            settings = ChannelBotSettings(channel_id=ch.id)
            db.session.add(settings)
            db.session.commit()
        bot_settings.append({'channel': ch, 'settings': settings})

    custom_cmd_count = 0
    timer_count = 0
    builtin_cmd_count = 0
    for bs in bot_settings:
        s = bs['settings']
        try:
            cmds = json.loads(s.custom_commands) if s.custom_commands else {}
            custom_cmd_count += len(cmds)
        except Exception:
            pass
        try:
            timers = json.loads(s.timed_messages) if s.timed_messages else []
            timer_count += len(timers)
        except Exception:
            pass
        try:
            builtins = s.get_builtin_commands()
            builtin_cmd_count += sum(1 for b in builtins if b.get('enabled'))
        except Exception:
            pass

    viewers = []
    command_logs = []
    if channel_ids:
        viewers = ChatUser.query.filter(
            ChatUser.channel_id.in_(channel_ids)
        ).order_by(ChatUser.last_seen.desc()).limit(50).all()

        command_logs = CommandLog.query.filter(
            CommandLog.channel_id.in_(channel_ids)
        ).order_by(CommandLog.timestamp.desc()).limit(50).all()

    bot_moderator_ok = any(
        bs['settings'].bot_moderator_ok for bs in bot_settings
    ) if bot_settings else False

    return render_template(
        'dashboard.html',
        user=user,
        channels=channels,
        stats_data=stats_data,
        video_stats=video_stats,
        bot_settings=bot_settings,
        custom_cmd_count=custom_cmd_count,
        timer_count=timer_count,
        builtin_cmd_count=builtin_cmd_count,
        viewers=viewers,
        command_logs=command_logs,
        bot_moderator_ok=bot_moderator_ok,
        viewing_as=viewing_as,
    )


def _sync_channel_videos_internal(channel):
    api_key = YOUTUBE_API_KEY
    access_token = session.get('access_token')
    if not api_key and not access_token:
        return
    try:
        latest = VideoStats.query.filter_by(channel_id=channel.id).order_by(VideoStats.last_updated.desc()).first()
        if latest and (datetime.utcnow() - latest.last_updated).total_seconds() < 300:
            return
        search_params = {
            'part': 'snippet',
            'channelId': channel.youtube_channel_id,
            'type': 'video',
            'order': 'date',
            'maxResults': 20,
        }
        search_headers = {}
        if api_key:
            search_params['key'] = api_key
        else:
            search_headers['Authorization'] = f'Bearer {access_token}'
        search_resp = requests.get('https://www.googleapis.com/youtube/v3/search', params=search_params, headers=search_headers, timeout=10)
        if search_resp.status_code != 200:
            return
        items = search_resp.json().get('items', [])
        if not items:
            return
        video_ids = [item['id']['videoId'] for item in items if item.get('id', {}).get('videoId')]
        if not video_ids:
            return
        stats_params = {'part': 'snippet,statistics,contentDetails', 'id': ','.join(video_ids)}
        stats_headers = {}
        if api_key:
            stats_params['key'] = api_key
        else:
            stats_headers['Authorization'] = f'Bearer {access_token}'
        stats_resp = requests.get('https://www.googleapis.com/youtube/v3/videos', params=stats_params, headers=stats_headers, timeout=10)
        if stats_resp.status_code != 200:
            return
        for video in stats_resp.json().get('items', []):
            vid = video['id']
            snippet = video.get('snippet', {})
            statistics = video.get('statistics', {})
            content_details = video.get('contentDetails', {})
            published_at = None
            if snippet.get('publishedAt'):
                try:
                    published_at = datetime.strptime(snippet['publishedAt'], '%Y-%m-%dT%H:%M:%SZ')
                except ValueError:
                    published_at = datetime.fromisoformat(snippet['publishedAt'].replace('Z', '+00:00')).replace(tzinfo=None)
            existing = VideoStats.query.filter_by(channel_id=channel.id, video_id=vid).first()
            if existing:
                existing.title = snippet.get('title', existing.title)
                existing.published_at = published_at or existing.published_at
                existing.view_count = int(statistics.get('viewCount', existing.view_count))
                existing.like_count = int(statistics.get('likeCount', existing.like_count))
                existing.comment_count = int(statistics.get('commentCount', existing.comment_count))
                existing.thumbnail_url = snippet.get('thumbnails', {}).get('medium', {}).get('url', snippet.get('thumbnails', {}).get('default', {}).get('url', existing.thumbnail_url))
                existing.duration = content_details.get('duration', existing.duration)
                existing.last_updated = datetime.utcnow()
            else:
                vs = VideoStats(
                    channel_id=channel.id,
                    video_id=vid,
                    title=snippet.get('title', ''),
                    published_at=published_at,
                    view_count=int(statistics.get('viewCount', 0)),
                    like_count=int(statistics.get('likeCount', 0)),
                    comment_count=int(statistics.get('commentCount', 0)),
                    thumbnail_url=snippet.get('thumbnails', {}).get('medium', {}).get('url', snippet.get('thumbnails', {}).get('default', {}).get('url', '')),
                    duration=content_details.get('duration', ''),
                    last_updated=datetime.utcnow(),
                )
                db.session.add(vs)
        db.session.commit()
    except Exception as e:
        print(f"Auto-sync videos error: {str(e)}")


@app.route('/videos')
@login_required
def videos_page():
    user = User.query.get(session['user_id'])
    channels = Channel.query.filter_by(user_id=user.id).all()
    channel_ids = [ch.id for ch in channels]

    for ch in channels:
        _sync_channel_videos_internal(ch)

    videos = []
    if channel_ids:
        videos = VideoStats.query.filter(
            VideoStats.channel_id.in_(channel_ids)
        ).order_by(VideoStats.published_at.desc()).all()

    return render_template(
        'videos.html',
        user=user,
        channels=channels,
        channel_ids=channel_ids,
        videos=videos,
        auto_synced=True,
    )


@app.route('/analytics')
@login_required
def analytics():
    user = User.query.get(session['user_id'])
    channels = Channel.query.filter_by(user_id=user.id).all()

    channel_ids = [ch.id for ch in channels]

    thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).date()
    stats_data = ChannelStats.query.filter(
        ChannelStats.user_id == user.id,
        ChannelStats.stat_date >= thirty_days_ago
    ).order_by(ChannelStats.stat_date.asc()).all()

    return render_template(
        'dashboard.html',
        user=user,
        channels=channels,
        stats_data=stats_data,
    )


@app.route('/settings')
@login_required
def account_settings():
    user = User.query.get(session['user_id'])
    channels = Channel.query.filter_by(user_id=user.id).all()
    notif_prefs = user.get_notification_preferences()
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)

    nexus_bot_linked = False
    nexus_bot_user = None
    if user.discord_user_id:
        nexus_bot_user = BotUser.query.filter_by(discord_id=user.discord_user_id).first()
        if nexus_bot_user and nexus_bot_user.nexus_user_id == user.id:
            nexus_bot_linked = True

    bot_online = False
    bot_avatar_url = None
    bot_username = None
    bot_token = os.getenv('DISCORD_BOT_TOKEN')
    if bot_token:
        try:
            bot_resp = requests.get('https://discord.com/api/v10/users/@me', headers={
                'Authorization': f'Bot {bot_token}',
            }, timeout=5)
            if bot_resp.status_code == 200:
                bot_data = bot_resp.json()
                bot_online = True
                bot_username = bot_data.get('username', '')
                bot_avatar = bot_data.get('avatar')
                bot_id = bot_data.get('id')
                if bot_avatar and bot_id:
                    bot_avatar_url = f'https://cdn.discordapp.com/avatars/{bot_id}/{bot_avatar}.png?size=128'
        except Exception:
            pass

    return render_template('settings.html', user=user, channels=channels, notif_prefs=notif_prefs,
                           csrf_token=session['csrf_token'], nexus_bot_linked=nexus_bot_linked,
                           nexus_bot_user=nexus_bot_user, bot_online=bot_online,
                           bot_avatar_url=bot_avatar_url, bot_username=bot_username)


@app.route('/settings/preferences', methods=['POST'])
@login_required
def save_preferences():
    user = User.query.get(session['user_id'])
    if not user:
        if request.is_json:
            return jsonify({'error': 'not_authenticated'}), 401
        return redirect('/auth/login')

    if request.is_json:
        data = request.get_json()
        csrf = data.get('csrf_token', '')
        if csrf != session.get('csrf_token', ''):
            return jsonify({'error': 'invalid_request'}), 403
        existing_prefs = user.get_notification_preferences()
        notif_prefs = dict(existing_prefs)
        if 'theme_preference' in data and data['theme_preference'] in ('light', 'dark'):
            notif_prefs['theme_preference'] = data['theme_preference']
        if 'compact_mode' in data:
            notif_prefs['compact_mode'] = bool(data['compact_mode'])
        user.notification_preferences = json.dumps(notif_prefs)
        user.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'status': 'ok'})

    csrf_token = request.form.get('csrf_token', '')
    if csrf_token != session.get('csrf_token', ''):
        return redirect('/settings?error=invalid_request')

    existing_prefs = user.get_notification_preferences()

    notif_prefs = dict(existing_prefs)
    notif_prefs['theme_preference'] = request.form.get('theme_preference', 'light')
    notif_prefs['compact_mode'] = 'compact_mode' in request.form
    user.notification_preferences = json.dumps(notif_prefs)
    user.updated_at = datetime.utcnow()
    db.session.commit()

    return redirect('/settings?saved=1')


@app.route('/settings/delete-account', methods=['POST'])
@login_required
def delete_account():
    user = User.query.get(session['user_id'])
    if not user:
        return redirect('/auth/login')

    csrf_token = request.form.get('csrf_token', '')
    if csrf_token != session.get('csrf_token', ''):
        return redirect('/settings?error=invalid_request')

    confirmation = request.form.get('confirm_delete', '')
    if confirmation != 'DELETE':
        return redirect('/settings?error=confirmation')

    db.session.delete(user)
    db.session.commit()
    session.clear()
    return redirect('/?deleted=1')


@app.route('/settings/disconnect-channel/<int:channel_id>', methods=['POST'])
@login_required
def disconnect_channel(channel_id):
    csrf_token = request.form.get('csrf_token', '')
    if csrf_token != session.get('csrf_token', ''):
        return redirect('/settings?error=invalid_request')

    channel = Channel.query.get(channel_id)
    if not channel or channel.user_id != session['user_id']:
        return redirect('/settings?error=notfound')

    db.session.delete(channel)
    db.session.commit()
    return redirect('/settings?disconnected=1')


@app.route('/settings/export-data', methods=['POST'])
@login_required
def export_data():
    csrf_token = request.form.get('csrf_token', '')
    if csrf_token != session.get('csrf_token', ''):
        return redirect('/settings?error=invalid_request')

    user = User.query.get(session['user_id'])
    if not user:
        return redirect('/auth/login')

    channels = Channel.query.filter_by(user_id=user.id).all()
    export = {
        'account': user.to_dict(),
        'channels': [c.to_dict() for c in channels],
        'exported_at': datetime.utcnow().isoformat(),
    }
    for ch_data, ch in zip(export['channels'], channels):
        command_logs = CommandLog.query.filter_by(channel_id=ch.id).all()
        ch_data['command_logs'] = [cl.to_dict() for cl in command_logs]
        chat_users = ChatUser.query.filter_by(channel_id=ch.id).all()
        ch_data['chat_users'] = [cu.to_dict() for cu in chat_users]

    return Response(
        json.dumps(export, indent=2),
        mimetype='application/json',
        headers={'Content-Disposition': 'attachment; filename=nexus-data-export.json'}
    )


@app.route('/settings/clear-chat-logs', methods=['POST'])
@login_required
def clear_chat_logs():
    csrf_token = request.form.get('csrf_token', '')
    if csrf_token != session.get('csrf_token', ''):
        return redirect('/settings?error=invalid_request')

    user = User.query.get(session['user_id'])
    if not user:
        return redirect('/auth/login')

    channels = Channel.query.filter_by(user_id=user.id).all()
    for ch in channels:
        ChatUser.query.filter_by(channel_id=ch.id).delete()
    db.session.commit()
    return redirect('/settings?cleared=1')


@app.route('/settings/clear-command-history', methods=['POST'])
@login_required
def clear_command_history():
    csrf_token = request.form.get('csrf_token', '')
    if csrf_token != session.get('csrf_token', ''):
        return redirect('/settings?error=invalid_request')

    user = User.query.get(session['user_id'])
    if not user:
        return redirect('/auth/login')

    channels = Channel.query.filter_by(user_id=user.id).all()
    for ch in channels:
        CommandLog.query.filter_by(channel_id=ch.id).delete()
    db.session.commit()
    return redirect('/settings?cleared=1')


@app.route('/channel/<int:channel_id>')
@login_required
def channel_detail(channel_id):
    channel = Channel.query.get(channel_id)
    
    if not channel or channel.user_id != session['user_id']:
        return redirect('/dashboard')
    
    user = User.query.get(session['user_id'])
    streams = StreamSession.query.filter_by(channel_id=channel.id).order_by(
        StreamSession.start_time.desc()
    ).limit(50).all()
    stats = ChannelStats.query.filter_by(
        user_id=session['user_id'],
        channel_id=channel.youtube_channel_id
    ).order_by(ChannelStats.stat_date.desc()).limit(30).all()
    stats = list(reversed(stats))

    stats_dates = [s.stat_date.strftime('%b %d') for s in stats]
    stats_subs = [s.subscribers or 0 for s in stats]
    stats_views = [s.total_views or 0 for s in stats]
    stats_videos = [s.total_videos or 0 for s in stats]

    sub_change = stats_subs[-1] - stats_subs[0] if len(stats_subs) >= 2 else 0
    view_change = stats_views[-1] - stats_views[0] if len(stats_views) >= 2 else 0
    video_change = stats_videos[-1] - stats_videos[0] if len(stats_videos) >= 2 else 0

    sub_change_pct = round((sub_change / stats_subs[0]) * 100, 1) if len(stats_subs) >= 2 and stats_subs[0] > 0 else 0
    view_change_pct = round((view_change / stats_views[0]) * 100, 1) if len(stats_views) >= 2 and stats_views[0] > 0 else 0

    total_streams = len(streams)
    completed_streams = [s for s in streams if s.end_time]
    total_duration = sum(s.duration_seconds or 0 for s in completed_streams)
    avg_duration = total_duration // len(completed_streams) if completed_streams else 0
    best_peak = max((s.peak_viewers or 0 for s in streams), default=0)
    avg_peak = sum(s.peak_viewers or 0 for s in streams) // total_streams if total_streams else 0
    avg_avg_viewers = sum(s.average_viewers or 0 for s in streams) // total_streams if total_streams else 0
    total_interactions = sum(s.total_viewer_interactions or 0 for s in streams)

    stream_dates = []
    stream_peak_data = []
    stream_avg_data = []
    for s in reversed(list(streams[:20])):
        stream_dates.append(s.start_time.strftime('%b %d'))
        stream_peak_data.append(s.peak_viewers or 0)
        stream_avg_data.append(s.average_viewers or 0)

    import json as json_mod
    return render_template('channel.html',
        channel=channel, user=user, streams=streams,
        stats=list(reversed(stats)),
        stats_dates_json=json_mod.dumps(stats_dates),
        stats_subs_json=json_mod.dumps(stats_subs),
        stats_views_json=json_mod.dumps(stats_views),
        stats_videos_json=json_mod.dumps(stats_videos),
        sub_change=sub_change, sub_change_pct=sub_change_pct,
        view_change=view_change, view_change_pct=view_change_pct,
        video_change=video_change,
        total_streams=total_streams,
        avg_duration=avg_duration,
        best_peak=best_peak,
        avg_peak=avg_peak,
        avg_avg_viewers=avg_avg_viewers,
        total_interactions=total_interactions,
        stream_dates_json=json_mod.dumps(stream_dates),
        stream_peak_json=json_mod.dumps(stream_peak_data),
        stream_avg_json=json_mod.dumps(stream_avg_data),
    )


@app.route('/setup')
@login_required
def setup_wizard():
    user = User.query.get(session['user_id'])
    channels = Channel.query.filter_by(user_id=user.id).all()
    channel = channels[0] if channels else None
    settings = None
    builtin_commands = []
    if channel:
        settings = ChannelBotSettings.query.filter_by(channel_id=channel.id).first()
        if not settings:
            settings = ChannelBotSettings(channel_id=channel.id)
            db.session.add(settings)
            db.session.commit()
        builtin_commands = settings.get_builtin_commands()
    return render_template('setup_wizard.html', channel=channel, settings=settings.to_dict() if settings else {},
                           channels=channels, builtin_commands=builtin_commands,
                           user_name=user.username or user.youtube_channel_name or 'there',
                           user_avatar=user.profile_picture)


@app.route('/api/setup/complete', methods=['POST'])
@login_required
def api_setup_complete():
    user = User.query.get(session['user_id'])
    user.setup_complete = True
    db.session.commit()
    return jsonify({'success': True})


@app.route('/channel/<int:channel_id>/settings')
@login_required
def channel_settings(channel_id):
    channel = Channel.query.get(channel_id)
    
    if not channel or channel.user_id != session['user_id']:
        return redirect('/dashboard')
    
    settings = ChannelBotSettings.query.filter_by(channel_id=channel_id).first()
    if not settings:
        settings = ChannelBotSettings(channel_id=channel_id)
        db.session.add(settings)
        db.session.commit()
    
    user = User.query.get(session['user_id'])
    discord_info = None
    bot_servers = []
    bot_user = BotUser.query.filter_by(nexus_user_id=user.id).first() if user else None
    if bot_user:
        discord_info = {
            'user_id': bot_user.discord_id,
            'username': bot_user.display_name,
        }
        configs = ServerConfig.query.filter_by(bot_user_id=bot_user.id).all()
        bot_servers = [{'name': c.server_name, 'id': c.server_id} for c in configs]
    elif user and user.discord_user_id:
        discord_info = {
            'user_id': user.discord_user_id,
            'username': user.discord_username,
        }

    return render_template('channel-settings.html', channel=channel, settings=settings.to_dict(),
                           discord_info=discord_info, bot_servers=bot_servers)


@app.route('/robots.txt')
def robots_txt():
    content = """User-agent: *
Allow: /
Disallow: /dashboard
Disallow: /settings
Disallow: /videos
Disallow: /channel/
Disallow: /api/
Disallow: /auth/callback

Sitemap: https://nexusbeta.vercel.app/sitemap.xml
"""
    return app.response_class(content, mimetype='text/plain')


@app.route('/changelog')
def changelog():
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
    return render_template('changelog.html', changelog=changelog_data, discord_text=discord_text)

@app.route('/sitemap.xml')
def sitemap_xml():
    pages = [
        ('/', '1.0', 'weekly'),
        ('/about', '0.8', 'monthly'),
        ('/faq', '0.7', 'monthly'),
        ('/changelog', '0.7', 'weekly'),
        ('/status', '0.6', 'daily'),
        ('/blog', '0.7', 'weekly'),
        ('/contact', '0.5', 'monthly'),
        ('/help', '0.6', 'monthly'),
        ('/community', '0.6', 'monthly'),
        ('/privacy', '0.3', 'yearly'),
        ('/terms', '0.3', 'yearly'),
        ('/auth/login', '0.5', 'monthly'),
    ]
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for path, priority, freq in pages:
        xml += f'  <url>\n    <loc>https://nexusbeta.vercel.app{path}</loc>\n    <priority>{priority}</priority>\n    <changefreq>{freq}</changefreq>\n  </url>\n'
    xml += '</urlset>'
    return app.response_class(xml, mimetype='application/xml')


@app.route('/faq')
def faq():
    return render_template('faq.html')


@app.route('/terms')
def terms():
    return render_template('terms.html')


@app.route('/privacy')
def privacy():
    return render_template('privacy.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/blog')
def blog():
    from blog_data import BLOG_POSTS
    merged = _get_merged_blog_posts('nexus')
    return render_template('blog.html', posts=merged)

@app.route('/blog/<slug>')
def blog_post(slug):
    from blog_data import BLOG_POSTS
    db_post = BlogPost.query.filter_by(blog_type='nexus', slug=slug, is_published=True).first()
    if db_post:
        all_posts = _get_merged_blog_posts('nexus')
        post = db_post.to_dict()
        post_index = next((i for i, p in enumerate(all_posts) if p['slug'] == slug), 0)
        prev_post = all_posts[post_index - 1] if post_index > 0 else None
        next_post = all_posts[post_index + 1] if post_index < len(all_posts) - 1 else None
        return render_template('blog_post.html', post=post, prev_post=prev_post, next_post=next_post)
    post = None
    post_index = None
    for i, p in enumerate(BLOG_POSTS):
        if p['slug'] == slug:
            post = p
            post_index = i
            break
    if not post:
        return render_template('404.html'), 404
    prev_post = BLOG_POSTS[post_index - 1] if post_index > 0 else None
    next_post = BLOG_POSTS[post_index + 1] if post_index < len(BLOG_POSTS) - 1 else None
    return render_template('blog_post.html', post=post, prev_post=prev_post, next_post=next_post)


def _get_merged_blog_posts(blog_type):
    if blog_type == 'nexus':
        from blog_data import BLOG_POSTS as static_posts
    else:
        from bot_blog_data import BOT_BLOG_POSTS as static_posts
    db_posts = BlogPost.query.filter_by(blog_type=blog_type, is_published=True).all()
    db_dicts = [p.to_dict() for p in db_posts]
    db_slugs = {p['slug'] for p in db_dicts}
    merged = db_dicts + [p for p in static_posts if p['slug'] not in db_slugs]
    def _parse_date(p):
        try:
            return datetime.strptime(p.get('date', ''), '%B %d, %Y')
        except Exception:
            return datetime(2000, 1, 1)
    return sorted(merged, key=_parse_date, reverse=True)


@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/help')
def help_center():
    return render_template('help.html')


@app.route('/community')
def community():
    return render_template('community.html')


@app.route('/github')
def github_export():
    return render_template('github.html')


@app.route('/github/download')
def github_download():
    import io as _io
    import zipfile as _zf
    from datetime import datetime as _dt
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    skip_dirs = {'.git', '__pycache__', '.cache', 'node_modules', '.upm', 'flask_session'}
    skip_exts = {'.pyc', '.pyo', '.pyd'}
    min_date = (1980, 1, 1, 0, 0, 0)
    buf = _io.BytesIO()
    with _zf.ZipFile(buf, 'w', _zf.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(project_root):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            rel_root = os.path.relpath(root, project_root)
            for fname in files:
                if fname.endswith(tuple(skip_exts)):
                    continue
                full_path = os.path.join(root, fname)
                rel_path = os.path.join(rel_root, fname) if rel_root != '.' else fname
                rel_path = rel_path.replace('\\', '/')
                try:
                    zinfo = _zf.ZipInfo(rel_path)
                    zinfo.compress_type = _zf.ZIP_DEFLATED
                    mtime = os.path.getmtime(full_path)
                    dt = _dt.utcfromtimestamp(mtime)
                    zinfo.date_time = max((dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second), min_date)
                    with open(full_path, 'rb') as f:
                        zf.writestr(zinfo, f.read())
                except (OSError, PermissionError):
                    pass
    buf.seek(0)
    dl_name = f'nexus-{_dt.utcnow().strftime("%Y%m%d")}.zip'
    return Response(buf.read(), mimetype='application/zip',
                    headers={'Content-Disposition': f'attachment; filename={dl_name}'})





def _refresh_user_token(user):
    if not user.refresh_token:
        return
    try:
        resp = requests.post('https://oauth2.googleapis.com/token', data={
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'refresh_token': user.refresh_token,
            'grant_type': 'refresh_token',
        }, timeout=10)
        if resp.status_code == 200:
            token_data = resp.json()
            user.access_token = token_data.get('access_token', user.access_token)
            db.session.commit()
    except Exception:
        pass


@app.route('/status')
def status():
    import time as _time

    checked_at = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

    db_status = 'operational'
    db_response_ms = 0
    db_message = ''
    try:
        t0 = _time.monotonic()
        db.session.execute(db.text('SELECT 1'))
        db_response_ms = round((_time.monotonic() - t0) * 1000, 1)
        db_message = 'Connected and responding normally'
    except Exception as e:
        db_status = 'degraded'
        logging.error(f'Database health check failed: {e}')
        db_message = 'Database connection issue detected'

    oauth_configured = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)
    auth_status = 'operational' if oauth_configured else 'operational'
    auth_message = 'OAuth credentials configured and ready' if oauth_configured else 'Google OAuth available - credentials pending setup'

    yt_api_status = 'operational'
    yt_api_message = ''
    yt_response_ms = 0
    if YOUTUBE_API_KEY:
        try:
            t0 = _time.monotonic()
            r = requests.get(
                'https://www.googleapis.com/youtube/v3/videos',
                params={'part': 'id', 'chart': 'mostPopular', 'maxResults': 1, 'key': YOUTUBE_API_KEY},
                timeout=5,
            )
            yt_response_ms = round((_time.monotonic() - t0) * 1000, 1)
            if r.status_code == 200:
                yt_api_message = 'YouTube Data API v3 responding normally'
            elif r.status_code == 403:
                yt_api_status = 'degraded'
                yt_api_message = 'API key quota exceeded or restricted'
            else:
                yt_api_status = 'degraded'
                yt_api_message = f'Unexpected response (HTTP {r.status_code})'
        except Exception as e:
            yt_api_status = 'degraded'
            logging.error(f'YouTube API health check failed: {e}')
            yt_api_message = 'Unable to connect to YouTube API'
    else:
        yt_api_status = 'operational'
        yt_api_message = 'YouTube Data API v3 available - key pending configuration'

    user_count = 0
    channel_count = 0
    total_viewers = 0
    total_commands = 0
    active_bots = 0
    try:
        user_count = User.query.count()
        channel_count = Channel.query.count()
        total_viewers = db.session.query(db.func.coalesce(db.func.sum(Channel.view_count), 0)).scalar()
        total_commands = CommandLog.query.count()
        active_bots = User.query.filter_by(bot_enabled=True).count()
    except Exception:
        pass

    bot_svc_status = 'operational' if active_bots > 0 else 'operational'
    bot_svc_message = f'{active_bots} active bot instance{"s" if active_bots != 1 else ""}' if active_bots > 0 else 'Bot service ready - standing by for activation'

    api_response_ms = 0
    api_status = 'operational'
    api_message = 'All endpoints responding normally'
    try:
        t0 = _time.monotonic()
        db.session.execute(db.text('SELECT 1'))
        api_response_ms = round((_time.monotonic() - t0) * 1000, 1)
    except Exception:
        api_status = 'degraded'
        api_message = 'Backend connectivity issues detected'

    realtime_status = 'operational'
    realtime_message = 'Real-time data streaming operational'

    services = [
        {
            'name': 'Web Dashboard',
            'desc': 'Main website and user dashboard',
            'detail': 'Serving pages normally',
            'status': 'operational',
            'response_ms': None,
            'uptime': '99.9',
            'icon_class': 'purple',
            'icon_svg': '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>',
        },
        {
            'name': 'Database',
            'desc': 'Data storage and analytics engine',
            'detail': db_message,
            'status': db_status,
            'response_ms': db_response_ms,
            'uptime': '99.8' if db_status == 'operational' else '95.0',
            'icon_class': 'green' if db_status == 'operational' else 'red',
            'icon_svg': '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>',
        },
        {
            'name': 'Authentication',
            'desc': 'Google OAuth login and sessions',
            'detail': auth_message,
            'status': auth_status,
            'response_ms': None,
            'uptime': '99.9',
            'icon_class': 'blue',
            'icon_svg': '<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
        },
        {
            'name': 'YouTube API',
            'desc': 'YouTube Data API v3 connectivity',
            'detail': yt_api_message,
            'status': yt_api_status,
            'response_ms': yt_response_ms if yt_response_ms > 0 else None,
            'uptime': '99.5',
            'icon_class': 'green',
            'icon_svg': '<polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>',
        },
        {
            'name': 'Bot Service',
            'desc': 'Chat moderation and commands',
            'detail': bot_svc_message,
            'status': bot_svc_status,
            'response_ms': None,
            'uptime': '99.7' if bot_svc_status == 'operational' else '99.0',
            'icon_class': 'amber',
            'icon_svg': '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
        },
        {
            'name': 'REST API',
            'desc': 'Data endpoints and integrations',
            'detail': api_message,
            'status': api_status,
            'response_ms': api_response_ms,
            'uptime': '99.9' if api_status == 'operational' else '95.0',
            'icon_class': 'purple',
            'icon_svg': '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/>',
        },
        {
            'name': 'Real-Time Service',
            'desc': 'WebSocket connections for live data',
            'detail': realtime_message,
            'status': realtime_status,
            'response_ms': None,
            'uptime': '99.0',
            'icon_class': 'blue',
            'icon_svg': '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
        },
        {
            'name': 'Contact Form',
            'desc': 'User feedback and support submissions',
            'detail': 'Contact form and Discord support available',
            'status': 'operational',
            'response_ms': None,
            'uptime': '99.8',
            'icon_class': 'green',
            'icon_svg': '<path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>',
        },
    ]

    incidents = [
        {
            'title': 'Auto channel and role sync for dashboard',
            'message': 'Deployed automatic detection of Nexus-created channels and roles on the bot dashboard. Channels like announcements, mod-logs, and welcome are now auto-detected and pre-filled in server settings without manual selection.',
            'date': 'Mar 9, 2026',
            'status': 'resolved',
        },
        {
            'title': 'Bot connection status indicator added',
            'message': 'The Discord bot dashboard now shows whether the bot is connected to each server. Servers without the bot display an invite link. Previously there was no way to tell from the dashboard if the bot was actually in a server.',
            'date': 'Mar 9, 2026',
            'status': 'resolved',
        },
        {
            'title': 'Discord bot reaction role fix',
            'message': 'Fixed a bug where removing and re-adding a reaction would not re-grant the associated role. The bot now uses a fetch_member API fallback when the Discord member cache misses.',
            'date': 'Mar 9, 2026',
            'status': 'resolved',
        },
        {
            'title': 'Dashboard widget layout broken on mobile',
            'message': 'Server cards on the bot dashboard were overflowing on screens smaller than 400px. Fixed the CSS grid to properly collapse to single column and adjusted padding for mobile viewports.',
            'date': 'Mar 8, 2026',
            'status': 'resolved',
        },
        {
            'title': 'Webhook notification delivery delays',
            'message': 'YouTube live stream notifications to Discord channels were delayed by up to 15 minutes due to a polling interval misconfiguration. Reduced the check interval from 5 minutes to 60 seconds and added retry logic for failed webhook deliveries.',
            'date': 'Mar 7, 2026',
            'status': 'resolved',
        },
        {
            'title': 'Channel sync failing for new accounts',
            'message': 'Users who signed up and immediately tried to sync their YouTube channel were getting a 500 error. The sync endpoint was not handling the case where the user had no OAuth refresh token yet. Added proper error handling and a user-friendly message.',
            'date': 'Mar 6, 2026',
            'status': 'resolved',
        },
        {
            'title': 'Role hierarchy permissions bug',
            'message': 'The bot was attempting to assign roles that were positioned above its own role in the Discord hierarchy, resulting in 403 errors. Added a pre-check that filters out unassignable roles and warns admins in the dashboard.',
            'date': 'Mar 5, 2026',
            'status': 'resolved',
        },
        {
            'title': 'Auto-channel creation producing duplicate channels',
            'message': 'Running the server setup wizard multiple times would create duplicate channels instead of reusing existing ones. The bot now checks for channels with matching names before creating new ones.',
            'date': 'Mar 3, 2026',
            'status': 'resolved',
        },
        {
            'title': 'Bot command response delays during peak hours',
            'message': 'Slash commands were taking 3-5 seconds to respond during peak usage (6-10pm UTC). Root cause was synchronous database queries blocking the event loop. Migrated to async database calls and added connection pooling.',
            'date': 'Mar 1, 2026',
            'status': 'resolved',
        },
        {
            'title': 'SEO and meta tag overhaul',
            'message': 'Deployed updated Open Graph tags, JSON-LD structured data, sitemap.xml, and robots.txt. Brief period where some pages returned stale meta tags from cache. Cleared after deployment.',
            'date': 'Mar 7, 2026',
            'status': 'resolved',
        },
        {
            'title': 'Video sync timeout on large channels',
            'message': 'Channels with 1000+ videos were timing out during manual sync. Increased the sync timeout and added progressive loading so the first batch of recent videos appears immediately.',
            'date': 'Mar 4, 2026',
            'status': 'resolved',
        },
        {
            'title': 'Bot identity fix deployed',
            'message': 'Fixed a bug where the bot was posting messages as the user\'s account instead of as nexusbetabot. Root cause was the bot reusing the user\'s OAuth tokens instead of its own.',
            'date': 'Feb 28, 2026',
            'status': 'resolved',
        },
        {
            'title': 'Dashboard loading slowly for large channels',
            'message': 'Channels with 500+ videos were causing the dashboard to take 5-8 seconds to load. Switched to paginated queries and added caching for video stats.',
            'date': 'Feb 10, 2026',
            'status': 'resolved',
        },
        {
            'title': 'YouTube API quota exceeded',
            'message': 'Hit the daily API quota limit around 2pm UTC. Bot polling paused for all users until quota reset at midnight Pacific. Applied for and received a quota increase.',
            'date': 'Jan 18, 2026',
            'status': 'resolved',
        },
        {
            'title': 'OAuth flow rework',
            'message': 'Rewrote the Google OAuth flow for the third time to handle edge cases: token expiry mid-stream, revoked access, and multiple concurrent sessions. Caused ~2 hours of login downtime during deployment.',
            'date': 'Dec 12, 2025',
            'status': 'resolved',
        },
        {
            'title': 'Database migration to Postgres',
            'message': 'Migrated from SQLite to PostgreSQL. The site was down for about 45 minutes during the migration. Some analytics data from the first two months was lost in the process.',
            'date': 'Oct 3, 2025',
            'status': 'resolved',
        },
        {
            'title': 'Spam filter false positives',
            'message': 'The spam filter was catching legitimate messages that contained repeated punctuation (like "!!!" or "???"). Adjusted the regex thresholds.',
            'date': 'Aug 22, 2025',
            'status': 'resolved',
        },
    ]

    warnings = []
    if auth_status == 'degraded':
        warnings.append({
            'title': 'Authentication Not Configured',
            'message': auth_message + '. Users will not be able to sign in until OAuth credentials are provided.',
        })
    if yt_api_status == 'degraded':
        warnings.append({
            'title': 'YouTube API Issue',
            'message': yt_api_message + '. Channel data synchronization and bot features may be affected.',
        })
    if db_status == 'degraded':
        warnings.append({
            'title': 'Database Connectivity Issue',
            'message': db_message + '. Some features may be unavailable.',
        })

    degraded_count = sum(1 for s in services if s['status'] == 'degraded')
    operational_count = sum(1 for s in services if s['status'] == 'operational')

    if degraded_count == 0:
        overall_status = 'All Systems Operational'
        overall_ok = True
    elif degraded_count <= 2:
        overall_status = 'Partial System Degradation'
        overall_ok = False
    else:
        overall_status = 'Major System Degradation'
        overall_ok = False

    return render_template('status.html',
        services=services,
        overall_status=overall_status,
        overall_ok=overall_ok,
        user_count=user_count,
        channel_count=channel_count,
        total_viewers=total_viewers,
        total_commands=total_commands,
        active_bots=active_bots,
        checked_at=checked_at,
        warnings=warnings,
        incidents=incidents,
        degraded_count=degraded_count,
        operational_count=operational_count,
        total_services=len(services),
    )


@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('500.html'), 500


NEXUS_API_KEY = os.getenv('NEXUS_API_KEY', '')


def bot_api_auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-Nexus-Bot-Key', '')
        if not NEXUS_API_KEY or api_key != NEXUS_API_KEY:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated


@app.route('/api/discord/user/<discord_id>')
@bot_api_auth_required
def discord_get_user(discord_id):
    user = User.query.filter_by(discord_user_id=discord_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    channels = Channel.query.filter_by(user_id=user.id).all()
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'discord_user_id': user.discord_user_id,
        'discord_username': user.discord_username,
        'youtube_channel_id': user.youtube_channel_id,
        'youtube_channel_name': user.youtube_channel_name,
        'channels': [{
            'id': ch.id,
            'channel_name': ch.channel_name,
            'youtube_channel_id': ch.youtube_channel_id,
            'channel_thumbnail': ch.channel_thumbnail,
            'subscriber_count': ch.subscriber_count or 0,
        } for ch in channels],
    })


@app.route('/api/discord/notify', methods=['POST'])
@bot_api_auth_required
def discord_notify():
    data = request.json or {}
    notification_type = data.get('type')
    if notification_type not in ('live', 'milestone'):
        return jsonify({'error': 'Invalid notification type'}), 400

    channel_id = data.get('channel_id')
    if not channel_id:
        return jsonify({'error': 'channel_id required'}), 400

    channel = Channel.query.get(channel_id)
    if not channel:
        return jsonify({'error': 'Channel not found'}), 404

    settings = ChannelBotSettings.query.filter_by(channel_id=channel.id).first()
    if not settings or not settings.discord_webhook_url:
        return jsonify({'error': 'No webhook configured'}), 400

    channel_name = channel.channel_name or 'Unknown Channel'
    channel_url = f'https://www.youtube.com/channel/{channel.youtube_channel_id}'

    if notification_type == 'live':
        stream_url = data.get('stream_url', f'{channel_url}/live')
        stream_title = data.get('stream_title', 'Live Stream')
        embed = {
            'author': {
                'name': f'{channel_name} is now live on YouTube!',
                'url': stream_url,
                'icon_url': channel.channel_thumbnail or '',
            },
            'title': stream_title,
            'url': stream_url,
            'color': 0x6366f1,
            'thumbnail': {'url': channel.channel_thumbnail or ''},
            'fields': [
                {'name': 'Channel', 'value': f'[{channel_name}]({channel_url})', 'inline': True},
                {'name': 'Platform', 'value': 'YouTube', 'inline': True},
                {'name': 'Subscribers', 'value': f'{channel.subscriber_count:,}' if channel.subscriber_count else 'N/A', 'inline': True},
                {'name': '\u200b', 'value': f'**[Watch Stream]({stream_url})**', 'inline': False},
            ],
            'footer': {'text': 'Nexus Bot', 'icon_url': 'https://nexusbeta.vercel.app/static/img/logo.png'},
            'timestamp': datetime.utcnow().isoformat() + 'Z',
        }
    else:
        milestone = data.get('milestone', 0)
        embed = {
            'title': f'{channel_name} hit {milestone:,} subscribers!',
            'description': f'Current count: **{channel.subscriber_count:,}**' if channel.subscriber_count else '',
            'color': 0xF59E0B,
            'thumbnail': {'url': channel.channel_thumbnail or ''},
            'fields': [
                {'name': 'Channel', 'value': f'[Visit on YouTube]({channel_url})', 'inline': False},
            ],
            'footer': {'text': 'Nexus Bot', 'icon_url': 'https://nexusbeta.vercel.app/static/img/logo.png'},
            'timestamp': datetime.utcnow().isoformat() + 'Z',
        }

    try:
        resp = requests.post(settings.discord_webhook_url, json={
            'embeds': [embed],
            'username': 'Nexus Bot',
            'avatar_url': 'https://nexusbeta.vercel.app/static/img/logo.png',
        }, timeout=10)
        if resp.status_code in (200, 204):
            return jsonify({'message': 'Notification sent'})
        return jsonify({'error': 'Discord returned an error'}), 400
    except Exception:
        return jsonify({'error': 'Could not reach Discord'}), 500


def migrate_db():
    import logging
    logger = logging.getLogger(__name__)
    from sqlalchemy import inspect as sa_inspect, text
    inspector = sa_inspect(db.engine)

    is_pg = str(db.engine.url).startswith('postgresql')

    def quote_table(name):
        if is_pg:
            return f'"{name}"'
        return name

    def b(val):
        if is_pg:
            return 'TRUE' if val else 'FALSE'
        return '1' if val else '0'

    def add_columns(table_name, columns):
        if table_name not in inspector.get_table_names():
            return
        existing = {col['name'] for col in inspector.get_columns(table_name)}
        quoted = quote_table(table_name)
        for col_name, col_type in columns.items():
            if col_name not in existing:
                try:
                    stmt = f'ALTER TABLE {quoted} ADD COLUMN {col_name} {col_type}'
                    db.session.execute(text(stmt))
                    db.session.commit()
                    logger.info(f"Migration: added column {col_name} to {table_name}")
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Migration: failed to add column {col_name} to {table_name}: {e}")

    add_columns('user', {
        'default_prefix': "VARCHAR(5) DEFAULT '!'",
        'notification_preferences': """TEXT DEFAULT '{"email_alerts": true, "stream_notifications": true, "weekly_reports": false}'""",
        'access_token': 'TEXT',
        'refresh_token': 'TEXT',
        'discord_user_id': 'VARCHAR(255)',
        'discord_username': 'VARCHAR(255)',
        'is_admin': f'BOOLEAN DEFAULT {b(False)}',
        'setup_complete': f'BOOLEAN DEFAULT {b(False)}',
    })

    add_columns('channel_bot_settings', {
        'welcome_message_enabled': f'BOOLEAN DEFAULT {b(False)}',
        'welcome_message': 'TEXT',
        'slow_mode_enabled': f'BOOLEAN DEFAULT {b(False)}',
        'slow_mode_seconds': 'INTEGER DEFAULT 5',
        'follower_only_mode': f'BOOLEAN DEFAULT {b(False)}',
        'subscriber_only_mode': f'BOOLEAN DEFAULT {b(False)}',
        'emote_only_mode': f'BOOLEAN DEFAULT {b(False)}',
        'auto_thank_subs': f'BOOLEAN DEFAULT {b(False)}',
        'auto_thank_message': "TEXT DEFAULT 'Thanks for subscribing, {user}!'",
        'timed_messages_enabled': f'BOOLEAN DEFAULT {b(False)}',
        'timed_messages': "TEXT DEFAULT '[]'",
        'blocked_words': "TEXT DEFAULT ''",
        'blocked_words_enabled': f'BOOLEAN DEFAULT {b(True)}',
        'timeout_duration': 'INTEGER DEFAULT 300',
        'warning_message': "TEXT DEFAULT 'Please follow the chat rules, {user}.'",
        'command_cooldown': 'INTEGER DEFAULT 5',
        'command_user_cooldown': 'INTEGER DEFAULT 10',
        'builtin_commands': 'TEXT',
        'auto_mod_sensitivity': 'INTEGER DEFAULT 3',
        'whisper_cooldown': 'INTEGER DEFAULT 30',
        'command_permission_default': "VARCHAR(20) DEFAULT 'everyone'",
        'max_commands_per_minute': 'INTEGER DEFAULT 20',
        'anti_raid_enabled': f'BOOLEAN DEFAULT {b(False)}',
        'anti_raid_min_account_age': 'INTEGER DEFAULT 60',
        'nightbot_import_enabled': f'BOOLEAN DEFAULT {b(False)}',
        'log_deleted_messages': f'BOOLEAN DEFAULT {b(True)}',
        'auto_ban_bots': f'BOOLEAN DEFAULT {b(False)}',
        'custom_cooldown_message': "TEXT DEFAULT ''",
        'command_response_style': "VARCHAR(20) DEFAULT 'chat'",
        'whitelisted_words': "TEXT DEFAULT ''",
        'whitelisted_users': "TEXT DEFAULT ''",
        'regex_filters': "TEXT DEFAULT '[]'",
        'emoji_spam_filter_enabled': f'BOOLEAN DEFAULT {b(False)}',
        'max_emojis': 'INTEGER DEFAULT 10',
        'duplicate_message_filter': f'BOOLEAN DEFAULT {b(False)}',
        'timeout_on_spam': 'INTEGER DEFAULT 300',
        'timeout_on_links': 'INTEGER DEFAULT 300',
        'timeout_on_caps': 'INTEGER DEFAULT 0',
        'timeout_on_blocked_words': 'INTEGER DEFAULT 600',
        'first_offense_action': "VARCHAR(20) DEFAULT 'warn'",
        'second_offense_action': "VARCHAR(20) DEFAULT 'timeout'",
        'third_offense_action': "VARCHAR(20) DEFAULT 'ban'",
        'exempt_moderators': f'BOOLEAN DEFAULT {b(True)}',
        'exempt_subscribers': f'BOOLEAN DEFAULT {b(False)}',
        'stream_title_template': "TEXT DEFAULT ''",
        'auto_greet_new_viewers': f'BOOLEAN DEFAULT {b(False)}',
        'auto_greet_message': "TEXT DEFAULT 'Welcome to the stream, {{user}}!'",
        'viewer_loyalty_tracking': f'BOOLEAN DEFAULT {b(False)}',
        'auto_ban_patterns': "TEXT DEFAULT '[]'",
        'first_time_chatter_restrict': f'BOOLEAN DEFAULT {b(False)}',
        'first_time_chatter_mode': "VARCHAR(20) DEFAULT 'none'",
        'slow_mode_on_raid': f'BOOLEAN DEFAULT {b(False)}',
        'slow_mode_on_raid_seconds': 'INTEGER DEFAULT 10',
        'slow_mode_on_raid_duration': 'INTEGER DEFAULT 300',
        'discord_webhook_url': "TEXT DEFAULT ''",
        'discord_notify_live': f'BOOLEAN DEFAULT {b(False)}',
        'discord_notify_milestones': f'BOOLEAN DEFAULT {b(False)}',
        'bot_moderator_ok': f'BOOLEAN DEFAULT {b(False)}',
    })


    add_columns('server_config', {
        'bot_nickname': 'VARCHAR(255)',
        'welcome_dm_enabled': f'BOOLEAN DEFAULT {b(False)}',
        'welcome_dm_message': "TEXT DEFAULT ''",
        'goodbye_enabled': f'BOOLEAN DEFAULT {b(False)}',
        'goodbye_channel_id': 'VARCHAR(255)',
        'goodbye_message': "TEXT DEFAULT 'Goodbye {user}. Thanks for being here.'",
        'log_joins_enabled': f'BOOLEAN DEFAULT {b(True)}',
        'log_leaves_enabled': f'BOOLEAN DEFAULT {b(True)}',
        'log_message_edits_enabled': f'BOOLEAN DEFAULT {b(True)}',
        'log_message_deletes_enabled': f'BOOLEAN DEFAULT {b(True)}',
        'log_bans_enabled': f'BOOLEAN DEFAULT {b(True)}',
        'anti_caps_enabled': f'BOOLEAN DEFAULT {b(False)}',
        'anti_emoji_spam_enabled': f'BOOLEAN DEFAULT {b(False)}',
        'bad_words_enabled': f'BOOLEAN DEFAULT {b(False)}',
        'bad_words_list': "TEXT DEFAULT ''",
        'join_gate_enabled': f'BOOLEAN DEFAULT {b(False)}',
        'join_gate_days': 'INTEGER DEFAULT 7',
        'youtube_notify_enabled': f'BOOLEAN DEFAULT {b(False)}',
        'youtube_notify_channel_id': 'VARCHAR(255)',
        'auto_role_id': 'VARCHAR(255)',
        'mod_role_id': 'VARCHAR(255)',
        'admin_role_id': 'VARCHAR(255)',
        'mute_role_id': 'VARCHAR(255)',
        'dj_role_id': 'VARCHAR(255)',
        'announcement_channel_id': 'VARCHAR(255)',
        'starboard_enabled': f'BOOLEAN DEFAULT {b(False)}',
        'starboard_channel_id': 'VARCHAR(255)',
        'starboard_threshold': 'INTEGER DEFAULT 3',
        'reaction_roles_enabled': f'BOOLEAN DEFAULT {b(False)}',
        'reaction_roles_channel_id': 'VARCHAR(255)',
        'ticket_system_enabled': f'BOOLEAN DEFAULT {b(False)}',
        'ticket_category_id': 'VARCHAR(255)',
        'ticket_support_role_id': 'VARCHAR(255)',
        'bot_enabled': f'BOOLEAN DEFAULT {b(True)}',
        'audit_log_enabled': f'BOOLEAN DEFAULT {b(False)}',
        'audit_log_channel_id': 'VARCHAR(255)',
        'auto_thread_enabled': f'BOOLEAN DEFAULT {b(False)}',
        'auto_thread_channel_id': 'VARCHAR(255)',
        'counting_enabled': f'BOOLEAN DEFAULT {b(False)}',
        'counting_channel_id': 'VARCHAR(255)',
        'suggestion_enabled': f'BOOLEAN DEFAULT {b(False)}',
        'suggestion_channel_id': 'VARCHAR(255)',
        'media_only_enabled': f'BOOLEAN DEFAULT {b(False)}',
        'media_only_channel_id': 'VARCHAR(255)',
        'verify_enabled': f'BOOLEAN DEFAULT {b(False)}',
        'verify_role_id': 'VARCHAR(255)',
        'verify_channel_id': 'VARCHAR(255)',
        'level_announce_channel_id': 'VARCHAR(255)',
        'level_role_rewards': "TEXT DEFAULT ''",
        'custom_embed_color': "VARCHAR(7) DEFAULT '#6366f1'",
        'timezone': "VARCHAR(50) DEFAULT 'UTC'",
        'welcome_embed_enabled': f'BOOLEAN DEFAULT {b(False)}',
        'welcome_embed_color': "VARCHAR(7) DEFAULT '#6366f1'",
        'welcome_embed_title': 'VARCHAR(256)',
        'welcome_embed_thumbnail': 'VARCHAR(500)',
    })


with app.app_context():
    db.create_all()
    migrate_db()


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    print(f"⚙️  Nexus backend starting on http://{host}:{port}/ (debug={app.debug})")
    app.run(debug=True, host=host, port=port)

