from app.core.db import DBConnPool, Connection
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
                user_id=data.user_id,
                created_at=data.created_at,
            ).returning(*user_profile_table.c)
        )

        result = await conn.execute(query)
        row = await result.fetchone()
        return UserProfileFrom(**row._mapping) if row else None

    
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
        result = await conn.execute(query)
        row = await result.fetchone()
        return UserProfileFrom(**row._mapping) if row else None