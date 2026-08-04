from .meta import metadata
from sqlalchemy import JSON, Column, DateTime, Integer, SmallInteger, String, Table, sql, BigInteger
from sqlalchemy.dialects.postgresql import UUID, JSONB


user_profile_table = Table(
    "user_profile",
    metadata,
    Column("id", Integer, primary_key=True),
    Column('uuid', UUID, nullable=False),
    Column("user_id", BigInteger, nullable=False, index=True),

    Column("created_at",
        DateTime(timezone=False),
        nullable=False,
        server_default=sql.func.now(),
        index=True,
    ),
    Column('updated_at', DateTime(timezone=False), nullable=True)
)