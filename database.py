from pathlib import Path
import aiosqlite


class Database:
    """Asynchronous SQLite database manager for guild settings, warnings, tickets, bumps, and mod logs."""

    def __init__(self, db_path: str = "data/moderation.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self.conn = await aiosqlite.connect(self.db_path)
        self.conn.row_factory = aiosqlite.Row
        await self.initialize_schema()

    async def close(self) -> None:
        if self.conn:
            await self.conn.close()

    async def initialize_schema(self) -> None:
        assert self.conn is not None
        await self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                mod_log_channel_id INTEGER,
                audit_log_channel_id INTEGER,
                automod_enabled INTEGER DEFAULT 1,
                anti_spam_enabled INTEGER DEFAULT 1,
                spam_threshold INTEGER DEFAULT 5,
                spam_interval_sec INTEGER DEFAULT 5,
                block_links INTEGER DEFAULT 0,
                block_invites INTEGER DEFAULT 1,
                max_mentions INTEGER DEFAULT 5,
                warn_threshold_timeout INTEGER DEFAULT 3,
                warn_threshold_ban INTEGER DEFAULT 5,
                ticket_category_id INTEGER,
                ticket_log_channel_id INTEGER,
                ticket_support_role_id INTEGER,
                bump_channel_id INTEGER,
                bump_role_id INTEGER,
                next_bump_timestamp INTEGER DEFAULT 0,
                autopromo_channel_id INTEGER,
                autopromo_interval_min INTEGER DEFAULT 120,
                autopromo_message TEXT,
                antiraid_enabled INTEGER DEFAULT 1,
                antiraid_joins INTEGER DEFAULT 6,
                antiraid_interval_sec INTEGER DEFAULT 10,
                antiraid_min_account_days INTEGER DEFAULT 2,
                antiraid_action TEXT DEFAULT 'kick',
                ghostping_enabled INTEGER DEFAULT 1,
                scam_guard_enabled INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS staff_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                author_id INTEGER NOT NULL,
                note TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER UNIQUE NOT NULL,
                owner_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                claimed_by INTEGER,
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS bump_stats (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                bump_count INTEGER DEFAULT 0,
                last_bump_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS bad_words (
                guild_id INTEGER NOT NULL,
                word TEXT NOT NULL,
                PRIMARY KEY (guild_id, word)
            );

            CREATE TABLE IF NOT EXISTS mod_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                target_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        migrations = [
            "ALTER TABLE guild_settings ADD COLUMN antiraid_enabled INTEGER DEFAULT 1",
            "ALTER TABLE guild_settings ADD COLUMN antiraid_joins INTEGER DEFAULT 6",
            "ALTER TABLE guild_settings ADD COLUMN antiraid_interval_sec INTEGER DEFAULT 10",
            "ALTER TABLE guild_settings ADD COLUMN antiraid_min_account_days INTEGER DEFAULT 2",
            "ALTER TABLE guild_settings ADD COLUMN antiraid_action TEXT DEFAULT 'kick'",
            "ALTER TABLE guild_settings ADD COLUMN ghostping_enabled INTEGER DEFAULT 1",
            "ALTER TABLE guild_settings ADD COLUMN scam_guard_enabled INTEGER DEFAULT 1",
        ]
        for sql in migrations:
            try:
                await self.conn.execute(sql)
            except Exception:
                pass
        await self.conn.commit()

    async def get_guild_settings(self, guild_id: int) -> dict:
        assert self.conn is not None
        async with self.conn.execute(
            "SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)

        await self.conn.execute(
            "INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (guild_id,)
        )
        await self.conn.commit()
        async with self.conn.execute(
            "SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else {}

    async def update_guild_setting(
        self, guild_id: int, column: str, value: int | str | None
    ) -> None:
        allowed_columns = {
            "mod_log_channel_id",
            "audit_log_channel_id",
            "automod_enabled",
            "anti_spam_enabled",
            "spam_threshold",
            "spam_interval_sec",
            "block_links",
            "block_invites",
            "max_mentions",
            "warn_threshold_timeout",
            "warn_threshold_ban",
            "ticket_category_id",
            "ticket_log_channel_id",
            "ticket_support_role_id",
            "bump_channel_id",
            "bump_role_id",
            "next_bump_timestamp",
            "autopromo_channel_id",
            "autopromo_interval_min",
            "autopromo_message",
            "antiraid_enabled",
            "antiraid_joins",
            "antiraid_interval_sec",
            "antiraid_min_account_days",
            "antiraid_action",
            "ghostping_enabled",
            "scam_guard_enabled",
        }
        if column not in allowed_columns:
            raise ValueError(f"Invalid setting column: {column}")

        assert self.conn is not None
        await self.get_guild_settings(guild_id)
        await self.conn.execute(
            f"UPDATE guild_settings SET {column} = ? WHERE guild_id = ?",
            (value, guild_id),
        )
        await self.conn.commit()

    # --- Staff Notes Management (Dossier) ---
    async def add_staff_note(
        self, guild_id: int, user_id: int, author_id: int, note: str
    ) -> int:
        assert self.conn is not None
        cursor = await self.conn.execute(
            "INSERT INTO staff_notes (guild_id, user_id, author_id, note) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, author_id, note),
        )
        await self.conn.commit()
        return cursor.lastrowid or 0

    async def get_staff_notes(self, guild_id: int, user_id: int) -> list[dict]:
        assert self.conn is not None
        async with self.conn.execute(
            "SELECT * FROM staff_notes WHERE guild_id = ? AND user_id = ? ORDER BY created_at DESC",
            (guild_id, user_id),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_user_mod_cases(self, guild_id: int, target_id: int) -> list[dict]:
        assert self.conn is not None
        async with self.conn.execute(
            "SELECT * FROM mod_cases WHERE guild_id = ? AND target_id = ? ORDER BY id DESC LIMIT 10",
            (guild_id, target_id),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    # --- Tickets Management ---
    async def create_ticket(
        self, guild_id: int, channel_id: int, owner_id: int, category: str
    ) -> int:
        assert self.conn is not None
        cursor = await self.conn.execute(
            "INSERT INTO tickets (guild_id, channel_id, owner_id, category) VALUES (?, ?, ?, ?)",
            (guild_id, channel_id, owner_id, category),
        )
        await self.conn.commit()
        return cursor.lastrowid or 0

    async def get_open_ticket_by_user(
        self, guild_id: int, owner_id: int
    ) -> dict | None:
        """Finds any open or archived ticket belonging to user (prevents opening duplicates)."""
        assert self.conn is not None
        async with self.conn.execute(
            "SELECT * FROM tickets WHERE guild_id = ? AND owner_id = ? AND status IN ('open', 'archived')",
            (guild_id, owner_id),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_active_ticket_by_user(
        self, guild_id: int, owner_id: int
    ) -> dict | None:
        return await self.get_open_ticket_by_user(guild_id, owner_id)

    async def get_ticket_by_channel(self, channel_id: int) -> dict | None:
        assert self.conn is not None
        async with self.conn.execute(
            "SELECT * FROM tickets WHERE channel_id = ?", (channel_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def claim_ticket(self, channel_id: int, moderator_id: int) -> None:
        assert self.conn is not None
        await self.conn.execute(
            "UPDATE tickets SET claimed_by = ? WHERE channel_id = ?",
            (moderator_id, channel_id),
        )
        await self.conn.commit()

    async def close_ticket_record(self, channel_id: int) -> None:
        assert self.conn is not None
        await self.conn.execute(
            "UPDATE tickets SET status = 'closed' WHERE channel_id = ?",
            (channel_id,),
        )
        await self.conn.commit()

    async def archive_ticket_record(self, channel_id: int) -> None:
        assert self.conn is not None
        await self.conn.execute(
            "UPDATE tickets SET status = 'archived' WHERE channel_id = ?",
            (channel_id,),
        )
        await self.conn.commit()

    async def reopen_ticket_record(self, channel_id: int) -> None:
        assert self.conn is not None
        await self.conn.execute(
            "UPDATE tickets SET status = 'open' WHERE channel_id = ?",
            (channel_id,),
        )
        await self.conn.commit()

    # --- Bump Tracker & Leaderboard ---
    async def record_bump(self, guild_id: int, user_id: int, next_timestamp: int) -> int:
        assert self.conn is not None
        await self.conn.execute(
            """
            INSERT INTO bump_stats (guild_id, user_id, bump_count, last_bump_at)
            VALUES (?, ?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET
                bump_count = bump_count + 1,
                last_bump_at = CURRENT_TIMESTAMP
            """,
            (guild_id, user_id),
        )
        await self.update_guild_setting(guild_id, "next_bump_timestamp", next_timestamp)
        async with self.conn.execute(
            "SELECT bump_count FROM bump_stats WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        ) as cursor:
            row = await cursor.fetchone()
            return row["bump_count"] if row else 1

    async def get_bump_leaderboard(self, guild_id: int, limit: int = 10) -> list[dict]:
        assert self.conn is not None
        async with self.conn.execute(
            "SELECT user_id, bump_count, last_bump_at FROM bump_stats WHERE guild_id = ? ORDER BY bump_count DESC LIMIT ?",
            (guild_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_due_bumps(self, current_timestamp: int) -> list[dict]:
        assert self.conn is not None
        async with self.conn.execute(
            "SELECT * FROM guild_settings WHERE next_bump_timestamp > 0 AND next_bump_timestamp <= ?",
            (current_timestamp,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    # --- Warnings Management ---
    async def add_warning(
        self, guild_id: int, user_id: int, moderator_id: int, reason: str
    ) -> int:
        assert self.conn is not None
        cursor = await self.conn.execute(
            "INSERT INTO warnings (guild_id, user_id, moderator_id, reason) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, moderator_id, reason),
        )
        await self.conn.commit()
        return cursor.lastrowid or 0

    async def get_warnings(self, guild_id: int, user_id: int) -> list[dict]:
        assert self.conn is not None
        async with self.conn.execute(
            "SELECT * FROM warnings WHERE guild_id = ? AND user_id = ? ORDER BY created_at DESC",
            (guild_id, user_id),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def remove_warning(self, guild_id: int, warning_id: int) -> bool:
        assert self.conn is not None
        cursor = await self.conn.execute(
            "DELETE FROM warnings WHERE guild_id = ? AND id = ?",
            (guild_id, warning_id),
        )
        await self.conn.commit()
        return cursor.rowcount > 0

    async def clear_warnings(self, guild_id: int, user_id: int) -> int:
        assert self.conn is not None
        cursor = await self.conn.execute(
            "DELETE FROM warnings WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        await self.conn.commit()
        return cursor.rowcount

    # --- Bad Words Management ---
    async def get_bad_words(self, guild_id: int) -> list[str]:
        assert self.conn is not None
        async with self.conn.execute(
            "SELECT word FROM bad_words WHERE guild_id = ? ORDER BY word ASC",
            (guild_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [r["word"] for r in rows]

    async def add_bad_word(self, guild_id: int, word: str) -> bool:
        assert self.conn is not None
        word_clean = word.strip().lower()
        cursor = await self.conn.execute(
            "INSERT OR IGNORE INTO bad_words (guild_id, word) VALUES (?, ?)",
            (guild_id, word_clean),
        )
        await self.conn.commit()
        return cursor.rowcount > 0

    async def remove_bad_word(self, guild_id: int, word: str) -> bool:
        assert self.conn is not None
        word_clean = word.strip().lower()
        cursor = await self.conn.execute(
            "DELETE FROM bad_words WHERE guild_id = ? AND word = ?",
            (guild_id, word_clean),
        )
        await self.conn.commit()
        return cursor.rowcount > 0

    # --- Mod Cases ---
    async def log_mod_case(
        self,
        guild_id: int,
        action: str,
        target_id: int,
        moderator_id: int,
        reason: str | None = None,
    ) -> int:
        assert self.conn is not None
        cursor = await self.conn.execute(
            "INSERT INTO mod_cases (guild_id, action, target_id, moderator_id, reason) VALUES (?, ?, ?, ?, ?)",
            (guild_id, action, target_id, moderator_id, reason or "no reason given"),
        )
        await self.conn.commit()
        return cursor.lastrowid or 0
