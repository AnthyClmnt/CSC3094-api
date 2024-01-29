import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from datetime import datetime, timedelta
import os


class AuthHandler:
    def __init__(self):
        self.secret = str(os.getenv("JWT_SECRET"))

    security = HTTPBearer()
    pwd_context = CryptContext(schemes=['bcrypt'], deprecated="auto")

    def getPasswordHash(self, password):
        return self.pwd_context.hash(password)

    def verifyPassword(self, plainPassword, hashedPassword):
        return self.pwd_context.verify(plainPassword, hashedPassword)

    def encodeToken(self, userId, expiration_minutes=20):
        payload = {
            'iss': 'dissertation',
            'sub': str(userId),
            'exp': datetime.utcnow() + timedelta(minutes=expiration_minutes),
            'iat': datetime.utcnow()
        }
        return jwt.encode(
            payload,
            self.secret,
            algorithm='HS256'
        )

    def decodeToken(self, token, boolResp=False):
        try:
            payload = jwt.decode(token, self.secret, algorithms=['HS256'])
            if boolResp:
                return True
            return payload['sub']
        except jwt.ExpiredSignatureError:
            if boolResp:
                return True
            raise HTTPException(status_code=401, detail='Token has Expired')
        except jwt.InvalidTokenError:
            if boolResp:
                return False
            raise HTTPException(status_code=401, detail='Invalid Token')

    def authWrapper(self, auth: HTTPAuthorizationCredentials = Security(security)):
        return self.decodeToken(auth.credentials)
