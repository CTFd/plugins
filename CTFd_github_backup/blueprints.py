from CTFd.models import Challenges
from CTFd.utils.decorators import admins_only
from CTFd.utils.user import get_current_user

from CTFd.plugins.github_backup.models import db, GithubRepositories, GithubChallengeSync, GithubFlagSync, GithubHintSync, UserGitHubToken
from CTFd.plugins.github_backup.expot_data import is_imported_from_github, prepare_json
from CTFd.plugins.github_backup.import_data import import_challenges_from_repo
from CTFd.plugins.github_backup.config import config

from flask import Blueprint, render_template, request, Response, send_file, redirect
from datetime import datetime
import requests
import io
import zipfile
import time
import jwt
import json
import pytz

my_bp = Blueprint(
    "github_backup",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/plugins/github_backup/static",
    url_prefix=""
)

@my_bp.route("/admin/plugins/github_backup")
@admins_only
def get_template():
    """
    Render the GitHub Backup Plugin template for admins.
    """
    installation_url = config["GITHUB_APP_INSTALLATION_URL"]
    return render_template("admin/plugins/github_backup.html", installation_url=installation_url)


def generate_jwt():
    """
    Generates a JWT for the GitHub App.
    """
    app_id = config["GITHUB_APP_ID"]
    private_key = config["GITHUB_APP_PRIVATE_KEY"]

    payload = {
        "iat": int(time.time()),
        "exp": int(time.time()) + 600,
        "iss": app_id
    }

    return jwt.encode(payload, private_key, algorithm="RS256")


def get_installation_access_token(installation_id):
    """
    Retrieves an installation access token for a specified GitHub App installation.
    """
    jwt_token = generate_jwt()

    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json"
    }

    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    r = requests.post(url, headers=headers)

    if r.status_code != 201:
        print("Error:", r.status_code, r.text)
        return None

    return r.json().get("token")


@my_bp.route("/plugins/github_backup/installations", methods=["GET"])
@admins_only
def link_installation():
    """
    Handles the linking of a GitHub app installation to a user by retrieving
    the installation's ID from the GitHub API and storing it in the database associated
    with the currently logged-in user. It ensures that valid authentication is used
    for communication with the GitHub API using a JWT token.
    """
    jwt_token = generate_jwt()

    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json"
    }

    r = requests.get("https://api.github.com/app/installations", headers=headers)

    if r.status_code != 200:
        return {"success": False, "message": "Error retrieving installations"}, 400

    installations = r.json()
    if not isinstance(installations, list):
        return {"success": False, "message": "Unexpected response"}, 400

    if len(installations) == 1:
        installation_id = installations[0]["id"]
    else:
        return {"success": False, "message": "Multiple installations.", "r": r.json()}, 400

    user_id = get_current_user().id
    token_entry = UserGitHubToken.query.filter_by(user_id=user_id).first()

    if token_entry:
        token_entry.token = installation_id
    else:
        token_entry = UserGitHubToken(user_id=user_id, token=installation_id)
        db.session.add(token_entry)

    db.session.commit()

    return {"success": True, "message": f"Installation ID saved correctly."}


@my_bp.route("/plugins/github_backup/repos", methods=["GET"])
@admins_only
def get_repos():
    """
    Retrieves all repositories associated with the
    installation. Returns the repository details, including their IDs, names, and full names.
    """
    user_id = get_current_user().id
    token_entry = UserGitHubToken.query.filter_by(user_id=user_id).first()

    if not token_entry:
        return {"success": False, "message": "Installation ID not found"}, 401

    installation_id = get_installation_access_token(token_entry.token)

    if not installation_id:
        return {"success": False, "message": "Could not obtain installation ID"}, 400

    headers = {
        "Authorization": f"token {installation_id}",
        "Accept": "application/vnd.github+json"
    }

    github_api_url = "https://api.github.com/installation/repositories"
    all_repos = []
    page = 1

    while True:
        response = requests.get(
            f"{github_api_url}?per_page=100&page={page}",
            headers=headers
        )

        if response.status_code != 200:
            return {
                "success": False,
                "message": "Could not retrieve repositories",
                "details": response.json()
            }, 400

        repos_page = response.json().get("repositories", [])
        all_repos.extend(repos_page)

        if "next" not in response.links:
            break

        page += 1

    repo_names = [
        {"id": r["id"], "name": r["name"], "full_name": r["full_name"]}
        for r in all_repos
    ]

    return {"success": True, "repos": repo_names}


