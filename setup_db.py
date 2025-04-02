#!/usr/bin/env python3
import os
import asyncio
import asyncpg
import argparse
from dotenv import load_dotenv
import logging
import json
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('db_setup')

async def setup_database(host, port, user, password, database):
    """Create the database if it doesn't exist and set up schema."""
    # First, connect to PostgreSQL server (without specifying database)
    try:
        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database='postgres'  # Connect to default database first
        )
        
        # Check if our database exists
        db_exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            database
        )
        
        if not db_exists:
            logger.info(f"Creating database '{database}'...")
            # Escape database name to prevent SQL injection
            await conn.execute(f"CREATE DATABASE \"{database}\"")
            logger.info(f"Database '{database}' created successfully.")
        else:
            logger.info(f"Database '{database}' already exists.")
            
        await conn.close()
        
        # Now connect to our database and set up schema
        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        
        # Read schema.sql file
        schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
        if not os.path.exists(schema_path):
            logger.error(f"Schema file not found at {schema_path}")
            return False
            
        with open(schema_path, 'r') as f:
            schema = f.read()
            
        # Execute schema script
        logger.info("Setting up database schema...")
        await conn.execute(schema)
        logger.info("Schema setup completed successfully.")
        
        await conn.close()
        return True
    except Exception as e:
        logger.error(f"Database setup error: {e}")
        return False

async def migrate_data_from_json():
    """Migrate data from JSON files to PostgreSQL."""
    load_dotenv()
    
    host = os.getenv('DB_HOST', 'localhost')
    port = os.getenv('DB_PORT', '5432')
    user = os.getenv('DB_USER', 'postgres')
    password = os.getenv('DB_PASSWORD', '')
    database = os.getenv('DB_NAME', 'discord_bot')
    
    try:
        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        
        # Migrate bank.json
        if os.path.exists('data/bank.json'):
            with open('data/bank.json', 'r') as f:
                content = f.read().strip()
                if content:
                    bank_data = json.loads(content)
                    
                    # Begin transaction
                    async with conn.transaction():
                        for user_id, data in bank_data.items():
                            wallet = data.get('wallet', 0)
                            bank = data.get('bank', 0)
                            last_work = data.get('last_work')
                            
                            # Insert or update user bank account
                            await conn.execute('''
                                INSERT INTO bank_accounts (user_id, wallet, bank, last_work)
                                VALUES ($1, $2, $3, $4)
                                ON CONFLICT (user_id) 
                                DO UPDATE SET wallet = $2, bank = $3, last_work = $4
                            ''', int(user_id), wallet, bank, last_work)
            
            logger.info("Bank data migration completed.")
                
        # Migrate jobs.json
        if os.path.exists('data/jobs.json'):
            with open('data/jobs.json', 'r') as f:
                content = f.read().strip()
                if content:
                    jobs_data = json.loads(content)
                    
                    # Begin transaction
                    async with conn.transaction():
                        # Process user jobs
                        user_jobs = jobs_data.get('user_jobs', {})
                        for user_id, jobs in user_jobs.items():
                            for job_name in jobs:
                                # Insert user job
                                await conn.execute('''
                                    INSERT INTO user_jobs (user_id, job_name)
                                    VALUES ($1, $2)
                                    ON CONFLICT (user_id, job_name) DO NOTHING
                                ''', int(user_id), job_name)
            
            logger.info("Jobs data migration completed.")
                
        # Migrate levels.json
        if os.path.exists('data/levels.json'):
            with open('data/levels.json', 'r') as f:
                content = f.read().strip()
                if content:
                    levels_data = json.loads(content)
                    
                    # Begin transaction
                    async with conn.transaction():
                        for user_id, data in levels_data.items():
                            xp = data.get('xp', 0)
                            level = data.get('level', 0)
                            total_messages = data.get('total_messages', 0)
                            last_message = data.get('last_message')
                            
                            if last_message:
                                # Convert timestamp to datetime
                                from datetime import datetime
                                last_message = datetime.fromtimestamp(last_message)
                            
                            # Insert or update user levels
                            await conn.execute('''
                                INSERT INTO user_levels (user_id, xp, level, total_messages, last_message)
                                VALUES ($1, $2, $3, $4, $5)
                                ON CONFLICT (user_id) 
                                DO UPDATE SET xp = $2, level = $3, total_messages = $4, last_message = $5
                            ''', int(user_id), xp, level, total_messages, last_message)
            
            logger.info("User levels data migration completed.")
                
        # Migrate voice_levels.json
        if os.path.exists('data/voice_levels.json'):
            with open('data/voice_levels.json', 'r') as f:
                content = f.read().strip()
                if content:
                    voice_data = json.loads(content)
                    
                    # Begin transaction
                    async with conn.transaction():
                        for user_id, data in voice_data.items():
                            voice_time = data.get('voice_time', 0)
                            
                            # Insert or update user voice activity
                            await conn.execute('''
                                INSERT INTO voice_activity (user_id, voice_time)
                                VALUES ($1, $2)
                                ON CONFLICT (user_id) 
                                DO UPDATE SET voice_time = $2
                            ''', int(user_id), voice_time)
            
            logger.info("Voice activity data migration completed.")
                
        # Migrate lastfm.json
        if os.path.exists('data/lastfm.json'):
            with open('data/lastfm.json', 'r') as f:
                content = f.read().strip()
                if content:
                    lastfm_data = json.loads(content)
                    
                    # Begin transaction
                    async with conn.transaction():
                        for user_id, username in lastfm_data.items():
                            # Insert or update lastfm username
                            await conn.execute('''
                                INSERT INTO lastfm_users (user_id, lastfm_username)
                                VALUES ($1, $2)
                                ON CONFLICT (user_id) 
                                DO UPDATE SET lastfm_username = $2
                            ''', int(user_id), username)
            
            logger.info("LastFM data migration completed.")
        
        await conn.close()
        return True
    except Exception as e:
        logger.error(f"Data migration error: {e}")
        return False

