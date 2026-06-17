#!/usr/bin/env python3

import os
import sys
import subprocess
from pathlib import Path

def main():
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║  NEXUS - Professional YouTube Analytics Platform          ║
    ║  Web Dashboard & Bot Management                            ║
    ║  Version 1.0 Beta                                          ║
    ╚════════════════════════════════════════════════════════════╝
    """)

    backend_path = Path(__file__).parent / "website" / "backend"

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

    print("\n🚀 Starting Nexus Web Server...")
    print("📱 Visit: http://localhost:5000 (or check PORT env var for custom port)")
    print("🛑 Press Ctrl+C to stop\n")

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

if __name__ == "__main__":
    main()