@my_bp.route("/plugins/github_backup/repos/selection", methods=["POST"])
@admins_only
def save_selected_repos():
    """
    Processes a POST request containing a list of repositories and
    saves them if they are not already stored for the user in the database. Each
    repository is stored with its associated details if it does not already
    exist. All changes are committed to the database after processing.
    """
    data = request.get_json()
    selected_repos = data.get("repos", [])
    user = get_current_user()

    if not isinstance(selected_repos, list):
        return {"success": False, "message": "Invalid data format"}, 400

    for repo in selected_repos:
        existing = GithubRepositories.query.filter_by(
            user_id=user.id,
            github_repo_id=repo["id"]
        ).first()

        if not existing:
            new_repo = GithubRepositories(
                user_id=user.id,
                github_repo_id=repo["id"],
                name=repo["name"],
                full_name=repo["full_name"],
                selected=False,
                last_synced_at=None
            )
            db.session.add(new_repo)

    db.session.commit()

    return {"success": True, "message": "Repositories saved correctly"}


@my_bp.route("/plugins/github_backup/repos/saved", methods=["GET"])
@admins_only
def list_saved_repos():
    """
    This function retrieves all GitHub repositories that are saved by the currently
    authenticated user.
    """
    user_id = get_current_user().id
    saved_repos = GithubRepositories.query.filter_by(user_id=user_id).all()

    result = []
    for repo in saved_repos:
        result.append({
            "id": repo.id,
            "name": repo.name,
            "full_name": repo.full_name,
            "selected": repo.selected,
            "last_synced_at": repo.last_synced_at.isoformat() if repo.last_synced_at else None,
        })

    return {"success": True, "repos": result}


@my_bp.route("/plugins/github_backup/repos/<int:repo_id>", methods=["DELETE"])
@admins_only
def delete_repo(repo_id):
    """
    Deletes a GitHub repository along with its related data stored in the database.
    """
    user_id = get_current_user().id
    repo = GithubRepositories.query.filter_by(id=repo_id, user_id=user_id).first()

    if not repo:
        return {"success": False, "message": "Repository not found"}, 404

    # Get and delete challenge syncs
    challenge_syncs = GithubChallengeSync.query.filter_by(github_repo_id=repo.id).all()
    for sync in challenge_syncs:
        db.session.delete(sync)

    # Get and delete flag syncs
    flag_syncs = GithubFlagSync.query.filter_by(github_repo_id=repo.id).all()
    for sync in flag_syncs:
        db.session.delete(sync)

    # Delete hint syncs
    hint_syncs = GithubHintSync.query.filter_by(github_repo_id=repo.id).all()
    for sync in hint_syncs:
        db.session.delete(sync)

    db.session.delete(repo)
    db.session.commit()

    return {"success": True, "message": "Repository and related data deleted correctly."}


@my_bp.route("/plugins/github_backup/repos/<int:repo_id>/import", methods=["POST"])
@admins_only
def import_from_repo(repo_id):
    """
    Handles importing challenges from a specified GitHub repository using a user's GitHub token.
    The function imports challenges, optionally deletes existing challenges based on the delete mode,
    and updates the repository synchronization time.
    """
    data = request.get_json()
    delete_mode = data.get("delete_mode")

    try:
        user_id = get_current_user().id
        repo = GithubRepositories.query.filter_by(id=repo_id, user_id=user_id).first()
        if not repo:
            return {"success": False, "message": "Repository not found"}, 404

        # Get token
        token_entry = UserGitHubToken.query.filter_by(user_id=user_id).first()
        if not token_entry:
            return {"success": False, "message": "No GitHub token configured"}, 400
        access_token = get_installation_access_token(token_entry.token)

        result = import_challenges_from_repo(repo, access_token, overwrite_existing=True, delete_mode=delete_mode)

        repo.selected = True
        repo.last_synced_at = datetime.now().astimezone(pytz.utc)
        db.session.commit()

        return {
            "success": result["success"],
            "message": f"{result['created']} challenges imported, {result['updated']} challenges updated, {result['skipped']} already existing, {result['removed']} deleted",
            "errors": result["errors"]
        }
    except Exception as e:
        return {"success": False, "message": e}, 500


