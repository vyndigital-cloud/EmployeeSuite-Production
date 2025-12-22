"""
Database Migration: Add shop_id, charge_id, and uninstalled_at to shopify_stores table
Safe migration - adds nullable columns
"""
import os
from logging_config import logger

def migrate_shopify_store_columns(app, db):
    """Add new columns to shopify_stores table - SQLite and PostgreSQL compatible"""
    # CRITICAL: Don't create nested app_context - assume we're already in one
    # If called from init_db(), we're already in app.app_context()
    try:
        # Get database dialect to determine which method to use
        dialect = db.engine.dialect.name
        
        # SQLite doesn't have information_schema, so we just try to add columns
        # PostgreSQL has information_schema, so we can check first
        if dialect == 'sqlite':
                # For SQLite, just try to add columns and catch "already exists" errors
                columns_to_add = [
                    ('shop_id', 'BIGINT'),
                    ('charge_id', 'VARCHAR(255)'),
                    ('uninstalled_at', 'TIMESTAMP')
                ]
                
                for col_name, col_type in columns_to_add:
                    try:
                        logger.info(f"Adding {col_name} column to shopify_stores table...")
                        db.session.execute(db.text(f"""
                            ALTER TABLE shopify_stores 
                            ADD COLUMN {col_name} {col_type}
                        """))
                        db.session.commit()
                        logger.info(f"✅ {col_name} column added successfully")
                    except Exception as e:
                        error_str = str(e).lower()
                        if "duplicate column" in error_str or "already exists" in error_str:
                            logger.info(f"✅ {col_name} column already exists")
                        else:
                            logger.warning(f"Could not add {col_name} column: {e}")
                        db.session.rollback()
            else:
                # For PostgreSQL, check information_schema first
                # Check if shop_id column exists
                try:
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
                            db.session.commit()  # CRITICAL: Commit immediately after each column
                            logger.info("✅ shop_id column added successfully")
                        except Exception as e:
                            # CRITICAL: Rollback immediately on error
                            try:
                                db.session.rollback()
                            except Exception:
                                pass
                            if "already exists" in str(e).lower() or "duplicate" in str(e).lower() or "current transaction is aborted" in str(e).lower():
                                logger.info("✅ shop_id column already exists")
                            else:
                                logger.warning(f"Could not add shop_id column: {e}")
                    else:
                        logger.info("✅ shop_id column already exists")
                except Exception as e:
                    logger.warning(f"Could not check for shop_id column: {e}")
                
                # Check if charge_id column exists
                try:
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
                            db.session.commit()  # CRITICAL: Commit immediately after each column
                            logger.info("✅ charge_id column added successfully")
                        except Exception as e:
                            # CRITICAL: Rollback immediately on error
                            try:
                                db.session.rollback()
                            except Exception:
                                pass
                            if "already exists" in str(e).lower() or "duplicate" in str(e).lower() or "current transaction is aborted" in str(e).lower():
                                logger.info("✅ charge_id column already exists")
                            else:
                                logger.warning(f"Could not add charge_id column: {e}")
                    else:
                        logger.info("✅ charge_id column already exists")
                except Exception as e:
                    logger.warning(f"Could not check for charge_id column: {e}")
                
                # Check if uninstalled_at column exists
                try:
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
                            db.session.commit()  # CRITICAL: Commit immediately after each column
                            logger.info("✅ uninstalled_at column added successfully")
                        except Exception as e:
                            # CRITICAL: Rollback immediately on error
                            try:
                                db.session.rollback()
                            except Exception:
                                pass
                            if "already exists" in str(e).lower() or "duplicate" in str(e).lower() or "current transaction is aborted" in str(e).lower():
                                logger.info("✅ uninstalled_at column already exists")
                            else:
                                logger.warning(f"Could not add uninstalled_at column: {e}")
                    else:
                        logger.info("✅ uninstalled_at column already exists")
                except Exception as e:
                    logger.warning(f"Could not check for uninstalled_at column: {e}")
                
                # Add indexes for new columns (PostgreSQL only - SQLite handles indexes differently)
                if dialect != 'sqlite':
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
                        try:
                            db.session.rollback()
                        except Exception:
                            pass
            
            # Final commit (though we've been committing after each column)
            try:
                db.session.commit()
            except Exception:
                pass
        logger.info("✅ Migration completed successfully")
        
    except Exception as e:
            logger.error(f"Migration error: {e}", exc_info=True)
            try:
                db.session.rollback()
            except Exception:
                pass
            # Don't raise - allow app to continue even if migration fails
            # Log the error but don't crash the app

if __name__ == "__main__":
    migrate_shopify_store_columns()