def create_env_file():
    """Create a .env file with database configuration."""
    env_path = '.env'
    
    # Check if .env already exists and prompt for override
    if os.path.exists(env_path):
        override = input(".env file already exists. Override? (y/N): ")
        if override.lower() != 'y':
            logger.info("Skipping .env file creation.")
            return
    
    # Prompt for database configuration
    host = input("Database host (default: localhost): ") or 'localhost'
    port = input("Database port (default: 5432): ") or '5432'
    user = input("Database user (default: postgres): ") or 'postgres'
    password = input("Database password: ")
    database = input("Database name (default: discord_bot): ") or 'discord_bot'
    
    # Create .env file
    with open(env_path, 'w') as f:
        f.write(f"DB_HOST={host}\n")
        f.write(f"DB_PORT={port}\n")
        f.write(f"DB_USER={user}\n")
        f.write(f"DB_PASSWORD={password}\n")
        f.write(f"DB_NAME={database}\n")
        
        # Keep existing bot token if present
        if os.path.exists('.env.old'):
            with open('.env.old', 'r') as old:
                for line in old:
                    if line.startswith('bot_token='):
                        f.write(line)
        else:
            # Prompt for bot token if not available
            token = input("Discord bot token (leave empty to skip): ")
            if token:
                f.write(f"bot_token={token}\n")
                
            # Prompt for LastFM key if not available
            lastfm_key = input("Last.fm API key (leave empty to skip): ")
            if lastfm_key:
                f.write(f"lastfm_key={lastfm_key}\n")
    
    logger.info(f".env file created at {env_path}")

async def main():
    parser = argparse.ArgumentParser(description='Discord Bot Database Setup')
    parser.add_argument('--setup', action='store_true', help='Set up database schema')
    parser.add_argument('--migrate', action='store_true', help='Migrate data from JSON files')
    parser.add_argument('--config', action='store_true', help='Create or update .env configuration')
    
    args = parser.parse_args()
    
    # Default to setup if no arguments provided
    if not (args.setup or args.migrate or args.config):
        args.setup = True
        args.config = True
        args.migrate = True
    
    if args.config:
        create_env_file()
    
    # Load environment variables
    load_dotenv()
    
    host = os.getenv('DB_HOST', 'localhost')
    port = os.getenv('DB_PORT', '5432')
    user = os.getenv('DB_USER', 'postgres')
    password = os.getenv('DB_PASSWORD', '')
    database = os.getenv('DB_NAME', 'discord_bot')
    
    if args.setup:
        logger.info("Setting up database...")
        success = await setup_database(host, port, user, password, database)
        if success:
            logger.info("Database setup completed successfully.")
        else:
            logger.error("Database setup failed.")
            sys.exit(1)
    
    if args.migrate:
        logger.info("Migrating data from JSON files...")
        success = await migrate_data_from_json()
        if success:
            logger.info("Data migration completed successfully.")
        else:
            logger.error("Data migration failed.")
            sys.exit(1)
    
    logger.info("All operations completed.")

if __name__ == "__main__":
    asyncio.run(main())