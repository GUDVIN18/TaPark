from app.core.db import db_pool, Connection
from loguru import logger as log
from app.support_ai.resources.schemas.user_profile import UserProfile, UserProfileFrom
from app.core.db.tables import user_profile_table
import uuid


class UserProfileCrud:
    @staticmethod
    async def create(
        conn: Connection, 
        data: UserProfile
    ) -> UserProfileFrom | None:
        query = (
            user_profile_table.insert().values(
                uuid=uuid.uuid4(),
                user_id=data.user_id
            ).returning(*user_profile_table.c)
        )

        record = await conn.fetch_one(query)
        log.info(f"UserProfileCrud.create: Created user profile for user_id={data.user_id}, record={record}")
        return UserProfileFrom(**record._mapping) if record else None

    
    @staticmethod
    async def get(
        conn: Connection,
        user_id: int,
    ) -> UserProfileFrom | None:
        query = (
            user_profile_table.select()
            .where(user_profile_table.c.user_id == user_id)
            .limit(1)
        )
        record = await conn.fetch_one(query)
        log.info(f"UserProfileCrud.get: Retrieved user profile for user_id={user_id}, record={record}")
        return UserProfileFrom(**record._mapping) if record else None