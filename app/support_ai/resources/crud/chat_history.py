import uuid
from app.core.db import db_pool, Connection
from app.core.db.tables import chat_history_table
from app.support_ai.resources.schemas.chat_history import ChatHistory, ChatHistoryFrom
from loguru import logger as log


class ChatHisoryCrud:
    @staticmethod
    async def create(
        conn: Connection,
        data: ChatHistory
    ) -> ChatHistoryFrom | None:
        query = (
            chat_history_table.insert().values(
                uuid=uuid.uuid4(),
                user_id=data.user_id,
                role=data.role,
                content=data.content,
            ).returning(*chat_history_table.c)
        )

        record = await conn.fetch_one(query)
        log.success(f"Создана запись в истории чата: {record}")
        return ChatHistoryFrom(**record._mapping) if record else None


    @staticmethod
    async def get(conn: Connection):
        pass