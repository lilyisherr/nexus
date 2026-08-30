#!/usr/bin/env python3

import os
import sys
import subprocess
from pathlib import Path


def start_discord_bot(project_root):
    if not os.getenv('DISCORD_BOT_TOKEN') or os.getenv('NEXUS_DISABLE_AUTO_BOT') == '1':
        return None

    bot_path = project_root / 'discord_bot'
    bot_file = bot_path / 'bot.py'
    if not bot_file.exists():
        print('⚠️  Discord bot entry point not found; starting website only.')
        return None

    print('🤖 Starting Discord bot alongside the website...')
    return subprocess.Popen([sys.executable, 'bot.py'], cwd=bot_path, env=os.environ.copy())

def main():
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║  NEXUS - Professional YouTube Analytics Platform          ║
    ║  Web Dashboard & Bot Management                            ║
    ║  Version 1.0 Beta                                          ║
    ╚════════════════════════════════════════════════════════════╝
    """)

    backend_path = Path(__file__).parent / "website" / "backend"
    project_root = Path(__file__).parent

    if not backend_path.exists():
        print("❌ Error: website/backend directory not found!")
        sys.exit(1)

    try:
        import flask
        import flask_sqlalchemy
        print("✅ Dependencies found")
    except ImportError:
        print("❌ Dependencies not installed!")
        print("\nRun this to install:")
        print("   pip install -r website/backend/requirements.txt")
        sys.exit(1)

    env_file = backend_path / ".env"
    if not env_file.exists():
        print("⚠️  .env file not found!")
        print("\nRun the setup wizard:")
        print("   cd website/backend")
        print("   python setup.py")
        print("   cd ../..")

    try:
        from dotenv import load_dotenv
        load_dotenv(env_file)
    except ImportError:
        pass

    print("\n🚀 Starting Nexus Web Server...")
    print("📱 Visit: http://localhost:5000 (or check PORT env var for custom port)")
    print("🛑 Press Ctrl+C to stop\n")

    bot_process = start_discord_bot(project_root)
    try:
        os.chdir(backend_path)
        subprocess.run([sys.executable, "app.py"], check=True)
    except KeyboardInterrupt:
        print("\n\n🛑 Nexus Web Server stopped by user")
        sys.exit(0)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
    finally:
        if bot_process and bot_process.poll() is None:
            print("\n🛑 Stopping Discord bot...")
            bot_process.terminate()
            try:
                bot_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                bot_process.kill()

if __name__ == "__main__":
    main()
