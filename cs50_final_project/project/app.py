import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///project.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show park reviews"""
    rows = db.execute(
        "SELECT park, SUM(shares) FROM transactions WHERE user_id=:user_id GROUP BY park HAVING SUM(shares) > 0", user_id=session["user_id"])

    holdings = []
    all_total = 0

    for row in rows:
        stock = lookup(row['park'])
        value = (stock["price"] * row["SUM(shares)"])
        holdings.append({"park": stock["park"], "name": stock["name"],
                        "shares": row["SUM(shares)"], "price": usd(stock["price"]), "total": usd(value)})
        all_total += stock["price"] * row["SUM(shares)"]


    return render_template("index.html", holdings=holdings, all_total=usd(all_total))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":

        # If symbol exists
        if not request.form.get("park"):
            return apology("Must Provide An Actual Symbol")

        # If you don't submit a share
        elif not request.form.get("shares"):
            return apology("Must Input Share(s)")

        # Shares are a whole number
        try:
            shares = int(request.form.get("shares"))
        except:
            return apology("Must Input Whole Number")

        # Shares are greater than 0
        if shares < 1:
            return apology("Must Be A Positive Number")

        # Looking up symbol
        symbol = request.form.get("park").upper()
        stock = lookup(symbol)
        if stock is None:
            return apology("symbol does not exist")

        # Transactions
        shares = int(request.form.get("shares"))
        transaction = shares * stock['price']


        update_cash = cash - transaction

        if update_cash < 0:
            return apology("Insufficient funds")


        # Update transactions table
        db.execute("INSERT INTO transactions (user_id, park, shares, price) VALUES (:user_id, :park, :shares, :price)",
                   user_id=session["user_id"], symbol=stock['park'], shares=shares, price=stock['price'])
        flash("Bought!")
        return redirect("/")

    else:
        return render_template("buy.html")




@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    """Allow user to change her password"""

    if request.method == "POST":

        # If you inputted old password
        if not request.form.get("current_password"):
            return apology("Please Enter Current Password")

        rows = db.execute("SELECT hash FROM users WHERE id = :user_id", user_id=session["user_id"])

        # Is old password correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("current_password")):
            return apology("Incorrect Password")

        # Entered new password
        if not request.form.get("new_password"):
            return apology("Must Enter New Password")

        # New Password Confirmation
        elif not request.form.get("new_password_confirmation"):
            return apology("Must Confirm New Password")

        elif request.form.get("new_password") != request.form.get("new_password_confirmation"):
            return apology("New Passwords Don't Match")

        # Update user and password database
        hash = generate_password_hash(request.form.get("new_password"))
        rows = db.execute("UPDATE users SET hash = :hash WHERE id = :user_id", user_id=session["user_id"], hash=hash)

        # Notification
        flash("Changed!")

    return render_template("change_password.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    session.clear()

    if request.method == "POST":

        # Was username entered
        if not request.form.get("username"):
            return apology("Must Enter Username")

        # Was password entered
        elif not request.form.get("password"):
            return apology("Must Enter Password")

        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Is username and password correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("Invalid Username And/Or Password")

        # Remember who logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    session.clear()

    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "GET":
        return render_template("quote.html")

    else:
        symbol = request.form.get("symbol")

        # If symbol was written
        if not symbol:
            return apology("Must Write Symbol")

        # Uppercase
        stock = lookup(symbol.upper())

        # If the symbol doesn't exist
        if stock == None:
            return apology("Symbol Does Not Exist")

        return render_template("quoted.html", name=stock["name"], price=stock["price"], symbol=stock["park"])


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")

    else:
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Enter Username
        if not username:
            return apology("Must Give Username")

        # Enter Password
        if not password:
            return apology("Must Give Password")

        # Confirm Password
        if not confirmation:
            return apology("Must Confirm Password")

        # Password and Confirmation match
        if password != confirmation:
            return apology("Passwords Don't Match")

        hash = generate_password_hash(password)

        # If username exists
        try:
            new_user = db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, hash)
        except:
            return apology("Username Already Exist")

        # Made new user
        session["user_id"] = new_user

        return redirect("/")



