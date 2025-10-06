from CTFd.models import Tags, Flags, Hints, Challenges
from CTFd.plugins.github_backup.validate_data import validate_tags_data, validate_flag_data, validate_hints_data, validate_challenge_data
from CTFd.plugins.github_backup.models import db, GithubChallengeSync, GithubFlagSync, GithubHintSync
from datetime import datetime
import json
import requests

def import_tags(challenge, tags_data, path, overwrite_existing):
    """
    Imports tags into the database for a given challenge.
    """
    validate_tags_data(tags_data, path)

    if overwrite_existing:
        Tags.query.filter_by(challenge_id=challenge.id).delete()

    for tag in tags_data:
        tag_entry = Tags(challenge_id=challenge.id, value=tag)
        db.session.add(tag_entry)


def import_flags(challenge_id, flags, repo_id, challenge_uuid, path, overwrite_existing):
    """
    Imports flags for a specific challenge and synchronizes them with a GitHub repository. This process allows adding,
    updating, and deleting flags based on their presence within the provided input data.
    """
    json_flag_uuids = set()
    now = datetime.utcnow()

    for flag in flags:
        try:
            validate_flag_data(flag, path)
        except ValueError as ve:
            raise ValueError(str(ve))

        flag_uuid = flag["uuid"]
        json_flag_uuids.add(flag_uuid)

        existing_flag_sync = GithubFlagSync.query.filter_by(flag_uuid=flag_uuid).first()

        if existing_flag_sync:
            if overwrite_existing:
                existing_flag = Flags.query.get(existing_flag_sync.flag_id)
                if existing_flag:
                    existing_flag.type = flag["type"]
                    existing_flag.content = flag["content"]
                    existing_flag.data = flag.get("data", "")
                    existing_flag_sync.last_updated_at = now
        else:
            new_flag = Flags(
                challenge_id=challenge_id,
                type=flag["type"],
                content=flag["content"],
                data=flag.get("data", "")
            )
            db.session.add(new_flag)
            db.session.flush()

            db.session.add(GithubFlagSync(
                flag_id=new_flag.id,
                github_repo_id=repo_id,
                challenge_uuid=challenge_uuid,
                flag_uuid=flag_uuid,
                last_updated_at=now
            ))

    # Delete flags that no longer exist in the JSON
    synced_flags = GithubFlagSync.query.filter_by(
        github_repo_id=repo_id,
        challenge_uuid=challenge_uuid
    ).all()

    for synced in synced_flags:
        if synced.flag_uuid not in json_flag_uuids:
            flag = Flags.query.get(synced.flag_id)
            if flag:
                db.session.delete(flag)
            db.session.delete(synced)


def import_hints(*, challenge_id, hints, repo_id, challenge_uuid, path, overwrite_existing=True):
    """
    Imports hints into the system, either creating new hints or updating existing ones. This function manages
    the synchronization of hints by using their unique identifiers (UUIDs). If a hint with the same UUID
    already exists, it may be updated depending on the overwrite_existing parameter.
    """
    validate_hints_data(hints, path)

    for hint_data in hints:
        uuid = hint_data.get("uuid")
        if not uuid:
            raise ValueError("One of the hints is missing the 'uuid' field.")

        existing_sync = GithubHintSync.query.filter_by(hint_uuid=uuid).first()

        if existing_sync:
            if overwrite_existing:
                hint = Hints.query.get(existing_sync.hint_id)
                if hint:
                    hint.title = hint_data.get("title", "")
                    hint.content = hint_data.get("content", "")
                    hint.cost = hint_data.get("cost", 0)
                    hint.type = hint_data.get("type", "standard")
                    existing_sync.last_updated_at = datetime.utcnow()
                continue
            else:
                continue

        hint = Hints(
            challenge_id=challenge_id,
            title=hint_data.get("title", ""),
            content=hint_data.get("content", ""),
            cost=hint_data.get("cost", 0),
            type=hint_data.get("type", "standard")
        )
        db.session.add(hint)
        db.session.flush()

        db.session.add(GithubHintSync(
            hint_id=hint.id,
            github_repo_id=repo_id,
            hint_uuid=uuid,
            challenge_uuid=challenge_uuid,
            hint_path=path,
            last_updated_at=datetime.utcnow()
        ))


def import_or_update_challenge(challenge_info, repo, path, overwrite_existing):
    """
    Handles the import or update of a challenge within a system by validating
    provided data, checking for existing synchronization records, and either
    updating or creating new database entries based on the operations performed.
    Performs optional overwriting of existing data when specified.
    """
    uuid = challenge_info.get("uuid")
    if not uuid:
        return None, False, "Missing 'uuid' field"

    try:
        validated_data = validate_challenge_data(challenge_info, path)
    except ValueError as ve:
        return None, False, str(ve)

    existing_sync = GithubChallengeSync.query.filter_by(challenge_uuid=uuid).first()

    if existing_sync:
        if overwrite_existing:
            challenge = Challenges.query.get(existing_sync.challenge_id)
            if challenge:
                challenge.name = validated_data["name"]
                challenge.description = validated_data["description"]
                challenge.category = validated_data["category"]
                challenge.value = validated_data["value"]
                challenge.state = validated_data["state"]
                challenge.type = validated_data["type"]
                challenge.connection_info = validated_data.get("conection_info")
                challenge.max_attempts = validated_data.get("max_attemps", 0)
                challenge.attribution = validated_data.get("attribution")
                existing_sync.last_updated_at = datetime.utcnow()
                return challenge, False, None
            else:
                return None, False, "Synchronized challenge not found in the database"
        else:
            return None, False, "Challenge already synchronized (no overwrite)"
    else:
        challenge = Challenges(
            name=validated_data["name"],
            description=validated_data["description"],
            category=validated_data["category"],
            value=validated_data["value"],
            state=validated_data["state"],
            type=validated_data["type"],
            connection_info=validated_data.get("conection_info"),
            max_attempts=validated_data.get("max_attemps", 0),
            attribution=validated_data.get("attribution")
        )
        db.session.add(challenge)
        db.session.flush()

        db.session.add(GithubChallengeSync(
            challenge_id=challenge.id,
            github_repo_id=repo.id,
            challenge_uuid=uuid,
            challenge_path=path,
            last_updated_at=datetime.utcnow()
        ))

        return challenge, True, None
    
    
