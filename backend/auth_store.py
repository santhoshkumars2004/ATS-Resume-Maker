"""Simple SQLite-backed auth and persistence for self-hosted usage."""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


_DB_PATH: Path | None = None
_DATA_DIR: Path | None = None
_OUTPUT_DIR: Path | None = None
SESSION_LIFETIME_DAYS = 30
PASSWORD_ITERATIONS = 200_000


@dataclass
class AuthUser:
    """Authenticated user record."""
    id: int
    email: str
    name: str


def configure_auth_store(data_dir: Path, output_dir: Path) -> None:
    """Configure the auth store paths and ensure schema exists."""
    global _DB_PATH, _DATA_DIR, _OUTPUT_DIR

    _DATA_DIR = Path(data_dir)
    _OUTPUT_DIR = Path(output_dir)
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (_DATA_DIR / "users").mkdir(parents=True, exist_ok=True)
    _DB_PATH = _DATA_DIR / "app.db"
    _initialize_db()


def _require_paths() -> tuple[Path, Path, Path]:
    if not _DB_PATH or not _DATA_DIR or not _OUTPUT_DIR:
        raise RuntimeError("Auth store not configured.")
    return _DB_PATH, _DATA_DIR, _OUTPUT_DIR


def _connection() -> sqlite3.Connection:
    db_path, _, _ = _require_paths()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _initialize_db() -> None:
    with _connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS optimization_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                company_name TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                original_score INTEGER NOT NULL,
                optimized_score INTEGER NOT NULL,
                status TEXT NOT NULL,
                review_applied INTEGER NOT NULL DEFAULT 0,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, digest_hex = stored_hash.split("$", 1)
    except ValueError:
        return False

    recomputed = _hash_password(password, salt=bytes.fromhex(salt_hex))
    return hmac.compare_digest(recomputed, stored_hash)


def _validate_email(email: str) -> str:
    normalized = email.strip().lower()
    if "@" not in normalized or "." not in normalized.split("@", 1)[-1]:
        raise ValueError("Enter a valid email address.")
    return normalized


def _user_from_row(row: sqlite3.Row | None) -> AuthUser | None:
    if not row:
        return None
    return AuthUser(id=row["id"], email=row["email"], name=row["name"])


def create_user(name: str, email: str, password: str) -> AuthUser:
    """Register a new user."""
    clean_name = name.strip()
    if len(clean_name) < 2:
        raise ValueError("Name must be at least 2 characters.")
    clean_email = _validate_email(email)
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")

    created_at = _utcnow().isoformat()
    password_hash = _hash_password(password)

    try:
        with _connection() as conn:
            cursor = conn.execute(
                "INSERT INTO users (email, name, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (clean_email, clean_name, password_hash, created_at),
            )
            user_id = int(cursor.lastrowid)
    except sqlite3.IntegrityError as exc:
        raise ValueError("An account with that email already exists.") from exc

    return AuthUser(id=user_id, email=clean_email, name=clean_name)


def authenticate_user(email: str, password: str) -> AuthUser | None:
    """Authenticate a user by email/password."""
    clean_email = _validate_email(email)
    with _connection() as conn:
        row = conn.execute(
            "SELECT id, email, name, password_hash FROM users WHERE email = ?",
            (clean_email,),
        ).fetchone()

    if not row or not _verify_password(password, row["password_hash"]):
        return None
    return AuthUser(id=row["id"], email=row["email"], name=row["name"])


def create_session(user_id: int) -> str:
    """Create and persist a new session token."""
    token = secrets.token_urlsafe(32)
    created_at = _utcnow()
    expires_at = created_at + timedelta(days=SESSION_LIFETIME_DAYS)

    with _connection() as conn:
        conn.execute(
            "INSERT INTO sessions (user_id, token_hash, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (user_id, _token_hash(token), created_at.isoformat(), expires_at.isoformat()),
        )

    return token


def delete_session(token: str) -> None:
    """Delete a session token."""
    with _connection() as conn:
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))


def get_user_by_token(token: str | None) -> AuthUser | None:
    """Resolve the authenticated user for a bearer/session token."""
    if not token:
        return None

    now_iso = _utcnow().isoformat()
    with _connection() as conn:
        row = conn.execute(
            """
            SELECT users.id, users.email, users.name
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token_hash = ? AND sessions.expires_at > ?
            """,
            (_token_hash(token), now_iso),
        ).fetchone()

    return _user_from_row(row)


