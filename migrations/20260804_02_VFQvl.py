"""

"""

from yoyo import step

__depends__ = {'20260804_01_6ynmr-create-user-profile-table'}

steps = [
    step(
        """
            CREATE TABLE IF NOT EXISTS chat_history (
                id SERIAL PRIMARY KEY,
                uuid UUID NOT NULL,
                user_id INTEGER NULL,
                role VARCHAR NULL,
                content VARCHAR NULL,
                reactions BOOLEAN NULL,
                created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
                updated_at TIMESTAMP NULL
            );
        """
    )
]