def remove_orphaned_challenges(repo, processed_paths, delete_mode="sync_only"):
    """
    Removes orphaned challenges associated with a given repository.

    This function identifies and removes database entries of challenges that are no
    longer present in the processed paths set provided. Orphaned challenges are
    identified as paths existing in the database but not in the `processed_paths` set.
    The function provides two modes of deletion: `sync_only`, which removes only the
    sync information, and `full`, which removes both the sync information and the
    associated challenge. Any encountered errors during the process are logged and
    returned.
    """
    errors = []
    count_removed = 0

    synced_challenges = GithubChallengeSync.query.filter_by(github_repo_id=repo.id).all()
    db_paths = {sc.challenge_path for sc in synced_challenges}
    missing_paths = db_paths - processed_paths

    for sc in synced_challenges:
        if sc.challenge_path in missing_paths:
            try:
                if delete_mode == "sync_only":
                    db.session.delete(sc)
                    count_removed += 1
                elif delete_mode == "full":
                    challenge = Challenges.query.get(sc.challenge_id)
                    if challenge:
                        db.session.delete(challenge)
                    db.session.delete(sc)
                    count_removed += 1
            except Exception as e:
                errors.append({"file": sc.challenge_path, "error": f"Error deleting: {str(e)}"})
                continue

    return count_removed, errors



def import_challenges_from_repo(repo, access_token, overwrite_existing=True, delete_mode="full"):
    """
    Imports challenge data from a specified GitHub repository into the system.
    """
    headers = {
        "Authorization": f"token {access_token}",
        "Accept": "application/vnd.github+json"
    }

    base_url = f"https://api.github.com/repos/{repo.full_name}/contents/challenges"
    file_list_resp = requests.get(base_url, headers=headers)

    print(file_list_resp)

    if file_list_resp.status_code != 200:
        return {"success": False, "message": "Could not access /challenges in the repository."}

    file_list = file_list_resp.json()
    count_created = 0
    count_updated = 0
    count_skipped = 0
    errors = []

    processed_paths = set()

    for file in file_list:
        if not file["name"].endswith(".json"):
            continue

        path = file["path"]

        file_resp = requests.get(file["download_url"], headers=headers)
        if file_resp.status_code != 200:
            errors.append({"file": path, "error": f"HTTP {file_resp.status_code}"})
            continue

        try:
            challenge_data = json.loads(file_resp.text)
            challenge_info = challenge_data.get("challenge", {})

            challenge, created, error_msg = import_or_update_challenge(challenge_info, repo, path, overwrite_existing)

            if error_msg:
                processed_paths.add(path)

                if error_msg != "Challenge already synchronized (no overwrite)":
                    errors.append({"file": path, "error": error_msg})
                else:
                    count_skipped += 1
                continue

            processed_paths.add(path)

            if challenge.type == "standard":
                if "dynamic" in challenge_info:
                    errors.append({"file": path, "error": "Standard challenges cannot have dynamic data."})
                    continue

                # Flags
                try:
                    import_flags(
                        challenge_id=challenge.id,
                        flags=challenge_info.get("flags", []),
                        repo_id=repo.id,
                        challenge_uuid=challenge_info["uuid"],
                        path=path,
                        overwrite_existing=overwrite_existing
                    )
                except ValueError as ve:
                    errors.append({"file": path, "error": str(ve)})
                    continue

                #
                try:
                    import_hints(
                        challenge_id=challenge.id,
                        hints=challenge_info.get("hints", []),
                        repo_id=repo.id,
                        challenge_uuid=challenge_info["uuid"],
                        path=path,
                        overwrite_existing=overwrite_existing
                    )
                except ValueError as ve:
                    errors.append({"file": path, "error": str(ve)})
                    continue

                # Import tags
                tags_data = challenge_info.get("tags", [])
                if tags_data:
                    try:
                        import_tags(challenge, tags_data, path, overwrite_existing)
                    except ValueError as ve:
                        errors.append({"file": path, "error": str(ve)})
                        continue

            else:
                continue

            if created:
                count_created += 1
            else:
                count_updated += 1

        except Exception as e:
            errors.append({"file": path, "error": str(e)})
            continue

    count_removed, orphan_errors = remove_orphaned_challenges(repo, processed_paths, delete_mode)
    errors.extend(orphan_errors)

    repo.last_synced_at = datetime.utcnow()
    db.session.commit()

    return {
        "success": True,
        "created": count_created,
        "updated": count_updated,
        "skipped": count_skipped,
        "removed": count_removed,
        "errors": errors
    }