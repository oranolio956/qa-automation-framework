#!/usr/bin/env python3
"""
Database Integration System
Provides database connectivity and import/export functionality for account data
"""

import sqlite3
import json
import logging
import hashlib
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import asyncio
import aiosqlite
from contextlib import asynccontextmanager

try:
    import psycopg2
    import psycopg2.extras
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

try:
    import pymongo
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False

from .account_export_system import ExportableAccount, SecurityLevel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """Database configuration"""
    db_type: str  # sqlite, postgresql, mongodb
    host: Optional[str] = None
    port: Optional[int] = None
    database: str = "accounts.db"
    username: Optional[str] = None
    password: Optional[str] = None
    table_name: str = "accounts"
    ssl_mode: str = "prefer"
    pool_size: int = 10
    timeout: int = 30

class SQLiteIntegration:
    """SQLite database integration"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.db_path = Path(config.database)
        self.logger = logging.getLogger(f"{__name__}.SQLite")
        
    async def initialize_database(self):
        """Initialize SQLite database with account schema"""
        schema_sql = """
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            display_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone_number TEXT,
            birth_date TEXT,
            password TEXT NOT NULL,
            first_name TEXT,
            last_name TEXT,
            bio TEXT,
            profile_pic_path TEXT,
            status TEXT DEFAULT 'ACTIVE',
            verification_status TEXT DEFAULT 'UNVERIFIED',
            account_type TEXT DEFAULT 'STANDARD',
            registration_time TEXT NOT NULL,
            login_verified BOOLEAN DEFAULT FALSE,
            snapchat_user_id TEXT,
            tinder_user_id TEXT,
            verification_code TEXT,
            device_fingerprint TEXT,
            creation_metadata TEXT,
            trust_score INTEGER DEFAULT 0,
            export_timestamp TEXT NOT NULL,
            export_id TEXT UNIQUE NOT NULL,
            security_hash TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_username ON accounts(username);
        CREATE INDEX IF NOT EXISTS idx_email ON accounts(email);
        CREATE INDEX IF NOT EXISTS idx_status ON accounts(status);
        CREATE INDEX IF NOT EXISTS idx_verification_status ON accounts(verification_status);
        CREATE INDEX IF NOT EXISTS idx_trust_score ON accounts(trust_score);
        CREATE INDEX IF NOT EXISTS idx_export_id ON accounts(export_id);
        CREATE INDEX IF NOT EXISTS idx_created_at ON accounts(created_at);
        """
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(schema_sql)
            await db.commit()
            self.logger.info(f"SQLite database initialized at {self.db_path}")
    
    async def insert_account(self, account: ExportableAccount) -> bool:
        """Insert single account into database"""
        try:
            insert_sql = """
            INSERT OR REPLACE INTO accounts (
                username, display_name, email, phone_number, birth_date, password,
                first_name, last_name, bio, profile_pic_path, status,
                verification_status, account_type, registration_time, login_verified,
                snapchat_user_id, tinder_user_id, verification_code,
                device_fingerprint, creation_metadata, trust_score,
                export_timestamp, export_id, security_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            values = (
                account.username, account.display_name, account.email,
                account.phone_number, account.birth_date, account.password,
                account.first_name, account.last_name, account.bio,
                account.profile_pic_path, account.status, account.verification_status,
                account.account_type, account.registration_time, account.login_verified,
                account.snapchat_user_id, account.tinder_user_id, account.verification_code,
                json.dumps(account.device_fingerprint) if account.device_fingerprint else None,
                json.dumps(account.creation_metadata) if account.creation_metadata else None,
                account.trust_score, account.export_timestamp, account.export_id,
                account.security_hash
            )
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(insert_sql, values)
                await db.commit()
                
            self.logger.info(f"Account {account.username} inserted into SQLite database")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to insert account {account.username}: {e}")
            return False
    
    async def insert_accounts_batch(self, accounts: List[ExportableAccount]) -> Dict[str, Any]:
        """Insert batch of accounts into database"""
        results = {"total": len(accounts), "successful": 0, "failed": 0, "errors": []}
        
        insert_sql = """
        INSERT OR REPLACE INTO accounts (
            username, display_name, email, phone_number, birth_date, password,
            first_name, last_name, bio, profile_pic_path, status,
            verification_status, account_type, registration_time, login_verified,
            snapchat_user_id, tinder_user_id, verification_code,
            device_fingerprint, creation_metadata, trust_score,
            export_timestamp, export_id, security_hash
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        async with aiosqlite.connect(self.db_path) as db:
            for account in accounts:
                try:
                    values = (
                        account.username, account.display_name, account.email,
                        account.phone_number, account.birth_date, account.password,
                        account.first_name, account.last_name, account.bio,
                        account.profile_pic_path, account.status, account.verification_status,
                        account.account_type, account.registration_time, account.login_verified,
                        account.snapchat_user_id, account.tinder_user_id, account.verification_code,
                        json.dumps(account.device_fingerprint) if account.device_fingerprint else None,
                        json.dumps(account.creation_metadata) if account.creation_metadata else None,
                        account.trust_score, account.export_timestamp, account.export_id,
                        account.security_hash
                    )
                    
                    await db.execute(insert_sql, values)
                    results["successful"] += 1
                    
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(f"{account.username}: {str(e)}")
                    self.logger.error(f"Failed to insert account {account.username}: {e}")
            
            await db.commit()
        
        self.logger.info(f"Batch insert completed: {results['successful']}/{results['total']} successful")
        return results
    
    async def get_accounts(self, limit: int = 100, offset: int = 0, 
                          filters: Optional[Dict] = None) -> List[ExportableAccount]:
        """Retrieve accounts from database"""
        base_sql = "SELECT * FROM accounts"
        params = []
        
        if filters:
            conditions = []
            for key, value in filters.items():
                if key in ['status', 'verification_status', 'username']:
                    conditions.append(f"{key} = ?")
                    params.append(value)
                elif key == 'trust_score_min':
                    conditions.append("trust_score >= ?")
                    params.append(value)
                elif key == 'created_after':
                    conditions.append("created_at >= ?")
                    params.append(value)
            
            if conditions:
                base_sql += " WHERE " + " AND ".join(conditions)
        
        base_sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        accounts = []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(base_sql, params) as cursor:
                async for row in cursor:
                    account = self._row_to_account(row)
                    accounts.append(account)
        
        self.logger.info(f"Retrieved {len(accounts)} accounts from database")
        return accounts
    
    async def get_account_by_username(self, username: str) -> Optional[ExportableAccount]:
        """Get specific account by username"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM accounts WHERE username = ?", (username,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._row_to_account(row)
        return None
    
    async def update_account_status(self, username: str, status: str, 
                                  verification_status: str = None) -> bool:
        """Update account status"""
        try:
            update_sql = "UPDATE accounts SET status = ?, updated_at = CURRENT_TIMESTAMP"
            params = [status]
            
            if verification_status:
                update_sql += ", verification_status = ?"
                params.append(verification_status)
            
            update_sql += " WHERE username = ?"
            params.append(username)
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(update_sql, params)
                await db.commit()
            
            self.logger.info(f"Updated account {username} status to {status}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update account {username}: {e}")
            return False
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        stats_sql = """
        SELECT 
            COUNT(*) as total_accounts,
            COUNT(CASE WHEN status = 'ACTIVE' THEN 1 END) as active_accounts,
            COUNT(CASE WHEN verification_status = 'VERIFIED' THEN 1 END) as verified_accounts,
            AVG(trust_score) as avg_trust_score,
            MAX(trust_score) as max_trust_score,
            COUNT(CASE WHEN snapchat_user_id IS NOT NULL THEN 1 END) as snapchat_linked,
            COUNT(CASE WHEN tinder_user_id IS NOT NULL THEN 1 END) as tinder_linked,
            DATE(MIN(created_at)) as first_account,
            DATE(MAX(created_at)) as latest_account
        FROM accounts
        """
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(stats_sql) as cursor:
                row = await cursor.fetchone()
                return dict(row)
    
    def _row_to_account(self, row) -> ExportableAccount:
        """Convert database row to ExportableAccount"""
        return ExportableAccount(
            username=row['username'],
            display_name=row['display_name'],
            email=row['email'],
            phone_number=row['phone_number'],
            birth_date=row['birth_date'],
            password=row['password'],
            first_name=row['first_name'],
            last_name=row['last_name'],
            bio=row['bio'],
            profile_pic_path=row['profile_pic_path'],
            status=row['status'],
            verification_status=row['verification_status'],
            account_type=row['account_type'],
            registration_time=row['registration_time'],
            login_verified=bool(row['login_verified']),
            snapchat_user_id=row['snapchat_user_id'],
            tinder_user_id=row['tinder_user_id'],
            verification_code=row['verification_code'],
            device_fingerprint=json.loads(row['device_fingerprint']) if row['device_fingerprint'] else None,
            creation_metadata=json.loads(row['creation_metadata']) if row['creation_metadata'] else None,
            trust_score=row['trust_score'],
            export_timestamp=row['export_timestamp'],
            export_id=row['export_id'],
            security_hash=row['security_hash']
        )

class PostgreSQLIntegration:
    """PostgreSQL database integration"""
    
    def __init__(self, config: DatabaseConfig):
        if not POSTGRES_AVAILABLE:
            raise ImportError("psycopg2 not available. Install with: pip install psycopg2-binary")
        
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.PostgreSQL")
        self.connection_string = (
            f"host={config.host} port={config.port} "
            f"dbname={config.database} user={config.username} "
            f"password={config.password} sslmode={config.ssl_mode}"
        )
    
    async def initialize_database(self):
        """Initialize PostgreSQL database with account schema"""
        schema_sql = """
        CREATE TABLE IF NOT EXISTS accounts (
            id SERIAL PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            display_name VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL,
            phone_number VARCHAR(20),
            birth_date VARCHAR(20),
            password VARCHAR(255) NOT NULL,
            first_name VARCHAR(255),
            last_name VARCHAR(255),
            bio TEXT,
            profile_pic_path VARCHAR(500),
            status VARCHAR(50) DEFAULT 'ACTIVE',
            verification_status VARCHAR(50) DEFAULT 'UNVERIFIED',
            account_type VARCHAR(50) DEFAULT 'STANDARD',
            registration_time TIMESTAMP NOT NULL,
            login_verified BOOLEAN DEFAULT FALSE,
            snapchat_user_id VARCHAR(255),
            tinder_user_id VARCHAR(255),
            verification_code VARCHAR(10),
            device_fingerprint JSONB,
            creation_metadata JSONB,
            trust_score INTEGER DEFAULT 0,
            export_timestamp TIMESTAMP NOT NULL,
            export_id VARCHAR(255) UNIQUE NOT NULL,
            security_hash VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_accounts_username ON accounts(username);
        CREATE INDEX IF NOT EXISTS idx_accounts_email ON accounts(email);
        CREATE INDEX IF NOT EXISTS idx_accounts_status ON accounts(status);
        CREATE INDEX IF NOT EXISTS idx_accounts_verification_status ON accounts(verification_status);
        CREATE INDEX IF NOT EXISTS idx_accounts_trust_score ON accounts(trust_score);
        CREATE INDEX IF NOT EXISTS idx_accounts_export_id ON accounts(export_id);
        CREATE INDEX IF NOT EXISTS idx_accounts_created_at ON accounts(created_at);
        CREATE INDEX IF NOT EXISTS idx_accounts_device_fingerprint ON accounts USING GIN(device_fingerprint);
        """
        
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    cur.execute(schema_sql)
                    conn.commit()
            self.logger.info("PostgreSQL database schema initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize PostgreSQL schema: {e}")
            raise
    
    async def insert_accounts_batch(self, accounts: List[ExportableAccount]) -> Dict[str, Any]:
        """Insert batch of accounts using PostgreSQL COPY for efficiency"""
        results = {"total": len(accounts), "successful": 0, "failed": 0, "errors": []}
        
        insert_sql = """
        INSERT INTO accounts (
            username, display_name, email, phone_number, birth_date, password,
            first_name, last_name, bio, profile_pic_path, status,
            verification_status, account_type, registration_time, login_verified,
            snapchat_user_id, tinder_user_id, verification_code,
            device_fingerprint, creation_metadata, trust_score,
            export_timestamp, export_id, security_hash
        ) VALUES %s
        ON CONFLICT (username) DO UPDATE SET
            display_name = EXCLUDED.display_name,
            status = EXCLUDED.status,
            verification_status = EXCLUDED.verification_status,
            trust_score = EXCLUDED.trust_score,
            updated_at = CURRENT_TIMESTAMP
        """
        
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    values = []
                    for account in accounts:
                        account_tuple = (
                            account.username, account.display_name, account.email,
                            account.phone_number, account.birth_date, account.password,
                            account.first_name, account.last_name, account.bio,
                            account.profile_pic_path, account.status, account.verification_status,
                            account.account_type, account.registration_time, account.login_verified,
                            account.snapchat_user_id, account.tinder_user_id, account.verification_code,
                            json.dumps(account.device_fingerprint) if account.device_fingerprint else None,
                            json.dumps(account.creation_metadata) if account.creation_metadata else None,
                            account.trust_score, account.export_timestamp, account.export_id,
                            account.security_hash
                        )
                        values.append(account_tuple)
                    
                    psycopg2.extras.execute_values(
                        cur, insert_sql, values, template=None, page_size=100
                    )
                    conn.commit()
                    results["successful"] = len(accounts)
                    
        except Exception as e:
            results["failed"] = len(accounts)
            results["errors"].append(str(e))
            self.logger.error(f"PostgreSQL batch insert failed: {e}")
        
        self.logger.info(f"PostgreSQL batch insert: {results['successful']}/{results['total']} successful")
        return results

class MongoDBIntegration:
    """MongoDB database integration"""
    
    def __init__(self, config: DatabaseConfig):
        if not MONGODB_AVAILABLE:
            raise ImportError("pymongo not available. Install with: pip install pymongo")
        
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.MongoDB")
        self.client = None
        self.db = None
        self.collection = None
    
    async def initialize_database(self):
        """Initialize MongoDB connection and collection"""
        try:
            connection_string = f"mongodb://{self.config.username}:{self.config.password}@{self.config.host}:{self.config.port}/{self.config.database}"
            self.client = pymongo.MongoClient(connection_string)
            self.db = self.client[self.config.database]
            self.collection = self.db[self.config.table_name]
            
            # Create indexes
            self.collection.create_index([("username", 1)], unique=True)
            self.collection.create_index([("email", 1)])
            self.collection.create_index([("status", 1)])
            self.collection.create_index([("verification_status", 1)])
            self.collection.create_index([("trust_score", 1)])
            self.collection.create_index([("export_id", 1)], unique=True)
            self.collection.create_index([("created_at", 1)])
            
            self.logger.info("MongoDB database initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MongoDB: {e}")
            raise
    
    async def insert_accounts_batch(self, accounts: List[ExportableAccount]) -> Dict[str, Any]:
        """Insert batch of accounts into MongoDB"""
        results = {"total": len(accounts), "successful": 0, "failed": 0, "errors": []}
        
        try:
            documents = []
            for account in accounts:
                doc = asdict(account)
                doc['created_at'] = datetime.now()
                doc['updated_at'] = datetime.now()
                documents.append(doc)
            
            # Use bulk upsert operations
            bulk_ops = []
            for doc in documents:
                bulk_ops.append(
                    pymongo.UpdateOne(
                        {"username": doc["username"]},
                        {"$set": doc, "$setOnInsert": {"created_at": doc["created_at"]}},
                        upsert=True
                    )
                )
            
            result = self.collection.bulk_write(bulk_ops, ordered=False)
            results["successful"] = result.upserted_count + result.modified_count
            
            self.logger.info(f"MongoDB batch insert: {results['successful']}/{results['total']} successful")
            
        except Exception as e:
            results["failed"] = len(accounts)
            results["errors"].append(str(e))
            self.logger.error(f"MongoDB batch insert failed: {e}")
        
        return results
    
    async def get_accounts(self, limit: int = 100, offset: int = 0, 
                          filters: Optional[Dict] = None) -> List[ExportableAccount]:
        """Retrieve accounts from MongoDB"""
        query = {}
        if filters:
            for key, value in filters.items():
                if key == 'trust_score_min':
                    query['trust_score'] = {"$gte": value}
                elif key == 'created_after':
                    query['created_at'] = {"$gte": value}
                else:
                    query[key] = value
        
        accounts = []
        cursor = self.collection.find(query).skip(offset).limit(limit).sort("created_at", -1)
        
        for doc in cursor:
            # Remove MongoDB _id field
            doc.pop('_id', None)
            doc.pop('created_at', None)
            doc.pop('updated_at', None)
            
            try:
                account = ExportableAccount(**doc)
                accounts.append(account)
            except Exception as e:
                self.logger.warning(f"Failed to convert document to account: {e}")
        
        self.logger.info(f"Retrieved {len(accounts)} accounts from MongoDB")
        return accounts

class DatabaseManager:
    """Manager for multiple database integrations"""
    
    def __init__(self):
        self.integrations: Dict[str, Union[SQLiteIntegration, PostgreSQLIntegration, MongoDBIntegration]] = {}
        self.logger = logging.getLogger(__name__)
    
    def add_sqlite_integration(self, name: str, database_path: str):
        """Add SQLite integration"""
        config = DatabaseConfig(db_type="sqlite", database=database_path)
        integration = SQLiteIntegration(config)
        self.integrations[name] = integration
        self.logger.info(f"SQLite integration '{name}' added")
    
    def add_postgresql_integration(self, name: str, host: str, port: int, 
                                  database: str, username: str, password: str):
        """Add PostgreSQL integration"""
        config = DatabaseConfig(
            db_type="postgresql", host=host, port=port,
            database=database, username=username, password=password
        )
        integration = PostgreSQLIntegration(config)
        self.integrations[name] = integration
        self.logger.info(f"PostgreSQL integration '{name}' added")
    
    def add_mongodb_integration(self, name: str, host: str, port: int,
                               database: str, username: str, password: str):
        """Add MongoDB integration"""
        config = DatabaseConfig(
            db_type="mongodb", host=host, port=port,
            database=database, username=username, password=password
        )
        integration = MongoDBIntegration(config)
        self.integrations[name] = integration
        self.logger.info(f"MongoDB integration '{name}' added")
    
    async def initialize_all(self):
        """Initialize all database integrations"""
        for name, integration in self.integrations.items():
            try:
                await integration.initialize_database()
                self.logger.info(f"Integration '{name}' initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize integration '{name}': {e}")
    
    async def store_accounts_all(self, accounts: List[ExportableAccount]) -> Dict[str, Dict]:
        """Store accounts in all configured databases"""
        results = {}
        
        for name, integration in self.integrations.items():
            try:
                result = await integration.insert_accounts_batch(accounts)
                results[name] = result
                self.logger.info(f"Stored accounts in '{name}': {result['successful']}/{result['total']}")
            except Exception as e:
                results[name] = {
                    "total": len(accounts),
                    "successful": 0,
                    "failed": len(accounts),
                    "errors": [str(e)]
                }
                self.logger.error(f"Failed to store accounts in '{name}': {e}")
        
        return results
    
    async def get_accounts_from(self, integration_name: str, **kwargs) -> List[ExportableAccount]:
        """Get accounts from specific integration"""
        if integration_name not in self.integrations:
            raise ValueError(f"Integration '{integration_name}' not found")
        
        integration = self.integrations[integration_name]
        return await integration.get_accounts(**kwargs)

# Convenience functions
def create_sqlite_database(database_path: str = "accounts.db") -> SQLiteIntegration:
    """Create SQLite database integration"""
    config = DatabaseConfig(db_type="sqlite", database=database_path)
    return SQLiteIntegration(config)

def create_postgresql_database(host: str, port: int, database: str, 
                              username: str, password: str) -> PostgreSQLIntegration:
    """Create PostgreSQL database integration"""
    config = DatabaseConfig(
        db_type="postgresql", host=host, port=port,
        database=database, username=username, password=password
    )
    return PostgreSQLIntegration(config)

# Example usage
if __name__ == "__main__":
    async def test_database_integration():
        # Create test accounts
        test_accounts = [
            ExportableAccount(
                username="test_db_user_1",
                display_name="Test DB User 1",
                email="testdb1@example.com",
                phone_number="+1234567890",
                birth_date="1995-01-01",
                password="TestDBPass123!",
                first_name="TestDB",
                last_name="User1",
                status="ACTIVE",
                verification_status="VERIFIED",
                trust_score=88
            ),
            ExportableAccount(
                username="test_db_user_2",
                display_name="Test DB User 2",
                email="testdb2@example.com",
                phone_number="+1234567891",
                birth_date="1996-02-02",
                password="TestDBPass456!",
                first_name="TestDB",
                last_name="User2",
                status="ACTIVE",
                verification_status="PENDING",
                trust_score=92
            )
        ]
        
        # Test SQLite integration
        print("Testing SQLite integration...")
        sqlite_db = create_sqlite_database("test_accounts.db")
        await sqlite_db.initialize_database()
        
        # Test batch insert
        result = await sqlite_db.insert_accounts_batch(test_accounts)
        print(f"SQLite batch insert result: {result}")
        
        # Test retrieval
        accounts = await sqlite_db.get_accounts(limit=10)
        print(f"Retrieved {len(accounts)} accounts from SQLite")
        
        # Test statistics
        stats = await sqlite_db.get_statistics()
        print(f"Database statistics: {stats}")
        
        print("Database integration testing completed successfully!")
    
    # Run test
    # asyncio.run(test_database_integration())
    print("Database integration system loaded successfully!")