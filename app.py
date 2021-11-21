from flask import Flask, request, abort, redirect, session
from os import environ, urandom
from requests import post, get
from datetime import timedelta
from github_webhook import Webhook

from orm import db, Sponsor
from bot import add_role, remove_role

app = Flask(__name__)

# environment variables
DISCORD_API_ENDPOINT = "https://discord.com/api/v6"

DISCORD_CLIENT_ID = environ["DISCORD_CLIENT_ID"]
DISCORD_CLIENT_SECRET = environ["DISCORD_CLIENT_SECRET"]
DISCORD_REDIRECT_URI = environ["DISCORD_REDIRECT_URI"]

GITHUB_CLIENT_ID = environ["GITHUB_CLIENT_ID"]
GITHUB_CLIENT_SECRET = environ["GITHUB_CLIENT_SECRET"]
GITHUB_REDIRECT_URI = environ["GITHUB_REDIRECT_URI"]
GITHUB_WEBHOOK_SECRET = environ["GITHUB_WEBHOOK_SECRET"]

MYSQL_USER = environ.get("MYSQL_USER", "sponsorcord")
MYSQL_DATABASE = environ.get("MYSQL_DATABASE", "sponsorcord")
MYSQL_PASSWORD = environ.get("MYSQL_PASSWORD", "password")
MYSQL_HOST = environ.get("MYSQL_HOST", "127.0.0.1")

DATABASE_TYPE = environ.get("DATABASE_TYPE", "mysql")

app.secret_key = environ.get("SECRET_KEY", urandom(24))

app.config["SESSION_COOKIE_SAMESITE"] = "Strict"
app.config["SESSION_PERMANENT"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=1)

# config
if DATABASE_TYPE == "mysql":
    app.config[
        "SQLALCHEMY_DATABASE_URI"
    ] = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DATABASE}"
elif DATABASE_TYPE == "sqlite":
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database/sponsorcord.db"
else:
    raise Exception(f"invalid DATABASE_TYPE {DATABASE_TYPE}")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# init db
db.init_app(app)

with app.app_context():
    db.create_all()

Session(app)
webhook = Webhook(app, endpoint="/github/webhook", secret=GITHUB_WEBHOOK_SECRET)


def github_login_url():
    return "https://github.com/login/oauth/authorize?%s" % "&".join(
        (
            f"client_id={GITHUB_CLIENT_ID}",
            f"redirect_uri={GITHUB_REDIRECT_URI}",
        )
    )


def get_github_user_id(code):
    data = {
        "client_id": GITHUB_CLIENT_ID,
        "client_secret": GITHUB_CLIENT_SECRET,
        "code": code,
        "redirect_uri": GITHUB_REDIRECT_URI,
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }
    r = post("https://github.com/login/oauth/access_token", data=data, headers=headers)
    r.raise_for_status()
    access_token = r.json()["access_token"]  # all we need

    # get user info
    headers = {"Authorization": f"token {access_token}"}
    r = get(f"https://api.github.com/user", headers=headers)
    r.raise_for_status()

    return r.json()["id"]


def discord_login_url():
    return "https://discord.com/api/oauth2/authorize?%s" % "&".join(
        (
            f"client_id={DISCORD_CLIENT_ID}",
            f"redirect_uri={DISCORD_REDIRECT_URI}",
            f"response_type=code",
            "scope=identify",
        )
    )


def get_discord_user_id(code):
    # get access_token and such
    data = {
        "client_id": DISCORD_CLIENT_ID,
        "client_secret": DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": DISCORD_REDIRECT_URI,
        "scope": "identify",
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = post("%s/oauth2/token" % DISCORD_API_ENDPOINT, data=data, headers=headers)
    r.raise_for_status()
    access_token = r.json()["access_token"]  # all we need

    # get user info
    headers = {"Authorization": f"Bearer {access_token}"}
    r = get(f"{DISCORD_API_ENDPOINT}/users/@me", headers=headers)
    r.raise_for_status()

    # return user info
    return r.json()["id"]


@app.route("/")
def index():
    if "github_id" not in session:
        return redirect(github_login_url())
    if "discord_id" not in session:
        return redirect(discord_login_url())
    sponsor = Sponsor.query.get(int(session["github_id"]))
    if not sponsor:
        return f"You are not a sponsor. github_id {session['github_id']} and discord_id {session['discord_id']}"

    if sponsor.discord_id:
        remove_role(sponsor.discord_id)

    sponsor.discord_id = int(session["discord_id"])
    db.session.add(sponsor)
    db.session.commit()

    add_role(session["discord_id"])

    return f"Wow, you are a sponsor! Your discord_id has been associated with your github_id and the role should have been added. github_id {session['github_id']} and discord_id {session['discord_id']}"


@webhook.hook(event_type="sponsorship")
def github_webhook(content):
    if "action" not in content:
        return "no action, nothing to do"

    if content["action"] == "created":
        sponsor = Sponsor(github_id=int(content["sender"]["id"]))
        db.session.add(sponsor)
        db.session.commit()

    if content["action"] == "cancelled":
        sponsor = Sponsor.query.get(int(content["sender"]["id"]))
        db.session.delete(sponsor)
        db.session.commit()

        try:
            remove_role(sponsor.discord_id)
        except Exception as e:
            print(
                f"tried to remove sponsor with GitHub id {sponsor.github_id} but it failed"
            )
            print(str(e))

    return "success"


@app.route("/auth/github/callback")
def github_callback():
    code = request.args.get("code")
    if not code:
        abort(400, "Invalid OAuth. Missing code.")

    session["github_id"] = get_github_user_id(code)
    return redirect("/")


@app.route("/auth/discord/callback")
def discord_callback():
    code = request.args.get("code")
    if not code:
        abort(400, "Invalid OAuth. Missing code.")

    session["discord_id"] = get_discord_user_id(code)
    return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0")
