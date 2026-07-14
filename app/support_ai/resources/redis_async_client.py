import httpx
import json
import redis.asyncio as redis
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from app.include.logging_config import logger as log
from app.include.config import config


class AsyncRedisClient:
    def __init__(
            self,
            session_id: str,
            url: str = f"redis://:{config.REDIS_PASS}@{config.REDIS_IP}:{config.REDIS_PORT}/0",
            key_prefix: str = "support_ai_history:"
        ):
        self.session_id = session_id
        self.url = url
        self.key_prefix = key_prefix
        # Создаем асинхронный пул соединений с Redis
        self.client = redis.from_url(url, decode_responses=True)
        self.key = f"{key_prefix}{session_id}"
        self.ttl = 86400  # 1 день

    # вход в контекстный менеджер
    async def __aenter__(self):
        return self
    # автоматическое закрытие соединения
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def get_session_history_v2(
            self,
        ) -> list:
        
        # Асинхронный запрос к Redis
        history = await self.client.lrange(self.key, 0, -1)
        lc_messages = []
        
        for msg_str in history:
            data = json.loads(msg_str)
            if data['role'] == 'user':
                lc_messages.append(HumanMessage(content=data['content']))
            elif data['role'] == 'ai':
                lc_messages.append(AIMessage(content=data['content']))
        return lc_messages

    async def get_recent_rag_contexts(self, limit: int = 6) -> list[dict]:
        history = await self.client.lrange(self.key, 0, -1)
        rag_contexts = []

        for msg_str in reversed(history):
            data = json.loads(msg_str)
            rag_context = data.get("rag_context")
            if not rag_context:
                continue

            rag_contexts.append(rag_context)
            if len(rag_contexts) >= limit:
                break

        return list(reversed(rag_contexts))

    async def keep_recent_rag_contexts(self, limit: int = 6):
        history = await self.client.lrange(self.key, 0, -1)
        parsed_history = [json.loads(msg_str) for msg_str in history]
        found = 0
        changed = False

        for data in reversed(parsed_history):
            if not data.get("rag_context"):
                continue

            found += 1
            if found > limit:
                data.pop("rag_context", None)
                changed = True

        if not changed:
            return

        async with self.client.pipeline(transaction=True) as pipe:
            pipe.delete(self.key)
            if parsed_history:
                pipe.rpush(
                    self.key,
                    *[json.dumps(data, ensure_ascii=False) for data in parsed_history]
                )
            pipe.expire(self.key, self.ttl)
            await pipe.execute()

    async def add_message(self, role: str, message: str, **metadata):
        try:
            payload = {
                "role": role,
                "content": message
            }
            payload.update({key: value for key, value in metadata.items() if value is not None})

            message_data = json.dumps(payload, ensure_ascii=False)
            
            await self.client.rpush(self.key, message_data)
            await self.client.expire(self.key, self.ttl)
            if payload.get("rag_context"):
                await self.keep_recent_rag_contexts(limit=6)
            
            log.info(f"Message added to Redis. Key: {self.key}, TTL.")
        except Exception as e:
            log.error(f"Redis add_message error: {e}")
