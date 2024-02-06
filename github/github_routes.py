from fastapi import APIRouter, HTTPException, Depends
from auth.auth_utils import AuthHandler
from models import GitHubCode, GitHubRepo, RepoCommit, CommitDetails, CommitStats, CommitFiles
from typing import List
import httpx
import os
from database import storeGitToken, getGitToken
from fastapi.responses import JSONResponse
from pydantic import HttpUrl
import json
import datetime

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
        headers = {"Authorization": f"Bearer {token}"}
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


@github_router.get("/repo-overview")
async def getRepoOverview(repoOwner: str, repoName: str, user_id=Depends(auth_handler.authWrapper)):
    token = getGitToken(user_id)

    # Fetch repository information from GitHub API
    repo_url = f"https://api.github.com/repos/{repoOwner}/{repoName}"
    async with httpx.AsyncClient() as client:
        repo_response = await client.get(repo_url, headers={"Authorization": f"Bearer {token}"})
    repo_data = repo_response.json()

    # Extract relevant repository information
    repo_info = {
        "name": repo_data["name"],
        "description": repo_data["description"],
        "owner": repoOwner,
        # Add other relevant fields
    }

    # Fetch contributors from GitHub API
    contributors_url = f"https://api.github.com/repos/{repoOwner}/{repoName}/contributors"
    async with httpx.AsyncClient() as client:
        contributors_response = await client.get(contributors_url, headers={"Authorization": f"Bearer {token}"})
    contributors_data = contributors_response.json()

    # Fetch all commits for the repository
    commits_url = f"https://api.github.com/repos/{repoOwner}/{repoName}/commits"
    async with httpx.AsyncClient() as client:
        commits_response = await client.get(commits_url, headers={"Authorization": f"Bearer {token}"})
    commits_data = commits_response.json()

    # Create a dictionary to store the commit count for each contributor
    commit_counts = {contributor["login"]: 0 for contributor in contributors_data}

    for commit in commits_data:
        author_login = commit["author"]["login"] if commit["author"] else None
        print(author_login)
        if author_login in commit_counts:
            commit_counts[author_login] += 1

    # Extract contributor information (name and profile image)
    contributors_info = [
        {
            "name": contributor["login"],
            "avatar_url": contributor["avatar_url"],
            "commit_count": commit_counts.get(contributor["login"], 0)
        }
        for contributor in contributors_data
    ]

    # Fetch language distribution from GitHub API
    languages_url = f"https://api.github.com/repos/{repoOwner}/{repoName}/languages"
    async with httpx.AsyncClient() as client:
        languages_response = await client.get(languages_url, headers={"Authorization": f"Bearer {token}"})
    languages_data = languages_response.json()

    # Organize language data for the donut chart
    language_labels = list(languages_data.keys())
    language_values = list(languages_data.values())
    language_percentages = [(value / sum(languages_data.values())) * 100 for value in language_values]
    language_colours = [get_language_colour(language) for language in language_labels]

    # Round each value to two decimal places
    rounded_values = [round(value, 2) for value in language_percentages]

    # Calculate the adjustment needed to make the sum exactly 100
    adjustment = 100 - sum(rounded_values)

    if language_percentages:
        # Use a more sophisticated rounding for the last value
        rounded_values[-1] = round(language_percentages[-1] + adjustment, 2)

    # Fetch the last 5 commits within the last week
    since_date = (datetime.datetime.now() - datetime.timedelta(days=30)).isoformat()
    commits_url = f"https://api.github.com/repos/{repoOwner}/{repoName}/commits"
    params = {"since": since_date, "per_page": 5}
    async with httpx.AsyncClient() as client:
        commits_response = await client.get(commits_url, params=params,
                                            headers={"Authorization": f"Bearer {token}"})
    commits_data = commits_response.json()

    # Extract relevant commit information
    last_commits = [
        {
            "sha": commit["sha"],
            "message": commit["commit"]["message"],
            "author": commit["commit"]["author"]["name"],
            "timestamp": commit["commit"]["author"]["date"]
        }
        for commit in commits_data
    ]

    return {
        "repo_info": repo_info,
        "contributors": contributors_info,
        "language_distribution": {
            "total": rounded_values,
            "labels": language_labels,
            "values": language_values,
            "colours": language_colours
        },
        "last_commits": last_commits
    }


@github_router.get("/commits", response_model=List[RepoCommit])
async def getCommits(repoOwner: str, repoName: str, user_id=Depends(auth_handler.authWrapper)):
    token = getGitToken(user_id)
    if token:
        headers = {"Authorization": f"Bearer {token}"}
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


@github_router.get("/commit/changes", response_model=CommitDetails)
async def getCommitChanges(sha: str, repoOwner: str, repoName: str, user_id=Depends(auth_handler.authWrapper)):
    token = getGitToken(user_id)
    if token:
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/repos/{repoOwner}/{repoName}/commits/{sha}",
                headers=headers
            )
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="GitHub API request failed")

            repo_commits_details = response.json()
            commitDetails = CommitDetails(
                sha=repo_commits_details['sha'],
                commit=repo_commits_details['commit'],
                stats=CommitStats(**repo_commits_details['stats']),
                files=[CommitFiles(**file_data) for file_data in repo_commits_details['files']]
            )

            return commitDetails
    else:
        raise HTTPException(status_code=400, detail="Github not connected")
