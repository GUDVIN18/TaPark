"""
create user_profile table
"""

from yoyo import step

__depends__ = {}

steps = [
    step(
        """
            CREATE TABLE IF NOT EXISTS user_profile (
                id SERIAL PRIMARY KEY,
                uuid UUID NOT NULL,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
                updated_at TIMESTAMP NULL
            );
        """
    )
]
