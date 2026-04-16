from utils.db import get_supabase
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("db_sync")

def sync_db():
    sb = get_supabase()
    
    # We use a trick: try to select the column. If it fails, add it.
    # Note: supabase-py doesn't have a direct 'execute raw sql' command easily accessible 
    # without going through a custom RPC.
    # However, we can use the 'rpc' method if the user has created an 'exec_sql' function.
    
    logger.info("Checking database schema synchronization...")
    
    tables_to_check = {
        "workers": ["platform", "gig_score", "is_on_shift", "last_seen_at"],
        "policies": ["premium_paid", "is_active"],
        "claims": ["hour_of_day", "day_of_week", "shift"]
    }

    # For a hackathon, we'll try to use the RPC if it exists, 
    # but most likely we'll just have to advise the user to run the schema.sql.
    
    # Let's try to detect if platform exists
    try:
        sb.table("workers").select("platform").limit(1).execute()
        logger.info("Column 'platform' exists. Database seems synced.")
    except Exception as e:
        logger.error(f"Schema mismatch detected: {e}")
        logger.info("ADVICE: Please run 'backend/database/schema.sql' in your Supabase SQL Editor.")

if __name__ == "__main__":
    sync_db()
