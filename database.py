"""
database.py
------------
Handles all SQLite database operations for SmartRuleAI.

This module is responsible for:
- Creating the database schema (facts, rules, conversations)
- Providing CRUD (Create, Read, Update, Delete) operations
- Seeding the database with an expanded cybersecurity knowledge base
  on first run

Keeping all raw SQL in one place makes the rest of the application
(knowledge_base.py, rules.py, reasoning_engine.py, chatbot.py, app.py)
completely independent of how data is actually stored.

Web note: Flask's dev/production server can dispatch requests from more
than one thread, so the connection is opened with check_same_thread=False
and every write goes through a re-entrant lock.
"""

import os
import sqlite3
import threading
from datetime import datetime

DB_FILENAME = os.environ.get("SMARTRULE_DB", "smartrule_ai.db")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_FILENAME)


class Database:
    """Thin wrapper around sqlite3 that exposes simple, safe methods."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._lock = threading.RLock()
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.row_factory = sqlite3.Row
        self._create_tables()

    # ------------------------------------------------------------------
    # Schema creation
    # ------------------------------------------------------------------
    def _create_tables(self):
        with self._lock:
            cursor = self.connection.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    concept TEXT UNIQUE NOT NULL,
                    statement TEXT NOT NULL,
                    keywords TEXT NOT NULL DEFAULT '',
                    category TEXT NOT NULL DEFAULT 'general',
                    polarity TEXT NOT NULL DEFAULT 'neutral',
                    is_base INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    if_concept TEXT NOT NULL,
                    then_concept TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender TEXT NOT NULL,
                    message TEXT NOT NULL,
                    mood TEXT NOT NULL DEFAULT '',
                    timestamp TEXT NOT NULL
                )
            """)

            self.connection.commit()

            # Lightweight migration for DBs created by earlier versions
            existing_cols = {row["name"] for row in cursor.execute("PRAGMA table_info(facts)")}
            if "category" not in existing_cols:
                cursor.execute("ALTER TABLE facts ADD COLUMN category TEXT NOT NULL DEFAULT 'general'")
            if "polarity" not in existing_cols:
                cursor.execute("ALTER TABLE facts ADD COLUMN polarity TEXT NOT NULL DEFAULT 'neutral'")
            conv_cols = {row["name"] for row in cursor.execute("PRAGMA table_info(conversations)")}
            if "mood" not in conv_cols:
                cursor.execute("ALTER TABLE conversations ADD COLUMN mood TEXT NOT NULL DEFAULT ''")
            self.connection.commit()

    # ------------------------------------------------------------------
    # Facts CRUD
    # ------------------------------------------------------------------
    def add_fact(self, concept: str, statement: str, keywords: str = "",
                 is_base: int = 1, category: str = "general", polarity: str = "neutral"):
        concept = concept.strip().lower().replace(" ", "_")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._lock:
            try:
                cur = self.connection.cursor()
                cur.execute(
                    "INSERT INTO facts (concept, statement, keywords, category, polarity, is_base, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (concept, statement.strip(), keywords.strip().lower(), category, polarity, is_base, now),
                )
                self.connection.commit()
                return cur.lastrowid
            except sqlite3.IntegrityError:
                raise ValueError(f"A fact with concept '{concept}' already exists.")

    def get_all_facts(self):
        with self._lock:
            cur = self.connection.cursor()
            cur.execute("SELECT * FROM facts ORDER BY id ASC")
            return cur.fetchall()

    def get_fact_by_concept(self, concept: str):
        with self._lock:
            cur = self.connection.cursor()
            cur.execute("SELECT * FROM facts WHERE concept = ?", (concept,))
            return cur.fetchone()

    def get_fact_by_id(self, fact_id: int):
        with self._lock:
            cur = self.connection.cursor()
            cur.execute("SELECT * FROM facts WHERE id = ?", (fact_id,))
            return cur.fetchone()

    def update_fact(self, fact_id: int, concept: str, statement: str, keywords: str = "",
                     category: str = "general", polarity: str = "neutral"):
        concept = concept.strip().lower().replace(" ", "_")
        with self._lock:
            try:
                cur = self.connection.cursor()
                cur.execute(
                    "UPDATE facts SET concept = ?, statement = ?, keywords = ?, category = ?, polarity = ? WHERE id = ?",
                    (concept, statement.strip(), keywords.strip().lower(), category, polarity, fact_id),
                )
                self.connection.commit()
            except sqlite3.IntegrityError:
                raise ValueError(f"A fact with concept '{concept}' already exists.")

    def delete_fact(self, fact_id: int):
        with self._lock:
            cur = self.connection.cursor()
            cur.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
            self.connection.commit()

    # ------------------------------------------------------------------
    # Rules CRUD
    # ------------------------------------------------------------------
    def add_rule(self, name: str, if_concept: str, then_concept: str, description: str = ""):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if_concept = if_concept.strip().lower().replace(" ", "_")
        then_concept = then_concept.strip().lower().replace(" ", "_")
        with self._lock:
            cur = self.connection.cursor()
            cur.execute(
                "INSERT INTO rules (name, if_concept, then_concept, description, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (name.strip(), if_concept, then_concept, description.strip(), now),
            )
            self.connection.commit()
            return cur.lastrowid

    def get_all_rules(self):
        with self._lock:
            cur = self.connection.cursor()
            cur.execute("SELECT * FROM rules ORDER BY id ASC")
            return cur.fetchall()

    def get_rule_by_id(self, rule_id: int):
        with self._lock:
            cur = self.connection.cursor()
            cur.execute("SELECT * FROM rules WHERE id = ?", (rule_id,))
            return cur.fetchone()

    def update_rule(self, rule_id: int, name: str, if_concept: str, then_concept: str, description: str = ""):
        if_concept = if_concept.strip().lower().replace(" ", "_")
        then_concept = then_concept.strip().lower().replace(" ", "_")
        with self._lock:
            cur = self.connection.cursor()
            cur.execute(
                "UPDATE rules SET name = ?, if_concept = ?, then_concept = ?, description = ? WHERE id = ?",
                (name.strip(), if_concept, then_concept, description.strip(), rule_id),
            )
            self.connection.commit()

    def delete_rule(self, rule_id: int):
        with self._lock:
            cur = self.connection.cursor()
            cur.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
            self.connection.commit()

    # ------------------------------------------------------------------
    # Conversations
    # ------------------------------------------------------------------
    def add_conversation(self, sender: str, message: str, mood: str = ""):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._lock:
            cur = self.connection.cursor()
            cur.execute(
                "INSERT INTO conversations (sender, message, mood, timestamp) VALUES (?, ?, ?, ?)",
                (sender, message, mood, now),
            )
            self.connection.commit()

    def get_all_conversations(self):
        with self._lock:
            cur = self.connection.cursor()
            cur.execute("SELECT * FROM conversations ORDER BY id ASC")
            return cur.fetchall()

    def search_conversations(self, keyword: str):
        with self._lock:
            cur = self.connection.cursor()
            like = f"%{keyword.lower()}%"
            cur.execute(
                "SELECT * FROM conversations WHERE LOWER(message) LIKE ? ORDER BY id ASC",
                (like,),
            )
            return cur.fetchall()

    def clear_conversations(self):
        with self._lock:
            cur = self.connection.cursor()
            cur.execute("DELETE FROM conversations")
            self.connection.commit()

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------
    def get_stats(self):
        with self._lock:
            cur = self.connection.cursor()
            cur.execute("SELECT COUNT(*) AS c FROM facts")
            facts_count = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) AS c FROM rules")
            rules_count = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) AS c FROM conversations")
            conv_count = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) AS c FROM facts WHERE is_base = 0")
            derived_count = cur.fetchone()["c"]
            return {
                "facts": facts_count,
                "rules": rules_count,
                "conversations": conv_count,
                "derived_facts": derived_count,
            }

    # ------------------------------------------------------------------
    # Sample data seeding
    # ------------------------------------------------------------------
    def seed_sample_data(self):
        """Populate the database with an expanded set of sample cybersecurity
        facts and rules the first time the application is run (i.e. when the
        facts table is empty)."""
        existing = self.get_all_facts()
        if existing:
            return  # already seeded, do nothing

        from seed_data import SAMPLE_FACTS, SAMPLE_RULES

        for concept, statement, keywords, category, polarity in SAMPLE_FACTS:
            self.add_fact(concept, statement, keywords, is_base=1, category=category, polarity=polarity)

        for name, if_c, then_c, desc in SAMPLE_RULES:
            self.add_rule(name, if_c, then_c, desc)

    def close(self):
        self.connection.close()
