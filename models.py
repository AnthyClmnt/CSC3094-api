# models.py
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional


class UserRegistration(BaseModel):
    email: str
    password: str
    forename: str


class UserLogin(BaseModel):
    email: str
    password: str


class User(BaseModel):
    id: int
    email: str
    forename: str
    githubConnected: bool


class GitHubCode(BaseModel):
    code: str


class Token(BaseModel):
    authToken: str


class RepoOwner(BaseModel):
    avatarUrl: HttpUrl = Field(validation_alias="avatar_url")
    name: str = Field(validation_alias="login")


class GitHubRepo(BaseModel):
    repoName: str = Field(validation_alias="name")
    owner: RepoOwner
    commitsUrl: HttpUrl = Field(validation_alias="commits_url")
    visibility: str
    description: Optional[str] = None
    updatedAt: str = Field(validation_alias="updated_at")
    language: Optional[str] = None
    languageColour: Optional[str] = None


class CommitAuthor(BaseModel):
    name: str
    date: str


class Commit(BaseModel):
    author: CommitAuthor
    message: str


class RepoCommit(BaseModel):
    sha: str
    commit: Commit


class CommitParams(BaseModel):
    repoOwner: str
    repoName: str

