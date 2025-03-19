import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models.user import Base, User
from passlib.context import CryptContext

# 設定モジュールからデータベース設定を読み込む
try:
    # 絶対インポートを使用
    from config import settings
    DATABASE_URL = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    engine = create_engine(DATABASE_URL)
except ImportError:
    # 直接の環境変数も確認
    DB_USER = os.getenv("POSTGRES_USER", "postgres")
    DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
    DB_HOST = os.getenv("POSTGRES_HOST", "db")
    DB_PORT = os.getenv("POSTGRES_PORT", "5432")
    DB_NAME = os.getenv("POSTGRES_DB", "shardbot")
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# パスワードハッシュ化の設定
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def init_db():
    # テーブルを作成
    Base.metadata.create_all(bind=engine)
    
    # セッションを作成
    db = SessionLocal()
    try:
        # 管理者ユーザーが存在するか確認
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            # 管理者ユーザーを作成
            hashed_password = pwd_context.hash("admin")
            admin = User(
                username="admin",
                hashed_password=hashed_password,
                email="admin@example.com",
                is_superuser=True,
                is_active=True,
                discord_id="admin"  # ダミーのdiscord_id
            )
            db.add(admin)
            db.commit()
            print("管理者ユーザーを作成しました")
        else:
            print("管理者ユーザーは既に存在します")
    except Exception as e:
        print(f"エラーが発生しました: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    init_db() 