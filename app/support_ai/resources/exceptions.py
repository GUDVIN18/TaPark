from typing import Any, Type, Optional
from fastapi import HTTPException
from pydantic import BaseModel, Field
from fastapi import status
from app.include.exceptions import AppHTTPException


class SupportAiErrorGeneration(AppHTTPException):
    http_code = status.HTTP_504_GATEWAY_TIMEOUT
    user_message = "Error Generation from SupportAi"


class SupportAiErrorFormat(AppHTTPException):
    http_code = status.HTTP_404_NOT_FOUND
    user_message = "Error format JSON from SupportAi"


class SupportAiErrorConnect(AppHTTPException):
    http_code = status.HTTP_502_BAD_GATEWAY
    user_message = "Error connect to SupportAi"

class SupportAiContentBlocked(AppHTTPException):
    http_code = status.HTTP_504_GATEWAY_TIMEOUT
    user_message = "Content is blocked by SupportAi"