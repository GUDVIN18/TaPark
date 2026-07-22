from typing import Any, Literal

import httpx

from app.include.config import config


Sender = Literal["client", "agent"]


class UsedeskAPIError(RuntimeError):
    """Raised when Usedesk rejects a request or cannot be reached."""


class UsedeskService:
    def __init__(
        self,
        *,
        base_url: str = config.USEDESK_BASE_URL,
        api_token: str = config.USEDESK_API_TOKEN,
        company_id: int = config.USEDESK_COMPANY_ID,
        channel_id: int = config.USEDESK_CHANNEL_ID,
        agent_id: int = config.USEDESK_AGENT_ID,
        timeout_seconds: float = config.USEDESK_TIMEOUT_SECONDS,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_token = api_token
        self._company_id = company_id
        self._channel_id = channel_id
        self._agent_id = agent_id
        self._timeout = httpx.Timeout(timeout_seconds)

    async def send_message(
        self,
        *,
        text: str,
        sender: Sender = "client",
        chat_id: int | None = None,
        client_id: int | None = None,
        name: str | None = None,
        email: str | None = None,
    ) -> dict[str, Any]:
        """Create/continue a client chat or send an agent reply."""
        normalized_text = text.strip()
        if not normalized_text:
            raise ValueError("Message text must not be empty")

        if sender == "client":
            return await self._send_client_message(
                text=normalized_text,
                chat_id=chat_id,
                client_id=client_id,
                name=name,
                email=email,
            )

        if sender == "agent":
            if chat_id is None:
                raise ValueError("chat_id is required for an agent message")
            return await self._send_agent_message(
                text=normalized_text,
                chat_id=chat_id,
            )

        raise ValueError(f"Unsupported sender: {sender}")

    async def _send_client_message(
        self,
        *,
        text: str,
        chat_id: int | None,
        client_id: int | None,
        name: str | None,
        email: str | None,
    ) -> dict[str, Any]:
        message_from: dict[str, Any] = {}
        if client_id is not None:
            message_from["client_id"] = client_id
        if name:
            message_from["name"] = name
        if email:
            message_from["email"] = email

        payload: dict[str, Any] = {
            "api_token": self._api_token,
            "company_id": self._company_id,
            "channel_id": self._channel_id,
            "message": {
                "text": text,
                "from": message_from,
            },
        }
        if chat_id is not None:
            payload["chat_id"] = chat_id

        response = await self._post(
            path="/chat/addMessage",
            json=payload,
        )
        if "chat_id" not in response:
            raise UsedeskAPIError(
                f"Usedesk did not return chat_id: {response}"
            )
        return response

    async def _send_agent_message(
        self,
        *,
        text: str,
        chat_id: int,
    ) -> dict[str, Any]:
        payload = {
            "api_token": self._api_token,
            "chat_id": chat_id,
            "user_id": self._agent_id,
            "text": text,
        }
        response = await self._post(
            path="/chat/sendMessage",
            data=payload,
        )
        print(response)
        response.setdefault("chat_id", chat_id)
        return response

    async def _post(
        self,
        *,
        path: str,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                http_response = await client.post(url, json=json, data=data)
        except httpx.HTTPError as error:
            raise UsedeskAPIError(
                f"Could not call Usedesk API at {url}: {error}"
            ) from error

        try:
            response: Any = http_response.json()
        except ValueError as error:
            body_preview = http_response.text[:500]
            raise UsedeskAPIError(
                "Usedesk returned a non-JSON response "
                f"with status {http_response.status_code}: {body_preview}"
            ) from error

        if http_response.is_error:
            raise UsedeskAPIError(
                f"Usedesk returned HTTP {http_response.status_code}: {response}"
            )
        if not isinstance(response, dict):
            raise UsedeskAPIError(
                f"Usedesk returned an unexpected response: {response}"
            )
        if response.get("status") is False or response.get("status") == "error":
            raise UsedeskAPIError(f"Usedesk rejected the request: {response}")

        return response


usedesk_service = UsedeskService()
