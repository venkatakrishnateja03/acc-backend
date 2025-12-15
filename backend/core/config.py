import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()
FILE_ENCRYPTION_KEY = os.getenv("FILE_ENCRYPTION_KEY")
fernet = Fernet(FILE_ENCRYPTION_KEY.encode())
_secret_key = os.getenv("SECRET_KEY")
if _secret_key is None:
    raise RuntimeError("SECRET_KEY is not set")

SECRET_KEY: str = _secret_key
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
FILES_DIR = os.path.join(BASE_DIR, "files")
os.makedirs(FILES_DIR, exist_ok=True)
db_url = os.getenv("DATABASE_URL")
algorithm = os.getenv("ALGORITHM", "HS256")
token_expire_minutes = int(os.getenv("token_expire_minutes"))
