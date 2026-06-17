import os
import sys
import time
import json
import logging
import pytz
import asyncio
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/youtube']

CLIENT_SECRET_STRING = """ {
  "installed": {
    "client_id": "145901399874-61setr1dtkobepvl6mu4cavb66iu9u2d.apps.googleusercontent.com",
    "project_id": "zonks-bot-9",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "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"
  }
} """

POLL_INTERVAL = 10
OFFLINE_CHECK_INTERVAL = 300
COMMAND_DELAY = 2

class CustomFormatter(logging.Formatter):
    def format(self, record):
        log_fmt = "[%(asctime)s] | %(levelname)-8s | %(message)s"
        formatter = logging.Formatter(log_fmt, datefmt='%Y-%m-%d %H:%M:%S')
        return formatter.format(record)

logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)

for handler in logging.root.handlers:
    handler.setFormatter(CustomFormatter())

logger = logging.getLogger()

class QuotaManager:
    def __init__(self, limit):
        self.limit = limit
        self.used = 0
        self.pacific_tz = pytz.timezone('US/Pacific')
        self.next_reset = self._get_next_reset()

    def _get_next_reset(self):
        now = datetime.now(self.pacific_tz)
        midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return midnight

    def check_reset(self):
        now = datetime.now(self.pacific_tz)
        if now >= self.next_reset:
            logger.info("Daily Quota Reset triggered (Midnight PT).")
            self.used = 0
            self.next_reset = self._get_next_reset()

    def add_cost(self, amount):
        self.used += amount
        if self.used >= self.limit:
            logger.warning(f"QUOTA LIMIT REACHED ({self.used}/{self.limit})!")
        return self.used < self.limit

quota = QuotaManager(110000)

def get_authenticated_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")
                creds = None

        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_config(json.loads(CLIENT_SECRET_STRING), SCOPES)
            
            flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
            
            auth_url, _ = flow.authorization_url(prompt='consent')
            
            print("-" * 60)
            print("GO TO THIS URL TO AUTHENTICATE:")
            print(auth_url)
            print("-" * 60)
            
            print("After selecting your account, Google will show you a code.")
            print("Copy that code and paste it below.")
            code = input("Enter the authorization code here: ")
            
            flow.fetch_token(code=code)
            creds = flow.credentials
            
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())

    return build('youtube', 'v3', credentials=creds)

def get_live_chat_id(youtube, channel_id):
    quota.add_cost(100)
    request = youtube.search().list(
        part="snippet",
        channelId=channel_id,
        eventType="live",
        type="video"
    )
    response = request.execute()

    if not response['items']:
        return None, None, None

    video_id = response['items'][0]['id']['videoId']
    title = response['items'][0]['snippet']['title']

    quota.add_cost(1)
    video_request = youtube.videos().list(
        part="liveStreamingDetails,snippet",
        id=video_id
    )
    video_response = video_request.execute()

    item = video_response['items'][0]
    chat_id = item.get('liveStreamingDetails', {}).get('activeLiveChatId')
    start_time_str = item.get('liveStreamingDetails', {}).get('actualStartTime')

    start_time = None
    if start_time_str:
        start_time = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC)

    return chat_id, title, start_time

def send_message(youtube, chat_id, text):
    quota.add_cost(50)
    try:
        youtube.liveChatMessages().insert(
            part="snippet",
            body={
                "snippet": {
                    "liveChatId": chat_id,
                    "type": "textMessageEvent",
                    "textMessageDetails": {
                        "messageText": text
                    }
                }
            }
        ).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        return False

async def bot_loop(youtube, channel_id):
    bot_name = "Nexus"
    is_live = False
    chat_id = None
    stream_start_time = None
    next_page_token = None

    while True:
        quota.check_reset()

        if not is_live:
            logger.info("Checking for stream status...")
            new_chat_id, stream_title, start_time = get_live_chat_id(youtube, channel_id)
            
            if new_chat_id:
                is_live = True
                chat_id = new_chat_id
                stream_start_time = start_time
                next_page_token = None
                
                logger.info(f"🔴 LIVE DETECTED: {stream_title}")
                logger.info(f"   Chat ID: {chat_id}")
                
                send_message(youtube, chat_id, f"🟢 {bot_name} is now online and watching the stream!")
                time.sleep(COMMAND_DELAY)
            else:
                logger.info("Channel is offline. Checking again in 5 minutes...")
                await asyncio.sleep(OFFLINE_CHECK_INTERVAL)
                continue

        try:
            quota.add_cost(1)
            request = youtube.liveChatMessages().list(
                liveChatId=chat_id,
                part="snippet,authorDetails",
                pageToken=next_page_token
            )
            response = request.execute()
            next_page_token = response.get('nextPageToken')
            polling_interval = response.get('pollingIntervalMillis', 2000) / 1000.0

            for item in response.get('items', []):
                msg = item['snippet']['displayMessage']
                author = item['authorDetails']['displayName']
                
                if msg.startswith('!'):
                    cmd = msg.split()[0].lower()
                    
                    if cmd == '!uptime':
                        if stream_start_time:
                            uptime_diff = datetime.now(pytz.UTC) - stream_start_time
                            hours, remainder = divmod(int(uptime_diff.total_seconds()), 3600)
                            minutes, seconds = divmod(remainder, 60)
                            send_message(youtube, chat_id, f"Stream Uptime: {hours}h {minutes}m {seconds}s")
                        else:
                            send_message(youtube, chat_id, "Stream uptime information is currently unavailable.")
                    
                    elif cmd == '!kill' and author.lower() == 'admin':
                        logger.info("Kill command received. Shutting down.")
                        os._exit(0)

            await asyncio.sleep(max(POLL_INTERVAL, polling_interval))

        except HttpError as e:
            if e.resp.status in [403, 404]:
                logger.warning("Stream ended or chat inaccessible.")
                is_live = False
                chat_id = None
                next_page_token = None
                logger.info(" **Stream Offline**")
            else:
                logger.error(f"API Error: {e}")
                await asyncio.sleep(POLL_INTERVAL)
        except Exception as e:
            logger.error(f"Loop Error: {e}")
            await asyncio.sleep(POLL_INTERVAL)

async def main():
    logger.info("Authenticating with YouTube...")
    channel_id = os.getenv('YOUTUBE_CHANNEL_ID')
    
    if not channel_id:
        print("Error: YOUTUBE_CHANNEL_ID environment variable not set")
        print("Please set it before running the bot: export YOUTUBE_CHANNEL_ID='your_channel_id'")
        sys.exit(1)
    
    logger.info("Authenticating with YouTube...")
    youtube = get_authenticated_service()
    logger.info("YouTube Authentication successful.")
    logger.info(f"Monitoring channel: {channel_id}")

    try:
        await bot_loop(youtube, channel_id)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception as e:
        logger.critical(f"Bot Loop crashed: {e}")

if __name__ == "__main__":
    asyncio.run(main())

