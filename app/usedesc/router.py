from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.include.logging_config import logger as log
from app.include.permissions import secret_access

from .service import UsedeskAPIError, usedesk_service


router = APIRouter()


class SendUsedeskMessageRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    text: str = Field(..., min_length=1, description="Текст сообщения")
    sender: Literal["client", "agent"] = Field(
        "client",
        description="client — сообщение клиента, agent — ответ ИИ/агента",
    )
    chat_id: int | None = Field(
        None,
        gt=0,
        description="Не передавайте для создания чата; передавайте для продолжения",
    )
    client_id: int | None = Field(None, gt=0)
    name: str | None = Field(None, max_length=255)
    email: str | None = Field(None, max_length=255)

    # @model_validator(mode="after")
    # def validate_agent_message(self) -> "SendUsedeskMessageRequest":
    #     if self.sender == "agent" and self.chat_id is None:
    #         raise ValueError("chat_id обязателен для сообщения агента")
    #     return self


class SendUsedeskMessageResponse(BaseModel):
    chat_id: int
    sender: Literal["client", "agent"]
    ticket_id: int | None = None
    client_id: int | None = None
    channel_id: int | None = None
    # usedesk_response: dict[str, Any]


@router.post(
    "/message",
    response_model=SendUsedeskMessageResponse,
    dependencies=[Depends(secret_access)],
    name="Отправить сообщение в Usedesk",
)
async def send_usedesk_message(
    data: SendUsedeskMessageRequest,
) -> SendUsedeskMessageResponse:
    try:
        result = await usedesk_service.send_message(
            text=data.text,
            sender=data.sender,
            chat_id=data.chat_id,
            client_id=data.client_id,
            name=data.name,
            email=data.email,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    except UsedeskAPIError as error:
        log.error(f"Usedesk API error: {error}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error

    return SendUsedeskMessageResponse(
        chat_id=int(result["chat_id"]),
        sender=data.sender,
        ticket_id=result.get("ticket_id"),
        client_id=result.get("client_id"),
        channel_id=result.get("channel_id"),
        usedesk_response=result,
    )
