#!/usr/bin/env python3

import os
import sys
import json
from pathlib import Path

def print_header():
    print("\n" + "="*60)
    print("  NEXUS - Professional YouTube Bot Platform")
    print("  Configuration Wizard - Beta v1.0")
    print("="*60 + "\n")

def print_section(title):
    print(f"\n▶ {title}")
    print("-" * 50)

def get_input(prompt, default=None):
    if default:
        prompt += f" [{default}]: "
    else:
        prompt += ": "

    value = input(prompt).strip()
    return value or default

def setup_google_oauth():
    print_section("Google OAuth 2.0 Setup")
    print("""
    To set up Google OAuth:
    1. Go to https://console.cloud.google.com/
    2. Create a new project or select existing
    3. Enable "YouTube Data API v3" and "Google+ API"
    4. Go to "Credentials" and create OAuth 2.0 ID
    5. Add authorized redirect URI: http://localhost:5000/auth/callback
       (Note: Change 5000 to match your PORT environment variable if different)
    6. Copy the Client ID and Client Secret
    """)

    client_id = get_input("Google Client ID")
    client_secret = get_input("Google Client Secret")

    if not client_id or not client_secret:
        print("❌ Google OAuth configuration incomplete!")
        return False

    print("✅ Google OAuth configured")
    return client_id, client_secret

def setup_youtube_api():
    print_section("YouTube API Key Setup")
    print("""
    To get a YouTube API Key:
    1. Go to https://console.cloud.google.com/
    2. Select your project
    3. Go to "Credentials"
    4. Create a new "API Key"
    5. Copy the key
    """)

    api_key = get_input("YouTube API Key")

    if not api_key:
        print("❌ YouTube API Key not provided!")
        return False

    print("✅ YouTube API Key configured")
    return api_key

def setup_database():
    print_section("Database Configuration")

    db_type = get_input(
        "Database type (sqlite/postgresql)",
        default="sqlite"
    )

    if db_type == "sqlite":
        db_url = "sqlite:///nexus.db"
        print(f"✅ Using SQLite: {db_url}")
    elif db_type == "postgresql":
        user = get_input("PostgreSQL Username", default="nexus")
        password = get_input("PostgreSQL Password")
        host = get_input("PostgreSQL Host", default="localhost")
        port = get_input("PostgreSQL Port", default="5432")
        dbname = get_input("Database Name", default="nexus")

        db_url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        print(f"✅ Configured PostgreSQL")
    else:
        db_url = "sqlite:///nexus.db"
        print(f"⚠️  Unknown DB type, defaulting to SQLite")

    return db_url

def create_env_file(client_id, client_secret, api_key, db_url):
    print_section("Creating .env file")

    env_content = f"""FLASK_ENV=development
SECRET_KEY=nexus-{os.urandom(16).hex()}

DATABASE_URL={db_url}

GOOGLE_CLIENT_ID={client_id}
GOOGLE_CLIENT_SECRET={client_secret}
GOOGLE_REDIRECT_URI=http://localhost:5000/auth/callback

YOUTUBE_API_KEY={api_key}
"""

    env_file = Path(__file__).parent / ".env"
    env_file.write_text(env_content)

    print(f"✅ Created .env file: {env_file}")
    return env_file

def main():
    print_header()

    if not Path("app.py").exists():
        print("❌ Error: app.py not found!")
        print("Please run this script from the website/backend directory")
        sys.exit(1)

    print("Welcome to Nexus Configuration Wizard!")
    print("\nThis will help you set up your Nexus instance.\n")

    oauth_result = setup_google_oauth()
    if not oauth_result:
        sys.exit(1)
    client_id, client_secret = oauth_result

    api_key = setup_youtube_api()
    if not api_key:
        sys.exit(1)

    db_url = setup_database()

    create_env_file(client_id, client_secret, api_key, db_url)

    print_section("Setup Complete!")
    print("""
    ✅ Configuration saved to .env

    Next steps:
    1. Start the Flask server:
       python app.py

    2. Visit http://localhost:5000

    3. Test the bot with:
       export YOUTUBE_CHANNEL_ID='your-channel-id'
       python ../../main.py

    For more information, see SETUP_GUIDE.md
    """)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during setup: {e}")
        sys.exit(1)
