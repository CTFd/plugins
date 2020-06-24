from flask import render_template, request, redirect, url_for, Blueprint, session
from CTFd.models import Users, db
from CTFd.utils import validators
from CTFd.utils.decorators import ratelimit
from CTFd.utils.helpers import get_errors
from CTFd.utils.plugins import override_template
from CTFd.utils.config import is_teams_mode
from CTFd.utils.logging import log
from CTFd.utils.security.auth import login_user
import ldap3
import random
import string
import os

def load(app):
    app.db.create_all()
    ldap = Blueprint('ldap', __name__, )

    # Change these settings to correspond to your ldap server
    settings = {
        "name": "ldap server",
        "host": "example.com",
        "port": 389,
        "encryption": "none",
        "base_dn": "dc=example,dc=com",
        "type_dn": "ou=people",
        "request": "(uid={})",
        "prefix": ""
    }

    # Replaces template files
    dir_path = os.path.dirname(os.path.realpath(__file__))
    template_path = os.path.join(dir_path, 'modified_templates/login.html')
    override_template('login.html', open(template_path).read())
    template_path = os.path.join(dir_path, 'modified_templates/settings.html')
    override_template('settings.html', open(template_path).read())
    template_path = os.path.join(dir_path, 'modified_templates/base.html')
    override_template('base.html', open(template_path).read())

    def login():
        errors = get_errors()
        if request.method == "POST":
            login_info = {
                'username': request.form["name"],
                'password': request.form["password"]
            }

            # Check if the user submitted an email address or username
            if validators.validate_email(login_info['username']) is True:
                user = Users.query.filter_by(email=login_info['username']).first()
                # If this is the first time logging inn you need to use your username
                errors.append("Use your username instead of email for first login")
            else:
                user = Users.query.filter_by(name=login_info['username']).first()

            # Ldap credentials prep
            login = login_info["username"].strip().lower()
            login_dn = 'uid=' + login + ',' + settings['type_dn'] + ',' + settings['base_dn']
            password = login_info["password"]

            if password.rstrip() == "":
                errors.append("Empty passwordfield")
                db.session.close()
                return render_template("login.html", errors=errors)

            try:
                # Connect to the ldap
                print("connection to ldap")
                server = ldap3.Server(settings['host'], port=settings['port'], use_ssl=settings["encryption"] == 'ssl', get_info=ldap3.ALL)
                conn = ldap3.Connection(server, user=login_dn, password=password, auto_bind='NONE', version=3, authentication='SIMPLE', client_strategy='SYNC', auto_referrals=True, check_names=True, read_only=False, lazy=False, raise_exceptions=False)
                # Start tls for confidentiality
                conn.start_tls()
                # Check authenticity of credentials
                if not conn.bind():
                    # I'll leave this print for troubleshooting with login. Tip: if login isn't working check 'type_dn' in settings. I assume all people are registered as 'ou=people' in the system
                    # print("ERROR ", conn.result)
                    errors.append("Your username or password is incorrect")
                    log("logins", "[{date}] {ip} - submitted invalid password for {name}")
                    db.session.close()
                    return render_template("login.html", errors=errors)
                print("Connected")
            except Exception as e:
                errors.append("Can't initialze connection to " + settings['host'] + ': ' + str(e))
                db.session.close()
                return render_template("login.html", errors=errors)

            # If we have gotten to this point it means that the user credentials matched an entry in ldap

            # Check if user has logged inn before
            if user:
                session.regenerate()

                login_user(user)
                log("logins", "[{date}] {ip} - {name} logged in")

                db.session.close()
                if request.args.get("next") and validators.is_safe_url(request.args.get("next")):
                    return redirect(request.args.get("next"))
                return redirect(url_for("challenges.listing"))
            else:
                # Register the user in our system
                # First we get email from ldap
                try:
                    ldap_request = settings["request"].format(login)
                    conn.search(settings["base_dn"], ldap_request, attributes=["cn", "mail"])
                    response = conn.response
                except Exception as ex:
                    errors.append("Can't get user data : " + str(ex))
                    conn.unbind()
                    db.session.close()
                    return render_template("login.html", errors=errors)
                try:
                    # In some systems users have multiple entries on the same username, we search for one that has an email attribute.
                    for entry in response:
                        if entry["attributes"]["mail"] != []:
                            email = entry["attributes"]["mail"][0]
                            break
                    conn.unbind()
                except KeyError as e:
                    errors.append("Can't get field " + str(e) + " from your LDAP server")
                    db.session.close()
                    return render_template("login.html", errors=errors)
                except Exception as e:
                    errors.append("Can't get some user fields", e)
                    db.session.close()
                    return render_template("login.html", errors=errors)

                # Add the new user to the DB
                with app.app_context():
                    # We create a random password, this won't be used and is simply here because it is required in CTFd
                    # It is random so the account cannot be accessed by conventional loggin
                    dummy_password = randomString(28)
                    user = Users(name=login, email=email, password=dummy_password)
                    db.session.add(user)
                    db.session.commit()
                    db.session.flush()

                    login_user(user)

                log("registrations", "[{date}] {ip} - {name} registered with {email}")
                db.session.close()

                if is_teams_mode():
                    return redirect(url_for("teams.private"))
                return redirect(url_for("challenges.listing"))
        else:
            db.session.close()
            return render_template("login.html", errors=errors)

    def randomString(stringLength=28):
        letters = string.ascii_lowercase
        return ''.join(random.choice(letters) for i in range(stringLength))

    # Removes registration of regular accounts
    def register_overwrite():
        return redirect('/404')
    app.view_functions['auth.register'] = register_overwrite

    # Removes oauth login
    def oauth_overwrite():
        return redirect('/404')
    app.view_functions['auth.oauth'] = oauth_overwrite
    
    app.view_functions['auth.login'] = login
    app.register_blueprint(ldap)