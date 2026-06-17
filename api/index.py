import sys
import os
import logging
import traceback

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Setup paths to locate backend and frontend folders
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_path = os.path.join(project_root, 'website', 'backend')
frontend_path = os.path.join(project_root, 'website', 'frontend')

sys.path.insert(0, backend_path)

os.environ.setdefault('VERCEL', '1')

# 1. Import the app globally so Vercel's scanner can detect it
try:
    from app import app, db, migrate_db
    logger.info("Flask app imported successfully")
except Exception as e:
    logger.error(f"Failed to import Flask app: {e}")
    traceback.print_exc()
    raise

# 2. Configure Database URI
db_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
if 'sqlite' in db_url:
    logger.warning("Using SQLite on Vercel - database operations will fail. Set DATABASE_URL env var.")
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tmp/nexus.db'

# 3. Handle database initialization and migrations
try:
    with app.app_context():
        db.create_all()
        migrate_db()
        logger.info("Database tables created and migrated successfully")
except Exception as e:
    logger.error(f"Database initialization failed: {e}")

# 4. Explicitly expose 'app' as a global variable for Vercel's routing handler
application = app
