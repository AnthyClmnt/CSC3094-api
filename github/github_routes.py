from fastapi import APIRouter, HTTPException, Depends
from auth.auth_utils import AuthHandler
from models import GitHubCode, GitHubRepo, RepoCommit
from typing import List
import httpx
import os
from database import storeGitToken, getGitToken
from fastapi.responses import JSONResponse
from pydantic import HttpUrl
import json

auth_handler = AuthHandler()

github_router = APIRouter(
    prefix='/github',
    tags=['github'],
    dependencies=[Depends(auth_handler.authWrapper)]
)


def get_language_colour(language: str):
    script_dir = os.path.dirname(__file__)
    json_file_path = os.path.join(script_dir, 'language-colours.json')

    with open(json_file_path, 'r') as file:
        data = json.load(file)

        return data.get(language, None)


async def get_access_token(code: str):
    data = {
        "client_id": os.getenv('GITHUB_CLIENT_ID'),
        "client_secret": os.getenv('GITHUB_CLIENT_SECRET'),
        "code": code,
    }

    headers = {"Accept": "application/json"}

    async with httpx.AsyncClient() as client:
        response = await client.post("https://github.com/login/oauth/access_token", headers=headers, data=data)

    if response.status_code == 200:
        try:
            return response.json()['access_token']
        except Exception:
            raise HTTPException(status_code=400, detail="GitHub OAuth error")
    else:
        raise HTTPException(status_code=400, detail="GitHub OAuth error")


@github_router.post("/access-token")
async def connectGithub(code: GitHubCode, user_id=Depends(auth_handler.authWrapper)):
    access_token = await get_access_token(code.code)
    result = storeGitToken(access_token, user_id)

    if result:
        return JSONResponse(content={"message": "GitHub token stored successfully"}, status_code=200)
    else:
        raise HTTPException(status_code=400, detail="Failed to store Github access token")


@github_router.get("/repos", response_model=List[GitHubRepo])
async def getRepos(user_id=Depends(auth_handler.authWrapper)):
    token = getGitToken(user_id)
    if token:
        headers = {"Authorization": f"Bearer {token[0]}"}
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.github.com/user/repos", headers=headers)

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="GitHub API request failed")

        github_repos = response.json()
        mapped_repos = [GitHubRepo(**repo) for repo in github_repos]

        for i, repo in enumerate(mapped_repos):
            mapped_repos[i].commitsUrl = HttpUrl(str(repo.commitsUrl).replace('%7B/sha%7D', ''))

            if mapped_repos[i].language is not None:
                mapped_repos[i].languageColour = get_language_colour(mapped_repos[i].language)

        return mapped_repos
    else:
        raise HTTPException(status_code=400, detail="Github not connected")


@github_router.get("/commits", response_model=List[RepoCommit])
async def getCommits(repoOwner: str, repoName: str, user_id=Depends(auth_handler.authWrapper)):
    token = getGitToken(user_id)
    if token:
        headers = {"Authorization": f"Bearer {token[0]}"}
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/repos/{repoOwner}/{repoName}/commits",
                headers=headers
            )

            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="GitHub API request failed")

            repo_commits = response.json()
            return [RepoCommit(**commit) for commit in repo_commits]
    else:
        raise HTTPException(status_code=400, detail="Github not connected")
