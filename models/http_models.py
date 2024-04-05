from typing import Any
from fastapi.security.http import  HTTPBase
from fastapi.security.utils import get_authorization_scheme_param
from fastapi import  HTTPException, Request 
from sqlalchemy.orm import declarative_base 
import sqlalchemy
from jose import jwt
from jose.exceptions import JWTError
from base64 import b64decode
from db.postgre import postgresql
import json as jsonlib
import logging
import os

SECRET_KEY = os.getenv("SECRET_KEY", "SECRET_KEY")
CHECK_CODE_SALT = os.getenv("CHECK_CODE_SALT", "CHECK_CODE_SALT").encode()


class CustomOrmBase:
    def as_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}  # type: ignore


Base: type = declarative_base(cls=CustomOrmBase)


class User(Base):
    __tablename__ = "user"
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String(150))
    username = sqlalchemy.Column(sqlalchemy.String(100))
    password = sqlalchemy.Column(sqlalchemy.String(100))


class HTTPAuthorization(HTTPBase):
    async def bearer_handler(self, credentials: str):
        try:
            payload = jwt.decode(credentials, SECRET_KEY, algorithms=["HS256"])
            if "user_id" in payload:
                user = await postgresql.fetch_one(
                    query="""select * from public.user where id = :user_id""",
                    values={"user_id": payload["user_id"]},
                )
            else:
                user = None

            if user:
                return user, True
            return None, False  
        except JWTError as err:
            return None, False  
        except:
            if "payload" in locals():
                logging.exception("Author wrong:\n%s", jsonlib.dumps(payload, indent=2, ensure_ascii=False))  # type: ignore
            else:
                logging.exception("Author wrong")
            raise HTTPException(500, "inside wrong")

    SCHEMA_SET = {
        "bearer": "bearer_handler", 
    }

    def __init__(
        self,
        *,
        scheme_name: str | None = None,
        description: str | None = None,
        auto_error: bool = True
    ):
        super().__init__(
            scheme="bearer",
            scheme_name=scheme_name,
            description=description,
            auto_error=auto_error,  
        )

    async def authorize(self, request: Request) -> tuple[Any | None, bool]:
        authorization = request.headers.get("Authorization")
        scheme, token = get_authorization_scheme_param(authorization)
        if scheme and token:
            _scheme = scheme.lower()
            if _scheme in self.SCHEMA_SET:
                scheme_handler = self.SCHEMA_SET[_scheme]
                handler = (
                    getattr(self, self.SCHEMA_SET[_scheme], None)
                    if isinstance(scheme_handler, str)
                    else scheme_handler
                )
                if handler is not None:
                    if not callable(handler):
                        return None, bool(handler)
                    return await handler(token)  
        return None, False

    async def __call__(self, request: Request):
        user, passed = await self.authorize(request)
        setattr(request, "authorized", passed)
        request.scope["user"] = user

security = HTTPAuthorization()  
