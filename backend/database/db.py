import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Optional

# 数据库路径
DB_DIR = Path(__file__).parent
DB_PATH = DB_DIR / "zizi.db"


def init_database():
    """初始化数据库，创建表结构"""
    schema_path = DB_DIR / "schema.sql"

    if not schema_path.exists():
        print(f"Schema file not found: {schema_path}")
        return

    with get_db() as conn:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = f.read()

        # 分割SQL语句并执行
        statements = schema.split(';')
        for statement in statements:
            stmt = statement.strip()
            if stmt:
                try:
                    conn.execute(stmt)
                except sqlite3.OperationalError as e:
                    if "already exists" in str(e):
                        pass  # 表已存在，忽略
                    else:
                        raise

        conn.commit()
        print("Database initialized successfully")


@contextmanager
def get_db():
    """获取数据库连接的上下文管理器"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def execute_query(query: str, params: tuple = (), fetch_one: bool = False):
    """执行查询"""
    with get_db() as conn:
        cursor = conn.execute(query, params)
        if fetch_one:
            row = cursor.fetchone()
            return dict(row) if row else None
        else:
            rows = cursor.fetchall()
            return [dict(row) for row in rows]


def execute_update(query: str, params: tuple = ()) -> int:
    """执行更新操作，返回影响的行数"""
    with get_db() as conn:
        cursor = conn.execute(query, params)
        conn.commit()
        return cursor.rowcount


def execute_insert(query: str, params: tuple = ()) -> Optional[int]:
    """执行插入操作，返回插入的ID"""
    with get_db() as conn:
        cursor = conn.execute(query, params)
        conn.commit()
        return cursor.lastrowid
