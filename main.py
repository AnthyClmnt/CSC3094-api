# main.py
from fastapi import FastAPI
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from auth import auth_routes
from users import user_routes
from github import github_routes
import database

app = FastAPI()
load_dotenv()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You should restrict this to specific domains in a production environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Welcome to the Api"}


# Include API routes
app.include_router(auth_routes.auth_router)
app.include_router(user_routes.user_router)
app.include_router(github_routes.github_router)

# Create SQLite database connection
database.create_db()


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
