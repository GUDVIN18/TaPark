from pydantic import BaseModel, Field
from enum import Enum


class ButtonType(str, Enum):
    ADD_HABIT = "add_habit"
    # SUGGEST_RITUAL = "suggest_ritual"

class Button(BaseModel):
    type: ButtonType = Field(
        description=(
            "Тип кнопки: "
            # f"'{ButtonType.ADD_TO_DIARY.value}' — добавить конкретный совет/ритуал из ответа в дневник; "
            f"'{ButtonType.ADD_HABIT.value}' — предложить пользователю ритуал/совет для отслеживания и добавления в дневник."
        )
    )
    title: str = Field(
        description=(
            "название кнопки. "
            # "Для 'add_to_diary': 'Добавить [название совета] в дневник'. "
            f"Для '{ButtonType.ADD_HABIT.value}': краткое название ритуала, например 'Плотные шторы', 'Проветрить', 'Выключить свет' и т.д."
        )
    )
    text: str = Field(
        description=(
            "Текст привычки для добавления в дневник. Без формулировок типа 'Добавить [название] в дневник', только название"
        )
    )