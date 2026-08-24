"""AWS-hosted database connectivity, used to validate data before/after a test.

Credential resolution priority:
  1. AWS Secrets Manager, if ORM_DB_SECRET_ARN is set. Intended for the AWS VPS
     runner: boto3 authenticates via the instance/task IAM role (no plaintext
     DB password ever stored on disk there).
  2. Plain ORM_DB_* variables from the environment's .env file (ORM_DB_HOST,
     ORM_DB_USER, ORM_DB_PASSWORD, ORM_DB_DATABASE, ORM_DB_SCHEMA, DISABLE_SSL).
     Intended for local runs, where the AWS VPN client already puts you on the
     DB's network.

Only PostgreSQL is supported (psycopg2). Install the extra with:
    pip install refua-automation-core[db]
"""

from __future__ import annotations

import json
import logging
import os
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Optional, Sequence

logger = logging.getLogger(__name__)


class DatabaseNotConfiguredError(Exception):
    """Raised when no DB credentials can be resolved for the current environment."""


@dataclass(frozen=True)
class DbCredentials:
    host: str
    port: int
    dbname: str
    user: str
    password: str
    schema: Optional[str] = None
    sslmode: str = "require"


def _disable_ssl() -> bool:
    return os.getenv("DISABLE_SSL", "false").strip().lower() in ("true", "1", "yes")


class DatabaseManager:
    """Singleton providing psycopg2 connections and query helpers.

    Usage:
        db = DatabaseManager()
        rows = db.fetch_all("SELECT * FROM patients WHERE id = %s", (patient_id,))
    """

    _instance: Optional["DatabaseManager"] = None

    def __new__(cls) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _resolve_credentials(self) -> DbCredentials:
        secret_arn = os.getenv("ORM_DB_SECRET_ARN")
        if secret_arn:
            return self._credentials_from_secrets_manager(secret_arn)

        return self._credentials_from_env()

    @staticmethod
    def _credentials_from_env() -> DbCredentials:
        host = os.getenv("ORM_DB_HOST")
        user = os.getenv("ORM_DB_USER")
        password = os.getenv("ORM_DB_PASSWORD")
        dbname = os.getenv("ORM_DB_DATABASE")

        missing = [
            name
            for name, value in (
                ("ORM_DB_HOST", host),
                ("ORM_DB_USER", user),
                ("ORM_DB_PASSWORD", password),
                ("ORM_DB_DATABASE", dbname),
            )
            if not value
        ]
        if missing:
            raise DatabaseNotConfiguredError(
                f"Missing DB configuration: {', '.join(missing)}. "
                "Set them in the environment's .env file, or set ORM_DB_SECRET_ARN "
                "to load credentials from AWS Secrets Manager instead."
            )

        return DbCredentials(
            host=host,  # type: ignore[arg-type]
            port=int(os.getenv("ORM_DB_PORT", "5432")),
            dbname=dbname,  # type: ignore[arg-type]
            user=user,  # type: ignore[arg-type]
            password=password,  # type: ignore[arg-type]
            schema=os.getenv("ORM_DB_SCHEMA") or None,
            sslmode="disable" if _disable_ssl() else "require",
        )

    @staticmethod
    def _credentials_from_secrets_manager(secret_arn: str) -> DbCredentials:
        try:
            import boto3
        except ImportError as exc:
            raise DatabaseNotConfiguredError(
                "boto3 is required to load DB credentials from AWS Secrets Manager. "
                "Install with: pip install refua-automation-core[db]"
            ) from exc

        region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "il-central-1"
        client = boto3.client("secretsmanager", region_name=region)

        try:
            response = client.get_secret_value(SecretId=secret_arn)
            secret = json.loads(response["SecretString"])
        except Exception as exc:  # noqa: BLE001 - collapse to one clear error type
            raise DatabaseNotConfiguredError(
                f"Failed to load secret '{secret_arn}' from AWS Secrets Manager: {exc}"
            ) from exc

        # AWS RDS-managed secrets use these key names; dbname/schema fall back to env overrides.
        return DbCredentials(
            host=secret["host"],
            port=int(secret.get("port", 5432)),
            dbname=secret.get("dbname") or os.getenv("ORM_DB_DATABASE", ""),
            user=secret["username"],
            password=secret["password"],
            schema=os.getenv("ORM_DB_SCHEMA") or None,
            sslmode="disable" if _disable_ssl() else "require",
        )

    @contextmanager
    def get_connection(self) -> Iterator[Any]:
        """Yield a psycopg2 connection; closed on exit. Sets search_path if ORM_DB_SCHEMA is set."""
        try:
            import psycopg2
        except ImportError as exc:
            raise DatabaseNotConfiguredError(
                "psycopg2 is required for DB access. "
                "Install with: pip install refua-automation-core[db]"
            ) from exc

        creds = self._resolve_credentials()
        conn = psycopg2.connect(
            host=creds.host,
            port=creds.port,
            dbname=creds.dbname,
            user=creds.user,
            password=creds.password,
            sslmode=creds.sslmode,
            options=f"-c search_path={creds.schema}" if creds.schema else None,
            connect_timeout=10,
        )
        try:
            yield conn
        finally:
            conn.close()

    def fetch_all(self, query: str, params: Optional[Sequence[Any]] = None) -> list[dict]:
        """Run a SELECT and return all rows as a list of dicts."""
        with self.get_connection() as conn, conn.cursor() as cur:
            cur.execute(query, params)
            columns = [col.name for col in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]

    def fetch_one(self, query: str, params: Optional[Sequence[Any]] = None) -> Optional[dict]:
        """Run a SELECT and return the first row as a dict, or None if no rows matched."""
        rows = self.fetch_all(query, params)
        return rows[0] if rows else None

    def execute(self, statement: str, params: Optional[Sequence[Any]] = None) -> int:
        """Run an INSERT/UPDATE/DELETE (e.g. seeding or cleaning up test data) and commit."""
        with self.get_connection() as conn, conn.cursor() as cur:
            cur.execute(statement, params)
            conn.commit()
            return cur.rowcount
