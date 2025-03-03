import sys
from pathlib import Path

# プロジェクトルートディレクトリをPythonパスに追加
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

import bcrypt
from sqlalchemy.orm import Session

from web.server.database.database import engine, Base, get_db
from web.server.models.user import User
from web.server.models.settings import Settings

def init_db():
    print("データベースを初期化しています...")
    Base.metadata.create_all(bind=engine)
    print("データベースのテーブルが作成されました")

    # 管理者ユーザーの作成
    db = next(get_db())
    try:
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            print("管理者ユーザーを作成しています...")
            hashed_password = bcrypt.hashpw("admin".encode(), bcrypt.gensalt()).decode()
            admin_user = User(
                username="admin",
                password=hashed_password,
                is_admin=True
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)

            # 管理者ユーザーの設定を作成
            admin_settings = Settings(
                user_id=admin_user.id,
                theme="light",
                language="ja"
            )
            db.add(admin_settings)
            db.commit()
            print("管理者ユーザーが作成されました")
        else:
            print("管理者ユーザーは既に存在します")
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_db() 