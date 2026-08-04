from .meta import metadata
from sqlalchemy import JSON, Column, DateTime, Integer, SmallInteger, String, Table, sql, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB


chat_history_table = Table(
    "chat_history",
    metadata,
    Column("id", Integer, primary_key=True),
    Column('uuid', UUID, nullable=False),
    Column("user_id", Integer, nullable=True, index=True),
    Column('role', String, nullable=True),
    Column("content", String, nullable=True),
    Column("reactions", Boolean, nullable=True),

    Column("created_at",
        DateTime(timezone=False),
        nullable=False,
        server_default=sql.func.now(),
        index=True,
    ),
    Column('updated_at', DateTime(timezone=False), nullable=True)
)