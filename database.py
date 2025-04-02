import os
import asyncio
import asyncpg
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('database')

class Database:
    _instance = None
    _pool = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    async def initialize(self):
        """Initialize the database connection pool."""
        if self._initialized:
            return
        
        load_dotenv()
        
        # Get database configuration from environment variables
        self.host = os.getenv('DB_HOST', 'localhost')
        self.port = os.getenv('DB_PORT', '5432')
        self.user = os.getenv('DB_USER', 'postgres')
        self.password = os.getenv('DB_PASSWORD', 'password')
        self.database = os.getenv('DB_NAME', 'discord_bot')
        
        try:
            # Create connection pool
            self._pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                min_size=5,
                max_size=20
            )
            
            logger.info(f"Connected to PostgreSQL database at {self.host}:{self.port}")
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            # Fallback to JSON if database connection fails
            self._initialized = False
            raise
    
    @property
    def pool(self):
        """Get the connection pool."""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._pool
    
    async def execute(self, query, *args, **kwargs):
        """Execute a query and return the status."""
        try:
            async with self.pool.acquire() as conn:
                return await conn.execute(query, *args, **kwargs)
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Args: {args}")
            raise
    
    async def fetch(self, query, *args, **kwargs):
        """Execute a query and return all results."""
        try:
            async with self.pool.acquire() as conn:
                return await conn.fetch(query, *args, **kwargs)
        except Exception as e:
            logger.error(f"Query fetch error: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Args: {args}")
            raise
    
    async def fetchrow(self, query, *args, **kwargs):
        """Execute a query and return the first row."""
        try:
            async with self.pool.acquire() as conn:
                return await conn.fetchrow(query, *args, **kwargs)
        except Exception as e:
            logger.error(f"Query fetchrow error: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Args: {args}")
            raise
    
    async def fetchval(self, query, *args, **kwargs):
        """Execute a query and return a single value."""
        try:
            async with self.pool.acquire() as conn:
                return await conn.fetchval(query, *args, **kwargs)
        except Exception as e:
            logger.error(f"Query fetchval error: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Args: {args}")
            raise
    
    async def close(self):
        """Close the database connection pool."""
        if self._pool:
            await self._pool.close()
            self._initialized = False
            logger.info("Database connection pool closed")

# Global singleton instance
db = Database()