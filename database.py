"""
SQLite database layer for THGBot with tribute-centric data model.
Handles all database operations with thread safety and transaction support.
"""

import sqlite3
import os
import threading
from contextlib import contextmanager
from typing import Optional, Dict, List, Tuple, Any
import logging

logger = logging.getLogger(__name__)

try:
    datadir = os.environ["SNAP_DATA"]
except KeyError:
    logger.warning("SNAP_DATA not set, using current directory")
    datadir = "."

DATABASE_PATH = os.path.join(datadir, "thgbot.db")


class SQLDatabase:
    """Thread-safe SQLite database layer for THGBot."""
    
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._local = threading.local()
        self.init_schema()
    
    def get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(self.db_path)
            self._local.connection.row_factory = sqlite3.Row
            self._local.connection.execute("PRAGMA foreign_keys = ON")
        return self._local.connection
    
    def close_connection(self):
        """Close thread-local connection."""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            delattr(self._local, 'connection')
    
    @contextmanager
    def transaction(self):
        """Context manager for database transactions."""
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction failed: {e}")
            raise
    
    def init_schema(self):
        """Initialize database schema if it doesn't exist."""
        with self._lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Check if tables already exist
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='tributes'"
            )
            tables_exist = cursor.fetchone()
            
            if not tables_exist:
                logger.info(f"Initializing database schema at {self.db_path}")
                
                # Create tributes table
                cursor.execute("""
                    CREATE TABLE tributes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tribute_id TEXT NOT NULL UNIQUE,
                        tribute_name TEXT NOT NULL,
                        user_id INTEGER NOT NULL,
                        user_mention TEXT NOT NULL,
                        guild_id INTEGER,
                        created_at INTEGER,
                        face_claim_url TEXT,
                        prompt_channel_id INTEGER
                    )
                """)
                
                # Create inventories table
                cursor.execute("""
                    CREATE TABLE inventories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tribute_id TEXT NOT NULL UNIQUE,
                        capacity INTEGER DEFAULT 10,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (tribute_id) REFERENCES tributes(tribute_id) ON DELETE CASCADE
                    )
                """)
                
                # Create inventory_items table
                cursor.execute("""
                    CREATE TABLE inventory_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tribute_id TEXT NOT NULL,
                        item_number INTEGER NOT NULL,
                        item_name TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (tribute_id) REFERENCES tributes(tribute_id) ON DELETE CASCADE,
                        UNIQUE(tribute_id, item_number)
                    )
                """)
                
                # Create prompts table (1:1 with tributes - one prompt per tribute)
                cursor.execute("""
                    CREATE TABLE prompts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tribute_id TEXT NOT NULL UNIQUE,
                        message TEXT NOT NULL,
                        channel_id INTEGER,
                        created_at INTEGER,
                        FOREIGN KEY (tribute_id) REFERENCES tributes(tribute_id) ON DELETE CASCADE
                    )
                """)
                
                # Create prompt_images table
                cursor.execute("""
                    CREATE TABLE prompt_images (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        prompt_id TEXT NOT NULL,
                        file_path TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create files table
                cursor.execute("""
                    CREATE TABLE files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tribute_id TEXT NOT NULL,
                        file_type TEXT,
                        file_path TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (tribute_id) REFERENCES tributes(tribute_id) ON DELETE CASCADE
                    )
                """)
                
                # Create indexes
                cursor.execute("CREATE INDEX idx_tributes_tribute_id ON tributes(tribute_id)")
                cursor.execute("CREATE INDEX idx_tributes_user_id ON tributes(user_id)")
                cursor.execute("CREATE INDEX idx_inventories_tribute_id ON inventories(tribute_id)")
                cursor.execute("CREATE INDEX idx_inventory_items_tribute_id ON inventory_items(tribute_id)")
                cursor.execute("CREATE INDEX idx_prompts_tribute_id ON prompts(tribute_id)")
                cursor.execute("CREATE INDEX idx_files_tribute_id ON files(tribute_id)")
                
                conn.commit()
                logger.info("Database schema initialized successfully")
            else:
                logger.info("Database schema already exists, checking for migrations...")
            
            # Run migrations for existing databases (no lock needed - already holding it)
            self._run_migrations_unlocked(conn, cursor)
    
    def _run_migrations_unlocked(self, conn, cursor):
        """Run schema migrations for existing databases (assumes lock is already held)."""
        # Check if face_claim_url column exists in tributes table
        cursor.execute("PRAGMA table_info(tributes)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "face_claim_url" not in columns:
            logger.info("Adding face_claim_url column to tributes table")
            try:
                cursor.execute("ALTER TABLE tributes ADD COLUMN face_claim_url TEXT")
                conn.commit()
                logger.info("✓ Successfully added face_claim_url column")
            except sqlite3.OperationalError as e:
                logger.error(f"Failed to add face_claim_url column: {e}")
        
        # Check if prompt_channel_id column exists in tributes table
        if "prompt_channel_id" not in columns:
            logger.info("Adding prompt_channel_id column to tributes table")
            try:
                cursor.execute("ALTER TABLE tributes ADD COLUMN prompt_channel_id INTEGER")
                conn.commit()
                logger.info("✓ Successfully added prompt_channel_id column")
            except sqlite3.OperationalError as e:
                logger.error(f"Failed to add prompt_channel_id column: {e}")
        
        # Check if prompts table has prompt_id (old schema) - need to migrate to 1:1 relationship
        cursor.execute("PRAGMA table_info(prompts)")
        prompt_columns = [row[1] for row in cursor.fetchall()]
        
        if "prompt_id" in prompt_columns:
            logger.info("Migrating prompts table from many:1 to 1:1 relationship (removing prompt_id)")
            try:
                # Rename old table
                cursor.execute("ALTER TABLE prompts RENAME TO prompts_old")
                
                # Create new prompts table without prompt_id (1:1 relationship)
                cursor.execute("""
                    CREATE TABLE prompts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tribute_id TEXT NOT NULL UNIQUE,
                        message TEXT NOT NULL,
                        channel_id INTEGER,
                        created_at INTEGER,
                        FOREIGN KEY (tribute_id) REFERENCES tributes(tribute_id) ON DELETE CASCADE
                    )
                """)
                
                # Copy data from old table (keeping only the most recent prompt per tribute)
                cursor.execute("""
                    INSERT INTO prompts (id, tribute_id, message, channel_id, created_at)
                    SELECT id, tribute_id, message, channel_id, created_at
                    FROM (
                        SELECT * FROM prompts_old
                        ORDER BY tribute_id, id DESC
                    )
                    GROUP BY tribute_id
                """)
                
                # Drop old table
                cursor.execute("DROP TABLE prompts_old")
                
                # Recreate index
                cursor.execute("CREATE INDEX idx_prompts_tribute_id ON prompts(tribute_id)")
                
                conn.commit()
                logger.info("✓ Successfully migrated prompts table to 1:1 relationship")
            except sqlite3.OperationalError as e:
                logger.error(f"Failed to migrate prompts table: {e}")
    
    # TRIBUTE CRUD OPERATIONS
    
    def create_tribute(
        self, 
        tribute_id: str, 
        tribute_name: str, 
        user_id: int, 
        user_mention: str,
        guild_id: Optional[int] = None,
        created_at: Optional[int] = None,
        face_claim_url: Optional[str] = None,
        prompt_channel_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a new tribute."""
        import time
        if created_at is None:
            created_at = int(time.time())
        
        with self._lock:
            with self.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO tributes (tribute_id, tribute_name, user_id, user_mention, guild_id, created_at, face_claim_url, prompt_channel_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (tribute_id, tribute_name, user_id, user_mention, guild_id, created_at, face_claim_url, prompt_channel_id))
                
                tribute_row_id = cursor.lastrowid
                cursor.execute("SELECT * FROM tributes WHERE id = ?", (tribute_row_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
    
    def get_tribute(self, tribute_id: str) -> Optional[Dict[str, Any]]:
        """Get tribute by tribute_id."""
        with self._lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tributes WHERE tribute_id = ?", (tribute_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_all_tributes(self, guild_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all tributes, optionally filtered by guild."""
        with self._lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            if guild_id:
                cursor.execute("SELECT * FROM tributes WHERE guild_id = ? ORDER BY tribute_id", (guild_id,))
            else:
                cursor.execute("SELECT * FROM tributes ORDER BY tribute_id")
            return [dict(row) for row in cursor.fetchall()]
    
    def update_tribute(self, tribute_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Update tribute attributes."""
        with self._lock:
            with self.transaction() as conn:
                cursor = conn.cursor()
                allowed_fields = {'tribute_name', 'user_mention', 'guild_id'}
                updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
                
                if not updates:
                    cursor.execute("SELECT * FROM tributes WHERE tribute_id = ?", (tribute_id,))
                    row = cursor.fetchone()
                    return dict(row) if row else None
                
                set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
                cursor.execute(
                    f"UPDATE tributes SET {set_clause} WHERE tribute_id = ?",
                    list(updates.values()) + [tribute_id]
                )
                cursor.execute("SELECT * FROM tributes WHERE tribute_id = ?", (tribute_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
    
    def delete_tribute(self, tribute_id: str) -> bool:
        """Delete tribute and cascade delete all related data."""
        with self._lock:
            with self.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM tributes WHERE tribute_id = ?", (tribute_id,))
                return cursor.rowcount > 0
    
    def get_tribute_full(self, tribute_id: str) -> Optional[Dict[str, Any]]:
        """Get complete tribute data including inventory, prompt, and files."""
        with self._lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get tribute
            cursor.execute("SELECT * FROM tributes WHERE tribute_id = ?", (tribute_id,))
            tribute = cursor.fetchone()
            if not tribute:
                return None
            
            result = dict(tribute)
            
            # Get inventory
            cursor.execute("SELECT * FROM inventories WHERE tribute_id = ?", (tribute_id,))
            inv_row = cursor.fetchone()
            if inv_row:
                result['inventory'] = dict(inv_row)
                cursor.execute("""
                    SELECT item_number, item_name FROM inventory_items
                    WHERE tribute_id = ? ORDER BY item_number
                """, (tribute_id,))
                result['inventory']['items'] = {str(row['item_number']): row['item_name'] for row in cursor.fetchall()}
            
            # Get prompt
            cursor.execute("SELECT * FROM prompts WHERE tribute_id = ?", (tribute_id,))
            prompt_row = cursor.fetchone()
            result['prompt'] = dict(prompt_row) if prompt_row else None
            
            # Get files
            cursor.execute("SELECT * FROM files WHERE tribute_id = ?", (tribute_id,))
            result['files'] = [dict(row) for row in cursor.fetchall()]
            
            return result
    
    # INVENTORY CRUD OPERATIONS
    
    def create_inventory(self, tribute_id: str, capacity: int = 10) -> Dict[str, Any]:
        """Create inventory for a tribute."""
        with self._lock:
            with self.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO inventories (tribute_id, capacity)
                    VALUES (?, ?)
                """, (tribute_id, capacity))
                
                cursor.execute("SELECT * FROM inventories WHERE tribute_id = ?", (tribute_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
    
    def get_inventory(self, tribute_id: str) -> Optional[Dict[str, Any]]:
        """Get inventory for a tribute."""
        with self._lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM inventories WHERE tribute_id = ?", (tribute_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_inventory_items(self, tribute_id: str) -> List[Dict[str, Any]]:
        """Get all items for a tribute's inventory."""
        with self._lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT item_number, item_name FROM inventory_items 
                WHERE tribute_id = ? 
                ORDER BY item_number
            """, (tribute_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def add_inventory_item(self, tribute_id: str, item_name: str) -> int:
        """Add item to inventory, returns new item number."""
        with self._lock:
            with self.transaction() as conn:
                cursor = conn.cursor()
                # Get next item number
                cursor.execute("""
                    SELECT COALESCE(MAX(item_number), 0) + 1 as next_num
                    FROM inventory_items
                    WHERE tribute_id = ?
                """, (tribute_id,))
                next_num = cursor.fetchone()['next_num']
                
                cursor.execute("""
                    INSERT INTO inventory_items (tribute_id, item_number, item_name)
                    VALUES (?, ?, ?)
                """, (tribute_id, next_num, item_name))
                
                # Update inventory updated_at
                cursor.execute("""
                    UPDATE inventories SET updated_at = CURRENT_TIMESTAMP
                    WHERE tribute_id = ?
                """, (tribute_id,))
                
                return next_num
    
    def remove_inventory_item(self, tribute_id: str, item_number: int) -> bool:
        """Remove item from inventory and rekey remaining items."""
        with self._lock:
            with self.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM inventory_items
                    WHERE tribute_id = ? AND item_number = ?
                """, (tribute_id, item_number))
                
                if cursor.rowcount == 0:
                    return False
                
                # Rekey remaining items
                cursor.execute("""
                    SELECT * FROM inventory_items
                    WHERE tribute_id = ?
                    ORDER BY item_number
                """, (tribute_id,))
                items = cursor.fetchall()
                
                for idx, item in enumerate(items, 1):
                    cursor.execute("""
                        UPDATE inventory_items
                        SET item_number = ?
                        WHERE tribute_id = ? AND item_name = ?
                    """, (idx, tribute_id, item['item_name']))
                
                # Update inventory updated_at
                cursor.execute("""
                    UPDATE inventories SET updated_at = CURRENT_TIMESTAMP
                    WHERE tribute_id = ?
                """, (tribute_id,))
                
                return True
    
    def clear_inventory(self, tribute_id: str) -> bool:
        """Clear all items from inventory."""
        with self._lock:
            with self.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM inventory_items
                    WHERE tribute_id = ?
                """, (tribute_id,))
                
                cursor.execute("""
                    UPDATE inventories SET updated_at = CURRENT_TIMESTAMP
                    WHERE tribute_id = ?
                """, (tribute_id,))
                
                return True
    
    def search_inventory_items(self, item_name: str) -> List[Dict[str, Any]]:
        """Search for tributes with a specific item."""
        with self._lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.tribute_id, t.tribute_name, t.user_mention, ii.item_number, ii.item_name
                FROM inventory_items ii
                JOIN tributes t ON ii.tribute_id = t.tribute_id
                WHERE ii.item_name LIKE ?
                ORDER BY t.tribute_id, ii.item_number
            """, (f"%{item_name}%",))
            return [dict(row) for row in cursor.fetchall()]
    
    # PROMPT CRUD OPERATIONS
    
    def create_prompt(
        self,
        tribute_id: str,
        message: str,
        channel_id: int
    ) -> Dict[str, Any]:
        """Create a prompt for a tribute (1:1 relationship)."""
        import time
        created_at = int(time.time())
        
        with self._lock:
            with self.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO prompts (tribute_id, message, channel_id, created_at)
                    VALUES (?, ?, ?, ?)
                """, (tribute_id, message, channel_id, created_at))
                
                cursor.execute("""
                    SELECT * FROM prompts WHERE tribute_id = ?
                """, (tribute_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
    
    def get_prompt(self, tribute_id: str) -> Optional[Dict[str, Any]]:
        """Get prompt for a tribute."""
        with self._lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM prompts WHERE tribute_id = ?
            """, (tribute_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_all_prompts(self, guild_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all prompts, optionally filtered by guild."""
        with self._lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            if guild_id:
                cursor.execute("""
                    SELECT p.* FROM prompts p
                    JOIN tributes t ON p.tribute_id = t.tribute_id
                    WHERE t.guild_id = ?
                    ORDER BY p.tribute_id
                """, (guild_id,))
            else:
                cursor.execute("""
                    SELECT * FROM prompts
                    ORDER BY tribute_id
                """)
            return [dict(row) for row in cursor.fetchall()]
    
    def update_prompt(
        self,
        tribute_id: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Update prompt fields."""
        with self._lock:
            with self.transaction() as conn:
                cursor = conn.cursor()
                allowed_fields = {'message', 'channel_id'}
                updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
                
                if not updates:
                    return self.get_prompt(tribute_id)
                
                set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
                cursor.execute(
                    f"UPDATE prompts SET {set_clause} WHERE tribute_id = ?",
                    list(updates.values()) + [tribute_id]
                )
                return self.get_prompt(tribute_id)
    
    def delete_prompt(self, tribute_id: str) -> bool:
        """Delete a prompt."""
        with self._lock:
            with self.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM prompts WHERE tribute_id = ?
                """, (tribute_id,))
                return cursor.rowcount > 0
    
    def delete_all_prompts(self) -> int:
        """Delete all prompts."""
        with self._lock:
            with self.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM prompts")
                return cursor.rowcount
    
    # FILE CRUD OPERATIONS
    
    def add_file(self, tribute_id: str, file_type: str, file_path: str) -> Dict[str, Any]:
        """Add a file to a tribute."""
        with self._lock:
            with self.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO files (tribute_id, file_type, file_path, created_at)
                    VALUES (?, ?, ?, ?)
                """, (tribute_id, file_type, file_path, int(__import__('time').time())))
                
                file_id = cursor.lastrowid
                cursor.execute("SELECT * FROM files WHERE id = ?", (file_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
    
    def get_files(self, tribute_id: str, file_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get files for a tribute, optionally filtered by type."""
        with self._lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            if file_type:
                cursor.execute("""
                    SELECT * FROM files WHERE tribute_id = ? AND file_type = ?
                """, (tribute_id, file_type))
            else:
                cursor.execute("""
                    SELECT * FROM files WHERE tribute_id = ?
                """, (tribute_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def delete_file(self, file_id: int) -> bool:
        """Delete a file."""
        with self._lock:
            with self.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM files WHERE id = ?", (file_id,))
                return cursor.rowcount > 0
