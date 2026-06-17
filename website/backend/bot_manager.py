import threading
import time
import json
import logging
import requests
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

POLL_INTERVAL = 10
OFFLINE_CHECK_INTERVAL = 30


class BotInstance:
    def __init__(self, channel_id, youtube_channel_id, access_token, refresh_token,
                 client_id, client_secret, bot_settings=None,
                 bot_access_token=None, bot_refresh_token=None):
        self.channel_id = channel_id
        self.youtube_channel_id = youtube_channel_id
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.bot_settings = bot_settings or {}
        self.bot_access_token = bot_access_token
        self.bot_refresh_token = bot_refresh_token
        self.running = False
        self.thread = None
        self.is_live = False
        self.chat_id = None
        self.stream_title = None
        self.stream_start_time = None
        self.messages_processed = 0
        self.last_error = None
        self.started_at = None
        self.command_cooldowns = {}

    def _refresh_access_token(self):
        if not self.refresh_token:
            return False
        try:
            resp = requests.post('https://oauth2.googleapis.com/token', data={
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'refresh_token': self.refresh_token,
                'grant_type': 'refresh_token'
            })
            if resp.status_code == 200:
                data = resp.json()
                self.access_token = data['access_token']
                return True
        except Exception as e:
            logger.error(f"Token refresh failed for channel {self.channel_id}: {e}")
        return False

    def _refresh_bot_access_token(self):
        if not self.bot_refresh_token:
            return False
        try:
            resp = requests.post('https://oauth2.googleapis.com/token', data={
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'refresh_token': self.bot_refresh_token,
                'grant_type': 'refresh_token'
            })
            if resp.status_code == 200:
                data = resp.json()
                self.bot_access_token = data['access_token']
                return True
        except Exception as e:
            logger.error(f"Bot token refresh failed for channel {self.channel_id}: {e}")
        return False

    def _api_headers(self):
        return {'Authorization': f'Bearer {self.access_token}'}

    def _bot_api_headers(self):
        token = self.bot_access_token if self.bot_access_token else self.access_token
        return {'Authorization': f'Bearer {token}'}

    def _find_live_stream(self):
        try:
            resp = requests.get(
                'https://www.googleapis.com/youtube/v3/search',
                params={
                    'part': 'snippet',
                    'channelId': self.youtube_channel_id,
                    'eventType': 'live',
                    'type': 'video'
                },
                headers=self._api_headers()
            )
            if resp.status_code == 401:
                if self._refresh_access_token():
                    return self._find_live_stream()
                return None, None, None, None

            if resp.status_code != 200:
                return None, None, None, None

            data = resp.json()
            if not data.get('items'):
                return None, None, None, None

            video_id = data['items'][0]['id']['videoId']
            title = data['items'][0]['snippet']['title']

            vid_resp = requests.get(
                'https://www.googleapis.com/youtube/v3/videos',
                params={'part': 'liveStreamingDetails,snippet', 'id': video_id},
                headers=self._api_headers()
            )
            if vid_resp.status_code != 200:
                return None, None, None, None

            vid_data = vid_resp.json()
            if not vid_data.get('items'):
                return None, None, None, None

            item = vid_data['items'][0]
            chat_id = item.get('liveStreamingDetails', {}).get('activeLiveChatId')
            start_str = item.get('liveStreamingDetails', {}).get('actualStartTime')
            start_time = None
            if start_str:
                start_time = datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%SZ")

            return chat_id, title, start_time, video_id
        except Exception as e:
            logger.error(f"Error finding live stream for channel {self.channel_id}: {e}")
            return None, None, None, None

    def _send_live_notification(self, stream_title, video_id):
        try:
            from app import app, db, Channel, ChannelBotSettings
            with app.app_context():
                channel = Channel.query.get(self.channel_id)
                if not channel:
                    return
                settings = ChannelBotSettings.query.filter_by(channel_id=self.channel_id).first()
                if not settings:
                    return
                webhook_url = settings.discord_webhook_url
                if not webhook_url or not settings.discord_notify_live:
                    return
                import re
                if not re.match(r'^https://(discord\.com|discordapp\.com)/api/webhooks/', webhook_url):
                    logger.warning(f"Invalid webhook URL for channel {self.channel_id}, skipping notification")
                    return
                stream_url = f'https://www.youtube.com/watch?v={video_id}'
                channel_name = channel.channel_name or 'Unknown Channel'
                channel_url = f'https://www.youtube.com/channel/{channel.youtube_channel_id}'
                embed = {
                    'author': {
                        'name': f'{channel_name} is now live on YouTube!',
                        'url': stream_url,
                        'icon_url': channel.channel_thumbnail or '',
                    },
                    'title': stream_title or 'Live Stream',
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
                resp = requests.post(webhook_url, json={
                    'embeds': [embed],
                    'username': 'Nexus Bot',
                    'avatar_url': 'https://nexusbeta.vercel.app/static/img/logo.png',
                }, timeout=10)
                if resp.status_code in (200, 204):
                    logger.info(f"Live notification sent for channel {self.channel_id}")
                else:
                    logger.warning(f"Live notification failed for channel {self.channel_id}: {resp.status_code}")
        except Exception as e:
            logger.error(f"Error sending live notification for channel {self.channel_id}: {e}")

    def _mark_moderator_ok(self):
        try:
            from app import app, db, ChannelBotSettings
            with app.app_context():
                settings = ChannelBotSettings.query.filter_by(channel_id=self.channel_id).first()
                if settings and not settings.bot_moderator_ok:
                    settings.bot_moderator_ok = True
                    db.session.commit()
        except Exception:
            pass

    def _send_message(self, text):
        try:
            resp = requests.post(
                'https://www.googleapis.com/youtube/v3/liveChat/messages',
                params={'part': 'snippet'},
                headers={**self._bot_api_headers(), 'Content-Type': 'application/json'},
                json={
                    'snippet': {
                        'liveChatId': self.chat_id,
                        'type': 'textMessageEvent',
                        'textMessageDetails': {'messageText': text}
                    }
                }
            )
            if resp.status_code == 401:
                if self.bot_access_token and self._refresh_bot_access_token():
                    return self._send_message(text)
                elif self._refresh_access_token():
                    return self._send_message(text)
            success = resp.status_code == 200
            if success:
                self._mark_moderator_ok()
            return success
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False

    def _poll_messages(self, page_token=None):
        try:
            params = {
                'liveChatId': self.chat_id,
                'part': 'snippet,authorDetails'
            }
            if page_token:
                params['pageToken'] = page_token

            resp = requests.get(
                'https://www.googleapis.com/youtube/v3/liveChat/messages',
                params=params,
                headers=self._api_headers()
            )
            if resp.status_code == 401:
                if self._refresh_access_token():
                    return self._poll_messages(page_token)
                return None, None, POLL_INTERVAL

            if resp.status_code in [403, 404]:
                return None, None, None

            if resp.status_code != 200:
                return [], page_token, POLL_INTERVAL

            data = resp.json()
            next_token = data.get('nextPageToken')
            interval = max(POLL_INTERVAL, data.get('pollingIntervalMillis', 2000) / 1000.0)
            return data.get('items', []), next_token, interval
        except Exception as e:
            logger.error(f"Poll error: {e}")
            return [], page_token, POLL_INTERVAL

    def _check_cooldown(self, command, user_id, per_cmd_cooldown=None):
        key = f"{command}:{user_id}"
        now = time.time()
        if per_cmd_cooldown is not None:
            cooldown = per_cmd_cooldown
        else:
            cooldown = self.bot_settings.get('command_user_cooldown', 10)
        if key in self.command_cooldowns:
            if now - self.command_cooldowns[key] < cooldown:
                return False
        self.command_cooldowns[key] = now
        return True

    def _apply_moderation(self, message, author):
        settings = self.bot_settings

        if settings.get('spam_filter_enabled', True):
            max_repeat = settings.get('max_repeat_chars', 5)
            if max_repeat > 0:
                for i in range(len(message) - max_repeat):
                    if len(set(message[i:i + max_repeat + 1])) == 1:
                        return 'spam'

            max_len = settings.get('max_message_length', 200)
            if max_len > 0 and len(message) > max_len:
                return 'too_long'

        if settings.get('caps_filter_enabled', True):
            max_caps = settings.get('max_caps_percent', 70)
            alpha_chars = [c for c in message if c.isalpha()]
            if len(alpha_chars) > 5:
                caps_pct = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars) * 100
                if caps_pct > max_caps:
                    return 'caps'

        if settings.get('link_filter_enabled', True):
            import re
            url_pattern = re.compile(r'https?://\S+|www\.\S+')
            if url_pattern.search(message):
                whitelist = settings.get('link_whitelist', '').split(',')
                whitelist = [w.strip().lower() for w in whitelist if w.strip()]
                for match in url_pattern.finditer(message):
                    url = match.group().lower()
                    if not any(domain in url for domain in whitelist):
                        return 'link'

        if settings.get('blocked_words_enabled', True):
            blocked = settings.get('blocked_words', '').split(',')
            blocked = [w.strip().lower() for w in blocked if w.strip()]
            msg_lower = message.lower()
            for word in blocked:
                if word in msg_lower:
                    return 'blocked_word'

        return None

    def _get_builtin_commands(self):
        raw = self.bot_settings.get('builtin_commands')
        if raw:
            if isinstance(raw, str):
                try:
                    return json.loads(raw)
                except Exception:
                    return []
            if isinstance(raw, list):
                return raw
        return []

    def _process_builtin_command(self, cmd_name, cmd_config, author, parts):
        template = cmd_config.get('response_template', '')

        if cmd_name == 'uptime':
            if self.stream_start_time:
                diff = datetime.utcnow() - self.stream_start_time
                hours, remainder = divmod(int(diff.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                uptime_str = f"{hours}h {minutes}m {seconds}s"
                response = template.replace('{uptime}', uptime_str) if template else f"Stream has been live for {uptime_str}."
            else:
                response = "Stream uptime unavailable."
        elif cmd_name == 'title':
            title = self.stream_title or 'Unknown'
            response = template.replace('{title}', title) if template else f"Stream title: {title}"
        elif cmd_name == 'game':
            response = template.replace('{game}', self.stream_title or 'Unknown') if template else f"Currently playing: {self.stream_title or 'Unknown'}"
        elif cmd_name == 'commands':
            cmd_list = self._build_command_list()
            response = template.replace('{command_list}', cmd_list) if template else f"Commands: {cmd_list}"
        else:
            response = template.replace('{user}', author)
            response = response.replace('{target}', ' '.join(parts[1:]) if len(parts) > 1 else author)
            response = response.replace('{channel}', self.stream_title or '')

        if response:
            self._send_message(response)

    def _build_command_list(self):
        prefix = self.bot_settings.get('chat_prefix', '!')
        cmds = []
        for bc in self._get_builtin_commands():
            if bc.get('enabled', True):
                cmds.append(f"{prefix}{bc['name']}")
        custom_commands = self._get_custom_commands()
        for k in custom_commands:
            trigger = k if k.startswith(prefix) else f"{prefix}{k}"
            cmds.append(trigger)
        return ', '.join(cmds)

    def _get_custom_commands(self):
        raw = self.bot_settings.get('custom_commands', '{}')
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except Exception:
                return {}
        if isinstance(raw, dict):
            return raw
        return {}

    def _process_command(self, message, author, author_id):
        prefix = self.bot_settings.get('chat_prefix', '!')
        if not message.startswith(prefix):
            return

        parts = message[len(prefix):].split()
        if not parts:
            return
        cmd = parts[0].lower()

        builtin_cmds = self._get_builtin_commands()
        builtin_map = {bc['name']: bc for bc in builtin_cmds}

        if cmd in builtin_map:
            bc = builtin_map[cmd]
            if not bc.get('enabled', True):
                return
            cmd_cooldown = bc.get('cooldown', 10)
            if not self._check_cooldown(cmd, author_id, per_cmd_cooldown=cmd_cooldown):
                return
            self._process_builtin_command(cmd, bc, author, parts)
            return

        custom_commands = self._get_custom_commands()

        full_cmd = f"{prefix}{cmd}"
        cmd_data = custom_commands.get(cmd) or custom_commands.get(full_cmd)
        if cmd_data:
            if isinstance(cmd_data, dict):
                cmd_cooldown = cmd_data.get('cooldown')
                response = cmd_data.get('response', '')
            else:
                cmd_cooldown = None
                response = str(cmd_data)

            if not self._check_cooldown(cmd, author_id, per_cmd_cooldown=cmd_cooldown):
                return

            response = response.replace('{user}', author).replace('{channel}', self.stream_title or '')
            if response:
                self._send_message(response)

    def _run(self):
        self.started_at = datetime.utcnow()
        logger.info(f"Bot starting for channel {self.channel_id} ({self.youtube_channel_id})")
        page_token = None

        while self.running:
            try:
                if not self.is_live:
                    chat_id, title, start_time, video_id = self._find_live_stream()
                    if chat_id:
                        self.is_live = True
                        self.chat_id = chat_id
                        self.stream_title = title
                        self.stream_start_time = start_time
                        page_token = None
                        logger.info(f"Live stream detected: {title}")

                        if video_id:
                            threading.Thread(
                                target=self._send_live_notification,
                                args=(title, video_id),
                                daemon=True
                            ).start()

                        join_msg = self.bot_settings.get('join_message')
                        if join_msg:
                            time.sleep(self.bot_settings.get('response_delay', 2))
                            self._send_message(join_msg)
                    else:
                        time.sleep(OFFLINE_CHECK_INTERVAL)
                        continue

                items, page_token, interval = self._poll_messages(page_token)

                if interval is None:
                    logger.info(f"Stream ended for channel {self.channel_id}")
                    self.is_live = False
                    self.chat_id = None
                    self.stream_title = None
                    self.stream_start_time = None
                    continue

                if items:
                    for item in items:
                        self.messages_processed += 1
                        msg = item['snippet']['displayMessage']
                        author = item['authorDetails']['displayName']
                        author_id = item['authorDetails']['channelId']

                        violation = self._apply_moderation(msg, author)
                        if violation:
                            warning = self.bot_settings.get('warning_message', 'Please follow the chat rules, {user}.')
                            warning = warning.replace('{user}', author)
                            self._send_message(warning)
                            continue

                        self._process_command(msg, author, author_id)

                time.sleep(interval)

            except Exception as e:
                self.last_error = str(e)
                logger.error(f"Bot error for channel {self.channel_id}: {e}")
                time.sleep(POLL_INTERVAL)

        logger.info(f"Bot stopped for channel {self.channel_id}")

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        self.is_live = False
        self.chat_id = None

    def get_status(self):
        return {
            'running': self.running,
            'is_live': self.is_live,
            'stream_title': self.stream_title,
            'messages_processed': self.messages_processed,
            'last_error': self.last_error,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'channel_id': self.channel_id
        }


class BotManager:
    def __init__(self):
        self.instances = {}
        self._lock = threading.Lock()

    def start_bot(self, channel_id, youtube_channel_id, access_token, refresh_token,
                  client_id, client_secret, bot_settings=None,
                  bot_access_token=None, bot_refresh_token=None):
        with self._lock:
            if channel_id in self.instances:
                self.instances[channel_id].stop()

            instance = BotInstance(
                channel_id=channel_id,
                youtube_channel_id=youtube_channel_id,
                access_token=access_token,
                refresh_token=refresh_token,
                client_id=client_id,
                client_secret=client_secret,
                bot_settings=bot_settings,
                bot_access_token=bot_access_token,
                bot_refresh_token=bot_refresh_token
            )
            instance.start()
            self.instances[channel_id] = instance
            return instance.get_status()

    def stop_bot(self, channel_id):
        with self._lock:
            if channel_id in self.instances:
                self.instances[channel_id].stop()
                del self.instances[channel_id]
                return True
            return False

    def get_status(self, channel_id):
        with self._lock:
            if channel_id in self.instances:
                return self.instances[channel_id].get_status()
            return {'running': False, 'is_live': False, 'channel_id': channel_id}

    def get_all_status(self):
        with self._lock:
            return {cid: inst.get_status() for cid, inst in self.instances.items()}

    def update_settings(self, channel_id, bot_settings):
        with self._lock:
            if channel_id in self.instances:
                self.instances[channel_id].bot_settings = bot_settings

    def is_running(self, channel_id):
        with self._lock:
            return channel_id in self.instances and self.instances[channel_id].running


bot_manager = BotManager()
