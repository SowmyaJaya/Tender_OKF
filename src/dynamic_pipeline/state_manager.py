import sqlite3
import datetime
from pathlib import Path
from contextlib import closing
from typing import Optional, List, Dict


class StateManager:
    """
    Manages the SQLite database to track the pipeline state of BMRCL tender documents.
    Prevents redundant processing by saving checkpoints (extraction, review, okf_generation).
    """

    VALID_STATUSES = [
        "registered",     # PDF uploaded/detected
        "extracted",      # Heuristic parser generated the JSON
        "reviewed",       # Human approved the JSON structure
        "okf_generated",  # Markdown and YAML generated
        "wiki_linked",    # LLM added semantic cross-references
        "failed",         # Error occurred during processing
    ]

    def __init__(self, db_path: str = "data/pipeline_state.db"):
        self.db_path = db_path
        # Ensure the data directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self):
        """Returns a database connection with dictionary-like rows."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initializes the documents table if it does not exist."""
        with closing(self._get_connection()) as conn, conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    source_sha256 TEXT PRIMARY KEY,
                    source_path TEXT NOT NULL,
                    volume INTEGER,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def register_document(
        self,
        source_sha256: str,
        source_path: str,
        volume: Optional[int] = None,
    ) -> None:
        """
        Registers a new document into the tracking database.
        If the document already exists, it ignores the insertion.
        """
        with closing(self._get_connection()) as conn, conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO documents (
                    source_sha256,
                    source_path,
                    volume,
                    status,
                    last_updated
                )
                VALUES (?, ?, ?, 'registered', ?)
                """,
                (
                    source_sha256,
                    source_path,
                    volume,
                    datetime.datetime.now().isoformat(sep=" "),
                ),
            )

    def update_status(
        self,
        source_sha256: str,
        status: str,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Updates the processing checkpoint for a document.
        """
        if status not in self.VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{status}'. Must be one of "
                f"{self.VALID_STATUSES}"
            )

        with closing(self._get_connection()) as conn, conn:
            conn.execute(
                """
                UPDATE documents
                SET status = ?, error_message = ?, last_updated = ?
                WHERE source_sha256 = ?
                """,
                (
                    status,
                    error_message,
                    datetime.datetime.now().isoformat(sep=" "),
                    source_sha256,
                ),
            )

    def get_status(self, source_sha256: str) -> Optional[str]:
        """
        Retrieves the current status of a document by its hash.
        """
        with closing(self._get_connection()) as conn, conn:
            cursor = conn.execute(
                "SELECT status FROM documents WHERE source_sha256 = ?",
                (source_sha256,),
            )
            row = cursor.fetchone()
            return row["status"] if row else None

    def get_documents_by_status(self, status: str) -> List[Dict]:
        """
        Retrieves all documents currently sitting at a specific pipeline stage.
        Useful for batching operations (e.g., finding all 'extracted' docs to send to review).
        """
        if status not in self.VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{status}'. Must be one of "
                f"{self.VALID_STATUSES}"
            )

        with closing(self._get_connection()) as conn, conn:
            cursor = conn.execute(
                "SELECT * FROM documents WHERE status = ?",
                (status,),
            )
            return [dict(row) for row in cursor.fetchall()]
