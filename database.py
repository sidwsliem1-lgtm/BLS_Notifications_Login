"""
SQLite database operations.
"""

import aiosqlite
from typing import Optional, Dict, Any

DATABASE_PATH = "sessions.db"


class Database:
    def __init__(self):
        self.connection = None
    
    async def init_db(self):
        self.connection = await aiosqlite.connect(DATABASE_PATH)
        await self._create_tables()
    
    async def _create_tables(self):
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                username TEXT DEFAULT '',
                full_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                super_fingerprint TEXT NOT NULL,
                ip TEXT NOT NULL,
                user_agent TEXT NOT NULL,
                os TEXT NOT NULL,
                browser TEXT NOT NULL,
                screen TEXT NOT NULL,
                timezone TEXT NOT NULL,
                language TEXT NOT NULL,
                canvas TEXT NOT NULL,
                webgl TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await self.connection.execute("CREATE INDEX IF NOT EXISTS idx_telegram_id ON sessions(telegram_id)")
        await self.connection.execute("CREATE INDEX IF NOT EXISTS idx_phone ON sessions(phone)")
        await self.connection.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON sessions(created_at)")
        await self.connection.commit()
    
    async def insert_session(self, session_data: Dict[str, Any]) -> int:
        query = """
            INSERT INTO sessions (
                telegram_id, username, full_name, phone, fingerprint,
                super_fingerprint, ip, user_agent, os, browser, screen,
                timezone, language, canvas, webgl
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor = await self.connection.execute(query, (
            session_data["telegram_id"],
            session_data["username"],
            session_data["full_name"],
            session_data["phone"],
            session_data["fingerprint"],
            session_data["super_fingerprint"],
            session_data["ip"],
            session_data["user_agent"],
            session_data["os"],
            session_data["browser"],
            session_data["screen"],
            session_data["timezone"],
            session_data["language"],
            session_data["canvas"],
            session_data["webgl"]
        ))
        await self.connection.commit()
        return cursor.lastrowid
    
    async def get_latest_session_by_telegram(self, telegram_id: int, exclude_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        query = "SELECT * FROM sessions WHERE telegram_id = ?"
        params = [telegram_id]
        if exclude_id:
            query += " AND id != ?"
            params.append(exclude_id)
        query += " ORDER BY created_at DESC LIMIT 1"
        cursor = await self.connection.execute(query, params)
        row = await cursor.fetchone()
        if row:
            return self._row_to_dict(row)
        return None
    
    async def get_latest_session_by_phone(self, phone: str, exclude_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        query = "SELECT * FROM sessions WHERE phone = ?"
        params = [phone]
        if exclude_id:
            query += " AND id != ?"
            params.append(exclude_id)
        query += " ORDER BY created_at DESC LIMIT 1"
        cursor = await self.connection.execute(query, params)
        row = await cursor.fetchone()
        if row:
            return self._row_to_dict(row)
        return None
    
    async def get_session_by_id(self, session_id: int) -> Optional[Dict[str, Any]]:
        cursor = await self.connection.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = await cursor.fetchone()
        if row:
            return self._row_to_dict(row)
        return None
    
    def _row_to_dict(self, row) -> Dict[str, Any]:
        return {
            "id": row[0],
            "telegram_id": row[1],
            "username": row[2],
            "full_name": row[3],
            "phone": row[4],
            "fingerprint": row[5],
            "super_fingerprint": row[6],
            "ip": row[7],
            "user_agent": row[8],
            "os": row[9],
            "browser": row[10],
            "screen": row[11],
            "timezone": row[12],
            "language": row[13],
            "canvas": row[14],
            "webgl": row[15],
            "created_at": row[16],
        }
    
    async def close(self):
        if self.connection:
            await self.connection.close()