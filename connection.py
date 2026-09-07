import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# Load variables from .env
load_dotenv()


DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


# PostgreSQL connection URL
DATABASE_URL = (
    f"postgresql+psycopg://"
    f"{DB_USER}:{DB_PASSWORD}@"
    f"{DB_HOST}:{DB_PORT}/{DB_NAME}"
)


# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)


# Test connection
def test_connection():

    try:

        with engine.connect() as connection:

            result = connection.execute(
                text("SELECT version();")
            )

            version = result.fetchone()[0]

            print("PostgreSQL connection successful!")
            print(version)

    except Exception as e:

        print("PostgreSQL connection failed!")
        print("Error:", e)


if __name__ == "__main__":
    test_connection()