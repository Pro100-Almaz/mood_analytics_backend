import os
import psycopg2

DB_CONFIG = {
    "user": os.environ.get("PG_USER"),
    "password": os.environ.get("PG_PASSWORD"),
    "database": os.environ.get("PG_DB"),
    "host": os.environ.get("PG_HOST"),
    "port": os.environ.get("PG_PORT")
}

def create_db():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    cursor.execute("""
                CREATE TABLE IF NOT EXISTS egov_dialog (
                    id SERIAL PRIMARY KEY,
                    task_id VARCHAR(36),
                    data jsonb,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)

    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS egov_opendata (
                        id SERIAL PRIMARY KEY,
                        task_id VARCHAR(36),
                        data jsonb,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                """)

    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS egov_nla (
                        id SERIAL PRIMARY KEY,
                        task_id VARCHAR(36),
                        data jsonb,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                """)

    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS egov_budget (
                        id SERIAL PRIMARY KEY,
                        task_id VARCHAR(36),
                        data jsonb,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        )
                    """)

    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS adilet (
                        id SERIAL PRIMARY KEY,
                        task_id VARCHAR(36),
                        data jsonb,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        )
                    """)

    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS web (
                            id SERIAL PRIMARY KEY,
                            task_id VARCHAR(36),
                            data jsonb,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        )
                    """)

    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS facebook (
                            id SERIAL PRIMARY KEY,
                            task_id VARCHAR(36),
                            data jsonb,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        )
                    """)

    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS instagram (
                            id SERIAL PRIMARY KEY,
                            task_id VARCHAR(36),
                            data jsonb,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
    cursor.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id SERIAL PRIMARY KEY,
                    log_level VARCHAR(10) NOT NULL,
                    message TEXT,
                    step VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    conn.commit()
    cursor.close()
    conn.close()
