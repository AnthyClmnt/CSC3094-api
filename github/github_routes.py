from fastapi import APIRouter, HTTPException, Depends
from auth.auth_utils import AuthHandler
from models import GitHubCode, GitHubRepo, RepoCommit, CommitDetails, CommitStats, CommitFile
from typing import List, Optional
import httpx
import os
from database import storeGitToken, getGitToken, getRepoLastAnalysedTime, insert_commit_complexity, setLastAnalysedTime, getRepoAnalysis
from fastapi.responses import JSONResponse
from pydantic import HttpUrl
import json
import datetime
from analysis import calculate_cyclomatic_complexity, calculate_lines_to_comments_ratio, calculate_maintainability_index
from utils import grade_complexity, grade_comment_ratio, grade_maintainability

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

    repo_url = f"https://api.github.com/repos/{repoOwner}/{repoName}"
    async with httpx.AsyncClient() as client:
        repo_response = await client.get(repo_url, headers={"Authorization": f"Bearer {token}"})
    repo_data = repo_response.json()

    if 'message' in repo_data and repo_data['message'] == 'Not Found':
        raise HTTPException(status_code=404, detail="Repository not Found")

    last_analysed = getRepoLastAnalysedTime(repoName, repoOwner)
    analysis = getRepoAnalysis(repoOwner, repoName)

    struct_anal = []
    total_complexity_files = 0
    total_complexity = 0
    total_comment_ratio_files = 0
    total_comment_ratio = 0.0
    total_mi_files = 0
    total_mi = 0.0

    if analysis:
        for i, file in enumerate(analysis):
            file_anal = {
                "sha": file[2],
                "author": file[3],
                "fileName": file[4],
                "complexity": file[5],
                "maintain_index": file[6],
                "ltc_ratio": file[7]
            }

            if file_anal['complexity'] is not None:
                result = grade_complexity(file_anal['complexity'])

                file_anal['gradeText'] = result[0]
                file_anal['grade'] = result[1]
                file_anal['gradeClass'] = result[2]

                total_complexity += file_anal['complexity']
                total_complexity_files += 1

            if file_anal['ltc_ratio'] is not None:
                result = grade_comment_ratio(file_anal['ltc_ratio'])

                file_anal['commentGrade'] = result[0]
                file_anal['commentGradeClass'] = result[1]

                total_comment_ratio += file_anal['ltc_ratio']
                total_comment_ratio_files += 1

            if file_anal['maintain_index'] is not None:
                result = grade_maintainability(file_anal['maintain_index'])

                file_anal['maintainabilityGrade'] = result[0]
                file_anal['maintainabilityGradeClass'] = result[1]

                total_mi += file_anal['maintain_index']
                total_mi_files += 1

            struct_anal.append(file_anal)

    average_complexity = round(total_complexity / total_complexity_files, 2) if total_complexity_files != 0 else 0
    average_comment_ratio = round(total_comment_ratio / total_comment_ratio_files,
                                  2) if total_comment_ratio_files != 0 else 0
    average_mi = round(total_mi / total_mi_files, 2) if total_mi_files != 0 else 0

    average_complexity_grades = grade_complexity(average_complexity)
    average_comments_ratio_grades = grade_comment_ratio(average_comment_ratio)
    average_mi_grades = grade_maintainability(average_mi)

    return {
        "description": repo_data["description"],
        "title": repo_data["full_name"],
        "githubLink": repo_data["html_url"],
        "visibility": repo_data["private"],
        "owner_url": repo_data["owner"]["avatar_url"],
        "lastAnalysed": last_analysed,
        "analysis": struct_anal,
        "averageComplexity": average_complexity,
        "averageComplexityGrade": average_complexity_grades[1],
        "averageComplexityGradeClass": average_complexity_grades[2],
        "averageCommentRatio": average_comment_ratio,
        "averageCommentRatioGrade": average_comments_ratio_grades[0],
        "averageCommentRatioClass": average_comments_ratio_grades[1],
        "averageMaintainability": average_mi,
        "averageMaintainabilityGrade": average_mi_grades[0],
        "averageMaintainabilityClass": average_mi_grades[1]

    }


