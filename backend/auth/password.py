"""
auth/password.py

密码哈希工具（bcrypt）。
依赖：pip install bcrypt
"""
import bcrypt


def hash_password(plain: str) -> str:
    """将明文密码哈希后返回字符串（可直接存数据库）"""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """校验明文密码与哈希值是否匹配"""
    return bcrypt.checkpw(plain.encode(), hashed.encode())
