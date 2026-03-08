from collections.abc import Generator # 型ヒント、インスタンスのチェックとしての役割がある。

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker