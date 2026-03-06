"""
认证模块 - JWT Token 和用户认证
"""
import os
import bcrypt
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Header
from pydantic import BaseModel

# JWT配置
JWT_SECRET = os.getenv("JWT_SECRET", "zizi-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7  # Token有效期7天


class TokenData(BaseModel):
    """Token数据模型"""
    user_id: int
    phone: str
    exp: Optional[datetime] = None


class UserRegister(BaseModel):
    """用户注册模型"""
    phone: str
    password: str
    nickname: Optional[str] = None


class UserLogin(BaseModel):
    """用户登录模型"""
    phone: str
    password: str


class UserResponse(BaseModel):
    """用户响应模型"""
    id: int
    phone: str
    nickname: Optional[str]
    created_at: str
    last_login_at: Optional[str]


class User(BaseModel):
    """当前用户模型（用于FastAPI依赖注入）"""
    id: int
    phone: str
    nickname: Optional[str] = None


def hash_password(password: str) -> str:
    """使用bcrypt哈希密码"""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def create_access_token(user_id: int, phone: str) -> str:
    """创建JWT访问令牌"""
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {
        "user_id": user_id,
        "phone": phone,
        "exp": expire,
        "type": "access"
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """解码JWT令牌"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# 别名函数，用于兼容main.py的导入
verify_token = decode_token
get_password_hash = hash_password


def get_current_user(authorization: Optional[str] = Header(None)) -> Optional[Dict[str, Any]]:
    """
    从请求头中获取当前用户
    用法：在FastAPI路由中使用依赖注入

    async def some_endpoint(current_user: dict = Depends(get_current_user)):
        if not current_user:
            raise HTTPException(status_code=401, detail="未登录")
        ...
    """
    if not authorization:
        return None

    # 支持 "Bearer token" 格式
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    token = parts[1]
    payload = decode_token(token)
    return payload


def require_auth(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """要求必须登录，未登录抛出401错误"""
    user = get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")
    return user


# ==================== 用户业务逻辑 ====================

from database.db import execute_query, execute_insert


class TokenResponse(BaseModel):
    """Token响应模型"""
    access_token: str
    refresh_token: str
    token_type: str
    user: UserResponse


def register_user(phone: str, password: str, nickname: Optional[str] = None) -> dict:
    """
    注册新用户

    Args:
        phone: 手机号
        password: 密码
        nickname: 昵称（可选）

    Returns:
        包含token和用户信息的成功响应，或错误信息
    """
    # 检查手机号是否已存在
    existing = execute_query(
        "SELECT id FROM users WHERE phone = ?",
        (phone,),
        fetch_one=True
    )

    if existing:
        return {"error": "该手机号已注册"}

    # 哈希密码
    password_hash = hash_password(password)

    # 创建用户
    user_id = execute_insert(
        """INSERT INTO users (phone, password_hash, nickname, created_at, updated_at)
           VALUES (?, ?, ?, datetime('now'), datetime('now'))""",
        (phone, password_hash, nickname)
    )

    if not user_id:
        return {"error": "创建用户失败"}

    # 创建用户设置记录
    execute_insert(
        "INSERT INTO user_settings (user_id, preferred_voice, current_library) VALUES (?, 'serena', 'infant')",
        (user_id,)
    )

    # 创建访问令牌
    access_token = create_access_token(user_id, phone)
    refresh_token = create_refresh_token(user_id, phone)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "phone": phone,
            "nickname": nickname,
            "created_at": datetime.now().isoformat(),
            "last_login_at": None
        }
    }


def login_user(phone: str, password: str) -> dict:
    """
    用户登录

    Args:
        phone: 手机号
        password: 密码

    Returns:
        包含token和用户信息的成功响应，或错误信息
    """
    # 查找用户
    user = execute_query(
        "SELECT id, phone, password_hash, nickname, created_at, last_login_at FROM users WHERE phone = ?",
        (phone,),
        fetch_one=True
    )

    if not user:
        return {"error": "手机号或密码错误"}

    # 验证密码
    if not verify_password(password, user["password_hash"]):
        return {"error": "手机号或密码错误"}

    # 更新最后登录时间
    execute_query(
        "UPDATE users SET last_login_at = datetime('now') WHERE id = ?",
        (user["id"],)
    )

    # 创建访问令牌
    access_token = create_access_token(user["id"], user["phone"])
    refresh_token = create_refresh_token(user["id"], user["phone"])

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "phone": user["phone"],
            "nickname": user["nickname"],
            "created_at": user["created_at"],
            "last_login_at": user["last_login_at"]
        }
    }


def create_refresh_token(user_id: int, phone: str) -> str:
    """创建JWT刷新令牌（有效期30天）"""
    expire = datetime.utcnow() + timedelta(days=30)
    payload = {
        "user_id": user_id,
        "phone": phone,
        "exp": expire,
        "type": "refresh"
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def refresh_access_token(refresh_token: str) -> dict:
    """
    使用刷新令牌获取新的访问令牌

    Args:
        refresh_token: 刷新令牌

    Returns:
        包含新token的响应，或错误信息
    """
    try:
        payload = jwt.decode(refresh_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        # 检查token类型
        if payload.get("type") != "refresh":
            return {"error": "无效的刷新令牌"}

        user_id = payload.get("user_id")
        phone = payload.get("phone")

        # 验证用户是否存在
        user = execute_query(
            "SELECT id, phone, nickname, created_at, last_login_at FROM users WHERE id = ?",
            (user_id,),
            fetch_one=True
        )

        if not user:
            return {"error": "用户不存在"}

        # 创建新的访问令牌
        new_access_token = create_access_token(user_id, phone)
        new_refresh_token = create_refresh_token(user_id, phone)

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "phone": user["phone"],
                "nickname": user["nickname"],
                "created_at": user["created_at"],
                "last_login_at": user["last_login_at"]
            }
        }

    except jwt.ExpiredSignatureError:
        return {"error": "刷新令牌已过期，请重新登录"}
    except jwt.InvalidTokenError:
        return {"error": "无效的刷新令牌"}
