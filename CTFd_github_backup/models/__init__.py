from CTFd.models import db

class UserGitHubToken(db.Model):
    __tablename__ = "user_github_tokens"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    token = db.Column(db.String(255), nullable=False)

    user = db.relationship("Users", backref="github_token_entry", uselist=False)


class GithubRepositories(db.Model):
    __tablename__ = "github_repositories"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    github_repo_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255), nullable=False)
    selected = db.Column(db.Boolean, default=False)
    last_synced_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("Users", backref="github_repositories")


class GithubChallengeSync(db.Model):
    __tablename__ = "github_challenge_sync"

    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"))
    github_repo_id = db.Column(db.Integer, db.ForeignKey("github_repositories.id", ondelete="CASCADE"))
    challenge_uuid = db.Column(db.String(64), nullable=False, unique=True)
    challenge_path = db.Column(db.String(255), nullable=True)
    last_updated_at = db.Column(db.DateTime, nullable=True)

    challenge = db.relationship("Challenges", backref="github_sync")
    repo = db.relationship("GithubRepositories", backref="synced_challenges")


class GithubFlagSync(db.Model):
    __tablename__ = "github_flag_sync"

    id = db.Column(db.Integer, primary_key=True)
    flag_id = db.Column(db.Integer, db.ForeignKey("flags.id", ondelete="CASCADE"))
    github_repo_id = db.Column(db.Integer, db.ForeignKey("github_repositories.id", ondelete="CASCADE"))
    challenge_uuid = db.Column(db.String(64), nullable=False)
    flag_uuid = db.Column(db.String(64), nullable=False)
    last_updated_at = db.Column(db.DateTime, nullable=True)

    flag = db.relationship("Flags", backref="github_sync")
    repo = db.relationship("GithubRepositories", backref="synced_flags")


class GithubHintSync(db.Model):
    __tablename__ = "github_hint_sync"

    id = db.Column(db.Integer, primary_key=True)
    hint_id = db.Column(db.Integer, db.ForeignKey("hints.id", ondelete="CASCADE"))
    github_repo_id = db.Column(db.Integer, db.ForeignKey("github_repositories.id", ondelete="CASCADE"))
    hint_uuid = db.Column(db.String(128), nullable=False, unique=True)
    challenge_uuid = db.Column(db.String(128), nullable=False)
    hint_path = db.Column(db.String(512), nullable=True)
    last_updated_at = db.Column(db.DateTime, nullable=True)