"""

"""

from yoyo import step

__depends__ = {'20260804_02_VFQvl'}

steps = [
    step(
        """
            ALTER TABLE chat_history
            ALTER COLUMN user_id TYPE BIGINT;

            ALTER TABLE user_profile
            ALTER COLUMN user_id TYPE BIGINT;
        """
    )
]
