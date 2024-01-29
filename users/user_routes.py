from fastapi import APIRouter, Depends
import database
from models import User
from auth.auth_utils import AuthHandler

auth_handler = AuthHandler()

user_router = APIRouter(
    prefix='/user',
    tags=['user'],
    dependencies=[Depends(auth_handler.authWrapper)]
)


@user_router.get('/me', response_model=User)
async def userInfo(user_id=Depends(auth_handler.authWrapper)):
    user = database.getUser(user_id)
    return User(id=user[0], email=user[1], forename=user[2], githubConnected=bool(user[3]))
