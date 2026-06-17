#!/usr/bin/env python3

import os
import sys
import subprocess

def main():
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║  NEXUS - Professional YouTube Bot Platform                ║
    ║  Version 1.0 Beta                                          ║
    ╚════════════════════════════════════════════════════════════╝
    """)

    channel_id = os.getenv('YOUTUBE_CHANNEL_ID')

    if not channel_id:
        print("❌ ERROR: YOUTUBE_CHANNEL_ID environment variable not set!\n")
        print("To run the Nexus bot, set your YouTube channel ID:")
        print("\n   Linux/Mac:")
        print("   export YOUTUBE_CHANNEL_ID='UCxxxxxxxxxxxxx'")
        print("   python main.py")
        print("\n   Windows:")
        print("   set YOUTUBE_CHANNEL_ID=UCxxxxxxxxxxxxx")
        print("   python main.py")
        print("\nFind your channel ID at: https://www.youtube.com/channel_id")
        sys.exit(1)

    print(f"✅ Channel ID: {channel_id}")
    print("🚀 Starting Nexus Bot...\n")

    try:
        import asyncio
        from main import main as bot_main
        asyncio.run(bot_main())
    except ImportError:
        print("❌ Failed to import bot module")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Nexus Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
