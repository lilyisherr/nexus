import sys
import os
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_path = os.path.join(project_root, 'website', 'backend')
frontend_path = os.path.join(project_root, 'website', 'frontend')

sys.path.insert(0, backend_path)

os.environ.setdefault('VERCEL', '1')

try:
    from app import app, db, migrate_db
    logger.info("Flask app imported successfully")

    db_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if 'sqlite' in db_url:
        logger.warning("Using SQLite on Vercel - database operations will fail. Set DATABASE_URL env var.")
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tmp/nexus.db'

    try:
        with app.app_context():
            db.create_all()
            migrate_db()
            logger.info("Database tables created and migrated successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

except Exception as e:
    logger.error(f"Failed to import Flask app: {e}")
    import traceback
    traceback.print_exc()
    raise
