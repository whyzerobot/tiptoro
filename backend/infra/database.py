"""
infra/database.py

数据库访问层工厂。
- local  → SQLite (无需安装任何服务，直接运行)
- cloud  → PostgreSQL (生产环境)

使用方法：
    from infra.database import get_engine, get_session

    with get_session() as session:
        session.add(...)
        session.commit()
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, Engine, text
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase

from .config import infra_config

# SQLAlchemy ORM Base（所有 Model 继承此类）
class Base(DeclarativeBase):
    pass


_engine: Engine | None = None
_SessionFactory: sessionmaker | None = None


def get_engine() -> Engine:
    """懒加载并缓存 SQLAlchemy Engine"""
    global _engine
    if _engine is None:
        db_cfg = infra_config.get_db_config()
        kwargs: dict = {"echo": db_cfg.echo_sql}
        if db_cfg.driver == "postgresql":
            kwargs["pool_size"] = db_cfg.pool_size
            kwargs["max_overflow"] = db_cfg.max_overflow
        elif db_cfg.driver == "sqlite":
            # SQLite 多线程支持
            kwargs["connect_args"] = {"check_same_thread": False}

        _engine = create_engine(db_cfg.url, **kwargs)
        print(f"[DB] ✅ Engine ready | driver={db_cfg.driver} | env={infra_config.active_env}")
    return _engine


def get_session_factory() -> sessionmaker:
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    return _SessionFactory


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """上下文管理器：自动 commit/rollback"""
    factory = get_session_factory()
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """建表（首次运行或 local 开发时使用）"""
    engine = get_engine()
    Base.metadata.create_all(engine)
    print(f"[DB] 📦 Tables initialized | driver={infra_config.get_db_config().driver}")


def health_check() -> bool:
    """简单心跳检测"""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"[DB] ❌ Health check failed: {e}")
        return False
