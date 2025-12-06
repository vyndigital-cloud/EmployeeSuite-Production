"""
Database Migration: Add shop_id, charge_id, and uninstalled_at to shopify_stores table
Safe migration - adds nullable columns
"""
import os
from app import app, db
from logging_config import logger

def migrate_shopify_store_columns():
    """Add new columns to shopify_stores table"""
    with app.app_context():
        try:
            # Check if shop_id column exists
            result = db.session.execute(db.text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='shopify_stores' AND column_name='shop_id'
            """))
            
            if not result.fetchone():
                logger.info("Adding shop_id column to shopify_stores table...")
                try:
                    db.session.execute(db.text("""
                        ALTER TABLE shopify_stores 
                        ADD COLUMN shop_id BIGINT
                    """))
                    logger.info("✅ shop_id column added successfully")
                except Exception as e:
                    if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                        logger.info("✅ shop_id column already exists")
                    else:
                        logger.warning(f"Could not add shop_id column: {e}")
                        db.session.rollback()
            else:
                logger.info("✅ shop_id column already exists")
            
            # Check if charge_id column exists
            result = db.session.execute(db.text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='shopify_stores' AND column_name='charge_id'
            """))
            
            if not result.fetchone():
                logger.info("Adding charge_id column to shopify_stores table...")
                try:
                    db.session.execute(db.text("""
                        ALTER TABLE shopify_stores 
                        ADD COLUMN charge_id VARCHAR(255)
                    """))
                    logger.info("✅ charge_id column added successfully")
                except Exception as e:
                    if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                        logger.info("✅ charge_id column already exists")
                    else:
                        logger.warning(f"Could not add charge_id column: {e}")
                        db.session.rollback()
            else:
                logger.info("✅ charge_id column already exists")
            
            # Check if uninstalled_at column exists
            result = db.session.execute(db.text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='shopify_stores' AND column_name='uninstalled_at'
            """))
            
            if not result.fetchone():
                logger.info("Adding uninstalled_at column to shopify_stores table...")
                try:
                    db.session.execute(db.text("""
                        ALTER TABLE shopify_stores 
                        ADD COLUMN uninstalled_at TIMESTAMP
                    """))
                    logger.info("✅ uninstalled_at column added successfully")
                except Exception as e:
                    if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                        logger.info("✅ uninstalled_at column already exists")
                    else:
                        logger.warning(f"Could not add uninstalled_at column: {e}")
                        db.session.rollback()
            else:
                logger.info("✅ uninstalled_at column already exists")
            
            # Add indexes for new columns
            try:
                # Check if shop_id index exists
                result = db.session.execute(db.text("""
                    SELECT indexname 
                    FROM pg_indexes 
                    WHERE tablename='shopify_stores' AND indexname='ix_shopify_stores_shop_id'
                """))
                if not result.fetchone():
                    logger.info("Adding index for shop_id...")
                    db.session.execute(db.text("""
                        CREATE INDEX ix_shopify_stores_shop_id ON shopify_stores(shop_id)
                    """))
                    logger.info("✅ shop_id index added")
                
                # Check if charge_id index exists
                result = db.session.execute(db.text("""
                    SELECT indexname 
                    FROM pg_indexes 
                    WHERE tablename='shopify_stores' AND indexname='ix_shopify_stores_charge_id'
                """))
                if not result.fetchone():
                    logger.info("Adding index for charge_id...")
                    db.session.execute(db.text("""
                        CREATE INDEX ix_shopify_stores_charge_id ON shopify_stores(charge_id)
                    """))
                    logger.info("✅ charge_id index added")
            except Exception as e:
                logger.warning(f"Could not add indexes: {e}")
                # Don't rollback - indexes are optional
            
            db.session.commit()
            logger.info("✅ Migration completed successfully")
            
        except Exception as e:
            logger.error(f"Migration error: {e}", exc_info=True)
            db.session.rollback()
            raise

if __name__ == "__main__":
    migrate_shopify_store_columns()