def user_storage_dir(user_id: int) -> Path:
    """Return the per-user storage directory."""
    _, data_dir, _ = _require_paths()
    path = data_dir / "users" / str(user_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def user_output_dir(user_id: int) -> Path:
    """Return the per-user output directory."""
    _, _, output_dir = _require_paths()
    path = output_dir / f"user_{user_id}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def slugify_company_name(company_name: str) -> str:
    """Build a stable folder-safe company slug."""
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", company_name.strip().lower()).strip("_")
    return cleaned or "company"


def build_run_output_dir(user_id: int, company_name: str, run_id: str) -> Path:
    """Return a structured output directory for a single optimization run."""
    base_dir = user_output_dir(user_id)
    company_dir = base_dir / slugify_company_name(company_name)
    run_dir = company_dir / f"run_{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def resolve_user_output_path(user_id: int, relative_path: str) -> Path:
    """Resolve a relative artifact path safely inside the user's output directory."""
    base_dir = user_output_dir(user_id).resolve()
    candidate = (base_dir / relative_path).resolve()
    if not candidate.is_relative_to(base_dir):
        raise ValueError("Invalid artifact path.")
    return candidate


def save_user_template_bytes(user_id: int, filename: str, content: bytes) -> tuple[Path, str]:
    """Save an uploaded resume template for a user."""
    storage_dir = user_storage_dir(user_id)
    lower_name = filename.lower()
    if lower_name.endswith(".pdf"):
        save_path = storage_dir / "resume_template.pdf"
        save_path.write_bytes(content)
        template_type = "pdf"
    else:
        save_path = storage_dir / "resume_template.tex"
        save_path.write_bytes(content)
        template_type = "tex"
    return save_path, template_type


def save_user_template_text(user_id: int, content: str) -> Path:
    """Save LaTeX template content for a user."""
    storage_dir = user_storage_dir(user_id)
    save_path = storage_dir / "resume_template.tex"
    save_path.write_text(content, encoding="utf-8")
    return save_path


def get_user_template(user_id: int) -> tuple[Path | None, str | None]:
    """Return the user's current template path and type."""
    storage_dir = user_storage_dir(user_id)
    pdf_path = storage_dir / "resume_template.pdf"
    tex_path = storage_dir / "resume_template.tex"
    if pdf_path.exists():
        return pdf_path, "pdf"
    if tex_path.exists():
        return tex_path, "tex"
    return None, None


def list_user_templates(user_id: int) -> list[dict[str, Any]]:
    """List templates for a user."""
    template_path, template_type = get_user_template(user_id)
    if not template_path or not template_type:
        return []
    return [{
        "name": template_path.name,
        "path": str(template_path),
        "type": template_type,
        "size": template_path.stat().st_size,
    }]


def save_history_entry(
    user_id: int,
    company_name: str,
    provider: str,
    model: str,
    original_score: int,
    optimized_score: int,
    status: str,
    review_applied: bool,
    result_payload: dict[str, Any],
) -> int:
    """Persist an optimization result for later retrieval."""
    created_at = _utcnow().isoformat()
    with _connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO optimization_history (
                user_id, company_name, provider, model, original_score, optimized_score,
                status, review_applied, result_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                company_name,
                provider,
                model,
                original_score,
                optimized_score,
                status,
                int(review_applied),
                json.dumps(result_payload),
                created_at,
            ),
        )
        return int(cursor.lastrowid)


def list_history_entries(user_id: int, limit: int = 25) -> list[dict[str, Any]]:
    """List recent optimization runs for a user."""
    with _connection() as conn:
        rows = conn.execute(
            """
            SELECT id, company_name, provider, model, original_score, optimized_score,
                   status, review_applied, created_at
            FROM optimization_history
            WHERE user_id = ?
            ORDER BY datetime(created_at) DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()

    return [dict(row) for row in rows]


def get_history_entry(user_id: int, entry_id: int) -> dict[str, Any] | None:
    """Return a full saved optimization result."""
    with _connection() as conn:
        row = conn.execute(
            """
            SELECT id, company_name, provider, model, original_score, optimized_score,
                   status, review_applied, created_at, result_json
            FROM optimization_history
            WHERE user_id = ? AND id = ?
            """,
            (user_id, entry_id),
        ).fetchone()

    if not row:
        return None

    payload = json.loads(row["result_json"])
    return {
        "id": row["id"],
        "company_name": row["company_name"],
        "provider": row["provider"],
        "model": row["model"],
        "original_score": row["original_score"],
        "optimized_score": row["optimized_score"],
        "status": row["status"],
        "review_applied": bool(row["review_applied"]),
        "created_at": row["created_at"],
        "result": payload,
    }


def delete_history_entry(user_id: int, entry_id: int) -> bool:
    """Delete a saved optimization result and its artifacts if present."""
    entry = get_history_entry(user_id, entry_id)
    if not entry:
        return False

    output_dir = entry.get("result", {}).get("output_dir", "").strip()
    with _connection() as conn:
        conn.execute(
            "DELETE FROM optimization_history WHERE user_id = ? AND id = ?",
            (user_id, entry_id),
        )

    if output_dir:
        try:
            output_path = resolve_user_output_path(user_id, output_dir)
        except ValueError:
            return True
        if output_path.exists() and output_path.is_dir():
            shutil.rmtree(output_path, ignore_errors=True)

    return True