@my_bp.route("/plugins/github_backup/challenge/<int:challenge_id>/download", methods=["GET"])
@admins_only
def download_challenge(challenge_id: int) -> tuple[dict[str, bool | str], int] | Response:
    """
    Handles the downloading of a specific challenge data in JSON format. The endpoint generates
    a JSON file for the provided challenge ID and sends it as a downloadable attachment. The
    JSON content is obtained from a helper function and formatted with UTF-8 encoding.
    """

    try:
        data, name = prepare_json(challenge_id)

        json_bytes = json.dumps(data, indent=4, ensure_ascii=False).encode("utf-8-sig")

        return Response(
            json_bytes,
            mimetype="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="challenge_{name}.json"'
            },
        )
    except ValueError as e:
        return {"success": False, "message": str(e)}, 400
    except Exception as e:
        return {"success": False, "message": f"Unexpected error: {str(e)}"}, 500


@my_bp.route("/plugins/github_backup/challenges/download/example", methods=["GET"])
@admins_only
def download_example_json():
    """
    Handles the download of an example JSON file for a challenge configuration.
    """
    example = {
        "challenge": {
            "uuid": "000000000000000",
            "name": "knock, knock, Neo",
            "description": "Wake up. The matrix has you...",
            "attribution": "author",
            "connection_info": "https://link.com",
            "max_attempts": 3,
            "value": 50,
            "category": "web",
            "type": "standard",
            "state": "visibe or hidden",
            "flags": [
                {
                    "uuid": "000000000000000",
                    "type": "static",
                    "content": "flag{answer}",
                    "data": "case_insensitive",
                },
                {
                    "uuid": "000000000000000",
                    "type": "regex",
                    "content": "flag{.a*}",
                    "data": "",
                }
            ],
            "tags": [
                "tag1", "tag2"
            ],
            "hints": [
                {
                    "uuid": "000000000000000",
                    "title": "Hint 1",
                    "type": "standard",
                    "content": "Follow the white rabbit...",
                    "cost": 10
                },
                {
                    "uuid": "000000000000000",
                    "title": "Hint 2",
                    "type": "?",
                    "content": "?",
                    "cost": 20
                }
            ],
        }
    }

    json_bytes = json.dumps(example, indent=4, ensure_ascii=False).encode("utf-8-sig")

    return Response(
        json_bytes,
        mimetype="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="challenge_example.json"'
        },
    )


@my_bp.route("/plugins/github_backup/challenges", methods=["GET"])
@admins_only
def get_challenges():
    """
    Fetches a list of all challenges and their import status from GitHub.
    """
    challenges = Challenges.query.all()

    data = []
    for challenge in challenges:
        is_imported = is_imported_from_github(challenge.id)
        data.append({
            "id": challenge.id,
            "name": challenge.name,
            "imported": is_imported,
        })

    return {"success": True, "challenges": data}


@my_bp.route("/plugins/github_backup/challenges/download", methods=["POST"])
@admins_only
def download_multiple_challenges():
    """
    Handles a POST request to download multiple challenges as a ZIP archive.
    """
    try:
        challenge_ids = request.json.get("challenge_ids", [])
        if not challenge_ids:
            return {"success": False, "message": "No challenge IDs provided"}, 400

        # Creamos un buffer en memoria
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for cid in challenge_ids:
                try:
                    data, name = prepare_json(int(cid))
                    json_bytes = json.dumps(data, indent=4, ensure_ascii=False).encode("utf-8-sig")
                    zip_file.writestr(f"challenge_{name}.json", json_bytes)
                except Exception as e:
                    zip_file.writestr(f"challenge_{cid}_error.txt", str(e))

        zip_buffer.seek(0)

        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name="challenges_export.zip",
        )


    except Exception as e:
        return {"success": False, "message": f"Unexpected error: {str(e)}"}, 500