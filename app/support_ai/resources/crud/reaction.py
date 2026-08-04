import uuid
from app.core.db import db_pool, Connection
from app.core.db.tables import chat_history_table
from app.support_ai.resources.schemas import ReactionRequest
from loguru import logger as log


class ReactionCrud:
    @staticmethod
    async def set_reaction(conn: Connection, data: ReactionRequest):
        query = (
            chat_history_table.update()
            .where(
                chat_history_table.c.id == data.message_id,
                chat_history_table.c.user_id == data.user_id,
                chat_history_table.c.uuid == str(data.message_uuid)
            )
            .values(reactions=data.reaction)
        )
        await conn.execute(query)
        