from fastapi.testclient import TestClient
from unittest.mock import patch
from main import app
from models import User
from auth.auth_utils import AuthHandler
import os

client = TestClient(app)
auth_handler = AuthHandler()

fake_jwt_token = "fakeToken"
user_id = 1
mock_user_data_internal = (user_id, 'test@test.com', auth_handler.getPasswordHash("password"), True)
mock_user_data_external = (user_id, 'test@test.com', 'test', True)
auth_handler.secret = fake_jwt_token


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the Api"}


@patch('database.getUser')
def test_user_info(mock_get_user):
    with patch.dict(os.environ, {"JWT_SECRET": fake_jwt_token}):
        mock_get_user.return_value = mock_user_data_external
        token = str(auth_handler.encodeToken(user_id))

        response = client.get('/user/me', headers={'Authorization': f'Bearer {token}'})

        assert response.status_code == 200
        expected_user = User(id=user_id, email='test@test.com', forename='test', githubConnected=True)
        assert response.json() == expected_user.model_dump()


@patch('database.register')
def test_register_successful(mock_register):
    with patch.dict(os.environ, {"JWT_SECRET": fake_jwt_token}):
        mock_register.return_value = 1

        user_details = {
            "email": "test@example.com",
            "password": "password",
            "forename": "Test"
        }

        response = client.post("/auth/register", json=user_details)

        assert response.status_code == 200
        assert auth_handler.decodeToken(response.json()['accessToken']) == '1'


@patch('database.login')
def test_login_successful(mock_login):
    with patch.dict(os.environ, {"JWT_SECRET": fake_jwt_token}):
        mock_login.return_value = mock_user_data_internal

        user_details = {
            "email": "test@example.com",
            "password": "password",
        }

        response = client.post("/auth/login", json=user_details)

        assert response.status_code == 200
        assert auth_handler.decodeToken(response.json()['accessToken']) == '1'


@patch('database.login')
def test_login_unsuccessful(mock_login):
    with patch.dict(os.environ, {"JWT_SECRET": fake_jwt_token}):
        mock_login.return_value = None

        user_details = {
            "email": "invalid@example.com",
            "password": "invalid",
        }

        response = client.post("/auth/login", json=user_details)

        assert response.status_code == 401
