"""
Automated Database Backup System
Backs up PostgreSQL database and uploads to S3 with retention policy
"""
import os
import sys
import subprocess
import boto3
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import gzip
from logging_config import logger

class DatabaseBackup:
    def __init__(self):
        self.db_url = os.getenv('DATABASE_URL')
        self.s3_bucket = os.getenv('S3_BACKUP_BUCKET')
        self.s3_region = os.getenv('S3_BACKUP_REGION', 'us-east-1')
        self.aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.retention_days = int(os.getenv('BACKUP_RETENTION_DAYS', '30'))
        
        # Validate required environment variables
        if not self.db_url:
            raise ValueError("DATABASE_URL environment variable is required")
        if not self.s3_bucket:
            raise ValueError("S3_BACKUP_BUCKET environment variable is required")
        if not self.aws_access_key or not self.aws_secret_key:
            raise ValueError("AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are required")
    
    def _parse_db_url(self):
        """Parse DATABASE_URL to extract connection details"""
        # Format: postgresql://user:password@host:port/database
        # or: postgres://user:password@host:port/database
        url = self.db_url.replace('postgres://', 'postgresql://')
        if not url.startswith('postgresql://'):
            raise ValueError("Invalid DATABASE_URL format")
        
        # Remove protocol
        url = url.replace('postgresql://', '')
        
        # Split user:pass@host:port/db
        if '@' in url:
            auth, rest = url.split('@', 1)
            if ':' in auth:
                user, password = auth.split(':', 1)
            else:
                user = auth
                password = ''
            
            if '/' in rest:
                host_port, database = rest.split('/', 1)
                if ':' in host_port:
                    host, port = host_port.split(':')
                else:
                    host = host_port
                    port = '5432'
            else:
                raise ValueError("Database name not found in DATABASE_URL")
        else:
            raise ValueError("Invalid DATABASE_URL format")
        
        return {
            'user': user,
            'password': password,
            'host': host,
            'port': port,
            'database': database
        }
    
    def _create_backup_file(self):
        """Create a PostgreSQL backup using pg_dump"""
        db_info = self._parse_db_url()
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"employeesuite_backup_{timestamp}.sql"
        
        # Create temporary directory for backup
        temp_dir = tempfile.mkdtemp()
        backup_path = os.path.join(temp_dir, backup_filename)
        
        # Set PGPASSWORD environment variable for pg_dump
        env = os.environ.copy()
        env['PGPASSWORD'] = db_info['password']
        
        # Build pg_dump command (plain format for better compatibility)
        pg_dump_cmd = [
            'pg_dump',
            '-h', db_info['host'],
            '-p', db_info['port'],
            '-U', db_info['user'],
            '-d', db_info['database'],
            '-F', 'p',  # Plain SQL format
            '--no-owner',  # Don't dump ownership
            '--no-acl',    # Don't dump access privileges
        ]
        
        try:
            logger.info(f"Creating database backup: {backup_filename}")
            # Write output directly to file
            with open(backup_path, 'w') as f:
                result = subprocess.run(
                    pg_dump_cmd,
                    env=env,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True
                )
            
            # Check for errors in stderr
            if result.stderr:
                logger.warning(f"pg_dump warnings: {result.stderr}")
            
            # Compress the backup
            compressed_path = f"{backup_path}.gz"
            with open(backup_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    f_out.writelines(f_in)
            
            # Remove uncompressed file
            os.remove(backup_path)
            
            logger.info(f"Backup created successfully: {compressed_path}")
            return compressed_path, backup_filename + '.gz'
            
        except subprocess.CalledProcessError as e:
            logger.error(f"pg_dump failed: {e.stderr}")
            raise
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            raise
    
    def _upload_to_s3(self, local_path, s3_key):
        """Upload backup file to S3"""
        try:
            s3_client = boto3.client(
                's3',
                region_name=self.s3_region,
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key
            )
            
            logger.info(f"Uploading backup to S3: s3://{self.s3_bucket}/{s3_key}")
            
            # Upload with metadata
            s3_client.upload_file(
                local_path,
                self.s3_bucket,
                s3_key,
                ExtraArgs={
                    'Metadata': {
                        'backup_date': datetime.utcnow().isoformat(),
                        'service': 'employeesuite'
                    },
                    'ServerSideEncryption': 'AES256'
                }
            )
            
            logger.info(f"Backup uploaded successfully to S3")
            return True
            
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            raise
    
    def _cleanup_old_backups(self):
        """Delete backups older than retention period"""
        try:
            s3_client = boto3.client(
                's3',
                region_name=self.s3_region,
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key
            )
            
            cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
            
            # List all backups
            response = s3_client.list_objects_v2(
                Bucket=self.s3_bucket,
                Prefix='employeesuite_backup_'
            )
            
            if 'Contents' not in response:
                logger.info("No old backups to clean up")
                return
            
            deleted_count = 0
            for obj in response['Contents']:
                # Extract date from filename: employeesuite_backup_YYYYMMDD_HHMMSS.sql.gz
                try:
                    filename = obj['Key']
                    date_str = filename.split('_')[2] + '_' + filename.split('_')[3].replace('.sql.gz', '')
                    backup_date = datetime.strptime(date_str, '%Y%m%d_%H%M%S')
                    
                    if backup_date < cutoff_date:
                        s3_client.delete_object(Bucket=self.s3_bucket, Key=obj['Key'])
                        deleted_count += 1
                        logger.info(f"Deleted old backup: {obj['Key']}")
                except (IndexError, ValueError) as e:
                    logger.warning(f"Could not parse date from backup filename: {obj['Key']}")
                    continue
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old backup(s)")
            else:
                logger.info("No backups older than retention period")
                
        except Exception as e:
            logger.warning(f"Failed to clean up old backups: {e}")
            # Don't raise - cleanup failure shouldn't fail the backup
    
    def create_backup(self):
        """Main backup function - creates backup and uploads to S3"""
        backup_path = None
        try:
            # Create backup
            backup_path, backup_filename = self._create_backup_file()
            
            # Upload to S3
            s3_key = f"backups/{backup_filename}"
            self._upload_to_s3(backup_path, s3_key)
            
            # Clean up old backups
            self._cleanup_old_backups()
            
            # Clean up local file
            if backup_path and os.path.exists(backup_path):
                os.remove(backup_path)
                os.rmdir(os.path.dirname(backup_path))
            
            return {
                'success': True,
                'backup_file': backup_filename,
                's3_key': s3_key,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Backup failed: {e}", exc_info=True)
            
            # Clean up local file on error
            if backup_path and os.path.exists(backup_path):
                try:
                    os.remove(backup_path)
                    os.rmdir(os.path.dirname(backup_path))
                except:
                    pass
            
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }


def run_backup():
    """Standalone function to run backup (for cron jobs)"""
    try:
        backup = DatabaseBackup()
        result = backup.create_backup()
        return result
    except Exception as e:
        logger.error(f"Backup execution failed: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


if __name__ == "__main__":
    result = run_backup()
    if result['success']:
        print(f"✅ Backup successful: {result['backup_file']}")
        sys.exit(0)
    else:
        print(f"❌ Backup failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)
