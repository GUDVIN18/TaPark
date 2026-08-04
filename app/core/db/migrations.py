from yoyo import step

def apply_step(conn):
    cursor = conn.cursor()
    cursor.execute(
        # query to perform the migration
    )

def rollback_step(conn):
    cursor = conn.cursor()
    cursor.execute(
        # query to undo the above
    )