@github_router.get("/update-repo")
async def updateRepo(repoOwner: str, repoName: str, user_id=Depends(auth_handler.authWrapper)):
    last_updated = getRepoLastAnalysedTime(repoName, repoOwner)
    try:
        commits = await getCommits(repoOwner, repoName, last_updated, user_id)

        for commit in commits:
            commitChanges = await getCommitChanges(commit.sha, repoOwner, repoName, user_id)

            for file in commitChanges.files:
                cc = calculate_cyclomatic_complexity(file.patch, file.filename)
                mi = calculate_maintainability_index(file.patch, file.filename, cc)
                ltc = calculate_lines_to_comments_ratio(file.patch, file.filename)

                if cc is None and mi is None and ltc is None:
                    continue

                insert_commit_complexity(
                    repoOwner,
                    repoName,
                    commit.sha,
                    commit.commit.author.name,
                    file.filename,
                    cc,
                    mi,
                    ltc
                )

        setLastAnalysedTime(repoOwner, repoName)
        overview = await getRepoOverview(repoOwner, repoName, user_id)

        return overview, len(commits)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@github_router.get("/commits", response_model=List[RepoCommit])
async def getCommits(repoOwner: str, repoName: str, since: Optional[str] = None,
                     user_id=Depends(auth_handler.authWrapper)):
    token = getGitToken(user_id)
    if token:
        headers = {"Authorization": f"Bearer {token}"}
        params = {"per_page": 100}

        if since:
            since_datetime = datetime.datetime.strptime(since, "%Y-%m-%d %H:%M:%S.%f")
            since_isoformat = since_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
            params['since'] = since_isoformat

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/repos/{repoOwner}/{repoName}/commits",
                params=params,
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
                files=[CommitFile(**file_data) for file_data in repo_commits_details['files']]
            )

            return commitDetails
    else:
        raise HTTPException(status_code=400, detail="Github not connected")


@github_router.get("/commit/changes/file", response_model=CommitFile)
async def getCommitChangesFile(sha: str,
                               repoOwner: str,
                               repoName: str,
                               filename: str,
                               user_id=Depends(auth_handler.authWrapper)):
    shaChanges = await getCommitChanges(sha, repoOwner, repoName, user_id)
    commit_files = shaChanges.files
    filtered_files = [file for file in commit_files if file.filename == filename]
    return filtered_files[0]


@github_router.get("/issues")
async def GetIssues(repoOwner: str, repoName: str):
    analysis = getRepoAnalysis(repoOwner, repoName)

    struct_anal = []

    if analysis:
        for i, file in enumerate(analysis):
            file_anal = {
                "sha": file[2],
                "author": file[3],
                "fileName": file[4],
                "complexity": file[5],
                "maintain_index": file[6],
                "ltc_ratio": file[7],
            }

            if file_anal['complexity'] is not None:
                result = grade_complexity(file_anal['complexity'])

                file_anal['gradeText'] = result[0]
                file_anal['grade'] = result[1]
                file_anal['gradeClass'] = result[2]

            if file_anal['ltc_ratio'] is not None:
                result = grade_comment_ratio(file_anal['ltc_ratio'])

                file_anal['commentGrade'] = result[0]
                file_anal['commentGradeClass'] = result[1]

            if file_anal['maintain_index'] is not None:
                result = grade_maintainability(file_anal['maintain_index'])

                file_anal['maintainabilityGrade'] = result[0]
                file_anal['maintainabilityGradeClass'] = result[1]

            struct_anal.append(file_anal)

        return struct_anal


@github_router.patch("commit/analysis/remove-issue")
async def RemoveFileIssue():
    return True
