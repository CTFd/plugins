from CTFd.plugins.github_backup.models import GithubChallengeSync, GithubFlagSync, GithubHintSync
from CTFd.models import Tags, Flags, Hints, Challenges
from CTFd.plugins.github_backup.utils import generate_uuid


def is_imported_from_github(challenge_id: int) -> bool:
    """
    Determines if a challenge is imported from GitHub.
    """
    challenge_sync = GithubChallengeSync.query.filter_by(challenge_id=challenge_id).first()
    return bool(challenge_sync)


def prepare_json(challenge_id: int) -> tuple[dict, str]:
    """
    Generates a JSON-like structure and corresponding name for a given challenge.
    """
    challenge = Challenges.query.filter_by(id=challenge_id).first()
    if not challenge:
        raise ValueError("Challenge not found")

    challenge_sync = GithubChallengeSync.query.filter_by(challenge_id=challenge.id).first()

    if not challenge_sync:
        chellenge_uuid = generate_uuid()
    else:
        chellenge_uuid = challenge_sync.challenge_uuid

    # Prepare challenge data
    data = {
        "challenge": {
            "uuid": chellenge_uuid,
            "name": challenge.name,
            "description": challenge.description,
            "attribution": challenge.attribution,
            "connection_info": challenge.connection_info,
            "max_attempts": challenge.max_attempts,
            "value": challenge.value,
            "category": challenge.category,
            "type": challenge.type,
            "state": challenge.state,
            "flags": [],
            "tags": [],
            "hints": [],
        }
    }

    # Prepare flags data
    flags = Flags.query.filter_by(challenge_id=challenge.id).all()
    for f in flags:
        flag_sync = GithubFlagSync.query.filter_by(flag_id=f.id).first()

        if not flag_sync:
            flag_uuid = generate_uuid()
        else:
            flag_uuid = flag_sync.flag_uuid

        data["challenge"]["flags"].append({
            "uuid": flag_uuid,
            "type": f.type,
            "content": f.content,
            "data": f.data
        })

    # Prepare tags data
    tags = Tags.query.filter_by(challenge_id=challenge.id).all()
    data["challenge"]["tags"] = [t.value for t in tags]

    # Prepare hints data
    hints = Hints.query.filter_by(challenge_id=challenge.id).all()
    for h in hints:
        hint_sync = GithubHintSync.query.filter_by(hint_id=h.id).first()

        if not hint_sync:
            hint_uuid = generate_uuid()
        else:
            hint_uuid = hint_sync.hint_uuid

        data["challenge"]["hints"].append({
            "uuid": hint_uuid,
            "title": h.content,
            "type": h.type,
            "content": h.content,
            "cost": h.cost
        })

    return data, challenge.name
