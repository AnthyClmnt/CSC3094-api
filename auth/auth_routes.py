# auth_routes.py
from fastapi import APIRouter, HTTPException
import database
from models import UserRegistration, Token, UserLogin
from .auth_utils import AuthHandler

auth_router = APIRouter(
    prefix='/auth',
    tags=['authorisation']
)
auth_handler = AuthHandler()


@auth_router.post("/register", response_model=Token)
async def register(user_details: UserRegistration):
    user_details.password = auth_handler.getPasswordHash(user_details.password)
    user_id = database.register(user_details)

    token = auth_handler.encodeToken(user_id)
    return Token(authToken=token)


@auth_router.post("/login", response_model=Token)
async def login(user_details: UserLogin):
    user = database.login(user_details)

    if user is None:
        raise HTTPException(status_code=401, detail='Invalid Email/Password')
    if not auth_handler.verifyPassword(user_details.password, user[2]):
        raise HTTPException(status_code=401, detail='Invalid Email/Password')

    token = auth_handler.encodeToken(user[0])
    return Token(authToken=token)


@auth_router.post("/validate-token", response_model=bool)
async def validateToken(token: Token):
    return auth_handler.decodeToken(token.authToken, True)
