from flask import Blueprint
from flask import redirect, render_template, url_for 
from CTFd.models import db 
from CTFd.utils import user as current_user
from CTFd.utils.security.auth import logout_user
from CTFd.utils.helpers import get_errors

auth = Blueprint("auth", __name__)

@auth.route("/login", methods=["GET"])
def login():
    errors = get_errors()
    db.session.close()
    return render_template("login.html", errors=errors)

@auth.route("/logout")
def logout():
    if current_user.authed():
        logout_user()
    return redirect(url_for("views.static_html"))