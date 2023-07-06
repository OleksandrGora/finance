import os
import datetime

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")
# db.execute("DROP TABLE transactions")
# db.execute("DROP TABLE shares_state")
# db.execute("DELETE FROM users")
# db.execute("DELETE FROM sqlite_sequence")

db.execute(
    "CREATE TABLE IF NOT EXISTS 'transactions'"
    " ('trans_id' integer PRIMARY KEY AUTOINCREMENT NOT NULL,"
    "'user_id' int NOT NULL, 'symbol' varchar(255) NOT NULL,"
    "'shares' int NOT NULL,'price' real,'timestamp' timestamp)"
)
db.execute(
    "CREATE TABLE IF NOT EXISTS 'shares_state' ('user_id' int NOT NULL,"
    "'symbol' varchar(255) NOT NULL,'shares' int NOT NULL)"
)


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    user_id = session["user_id"]

    result = db.execute(
        "SELECT symbol, shares FROM shares_state WHERE user_id=? AND shares>0",
        user_id,
    )

    result1 = db.execute(
        "SELECT cash FROM users WHERE id=?",
        user_id,
    )

    cash = result1[0]["cash"]
    total = cash

    print(result1)

    for r in result:
        temp_res = lookup(r["symbol"])
        r["price"] = temp_res["price"]
        r["name"] = temp_res["name"]
        r["sum"] = r["shares"] * r["price"]
        total += r["sum"]
        r["sum"] = usd(r["sum"])
        r["price"] = usd(r["price"])
        r["symbol"] = r["symbol"].upper()

    print(result)

    return render_template("home.html", result=result, total=usd(total), cash=usd(cash))
    # return apology("TODO")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user_name = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        # Ensure username was submitted
        if not user_name:
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not password:
            return apology("must provide password", 403)

        elif not password == confirmation:
            return apology("passwords do not match", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = :username",
            username=user_name,
        )

        # Ensure username exists and password is correct
        if len(rows) > 0:
            # print(len(rows))
            return apology("username exists", 403)
        else:
            pass_hash = generate_password_hash(password)
            db.execute(
                "INSERT INTO users (username, hash, cash) VALUES (?,?,?)",
                user_name,
                pass_hash,
                10000,
            )

        # Remember which user has logged in
        # session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")
    else:
        return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Login user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = :username",
            username=request.form.get("username"),
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page

        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":
        # doing action after submitting form
        symbol = request.form.get("quote")
        if len(symbol) > 4:
            return apology("please enter another symbol", 403)

        response = lookup(symbol)
        print(response)
        return render_template("quoted.html", response=response)
    else:
        """Get stock quote."""
        return render_template("quote.html")
    # return apology("TODO")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        # doing action after submitting form
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")

        try:
            shares = int(shares)
        except:
            return apology("must provide number of shares", 403)

        if not symbol:
            return apology("must provide company symbol", 403)

        elif not shares or shares <= 0:
            return apology("must provide number of shares", 403)

        response = lookup(symbol)
        if not response:
            return apology("symbol not found", 403)

        price = response["price"]
        ct = datetime.datetime.now()
        user_id = session["user_id"]

        result = db.execute("SELECT cash FROM users WHERE id=?", user_id)

        if result[0]["cash"] - shares * price < 0:
            return apology("it is lack of money", 403)

        db.execute(
            "UPDATE users SET cash=? WHERE id=?",
            result[0]["cash"] - shares * price,
            user_id,
        )

        db.execute(
            "INSERT INTO transactions (user_id, symbol, shares, price,timestamp) VALUES (?, ?, ?, ?, ?)",
            user_id,
            symbol.upper(),
            shares,
            price,
            ct,
        )

        result = db.execute(
            "SELECT shares FROM shares_state WHERE user_id=? AND symbol=?",
            user_id,
            symbol,
        )

        # print(result[0]["Shares"])

        if not result:
            db.execute(
                "INSERT INTO shares_state (user_id, symbol, shares) VALUES (?, ?, ?)",
                user_id,
                symbol.upper(),
                shares,
            )
        else:
            db.execute(
                "UPDATE shares_state SET shares=? WHERE user_id=? AND symbol=?",
                shares + result[0]["shares"],
                user_id,
                symbol.upper(),
            )
        return redirect("/")
    else:
        """Get stock quote."""
        symbol = request.args.get("symbol")
        return render_template("buy.html", symbol=symbol)


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    user_id = session["user_id"]
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")

        try:
            shares = int(shares)
        except:
            return apology("must provide number of shares", 403)

        result = db.execute(
            "SELECT shares FROM shares_state WHERE user_id=? AND symbol=?",
            user_id,
            symbol,
        )
        print(result)
        if len(result) == 0 or result[0]["shares"] < shares:
            return apology("choose correct symbol or enter correct share number", 403)

        if result[0]["shares"] == shares:
            db.execute(
                "DELETE FROM shares_state WHERE user_id=? AND symbol=?",
                user_id,
                symbol.upper(),
            )
        else:
            db.execute(
                "UPDATE shares_state SET shares=? WHERE user_id=? AND symbol=?",
                result[0]["shares"] - shares,
                user_id,
                symbol.upper(),
            )

        response = lookup(symbol)
        price = response["price"]
        ct = datetime.datetime.now()

        db.execute(
            "INSERT INTO transactions (user_id, symbol, shares, price,timestamp) VALUES (?, ?, ?, ?, ?)",
            user_id,
            symbol.upper(),
            -shares,
            price,
            ct,
        )

        result = db.execute("SELECT cash FROM users WHERE id=?", user_id)
        db.execute(
            "UPDATE users SET cash=? WHERE id=?",
            result[0]["cash"] + shares * price,
            user_id,
        )

        return redirect("/")
    else:
        """Sell shares of stock"""
        result = db.execute(
            "SELECT symbol FROM shares_state WHERE user_id=? AND shares > 0",
            user_id,
        )
        symbol = request.args.get("symbol")

        if len(result) == 1:
            symbol = result[0]['symbol']

        return render_template("sell.html", result=result, symbol=symbol)


@app.route("/check", methods=["GET"])
def check():
    username = request.args.get("username")
    if len(username) < 1:
        return jsonify({"avalaible": False})

    rows = db.execute(
        "SELECT * FROM users WHERE username = :username",
        username=username,
    )

    # Ensure username exists and password is correct
    if len(rows) > 0:
        # print(len(rows))
        """Return true if username available, else false, in JSON format"""
        return jsonify({"avalaible": False})
    else:
        return jsonify({"avalaible": True})


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user_id = session["user_id"]
    result = db.execute(
        "SELECT * FROM transactions WHERE user_id=?",
        user_id,
    )

    for r in result:
        r["price"] = usd(r["price"])

    return render_template("history.html", result=result)


@app.route("/change_pass", methods=["GET", "POST"])
@login_required
def change_pass():
    user_id = session["user_id"]
    if request.method == "POST":
        old_pass = request.form.get("old_pass")
        new_pass = request.form.get("new_pass")
        confirmation = request.form.get("confirmation")
        # Ensure username was submitted
        if not old_pass:
            return apology("must provide old_pass", 403)

        # Ensure password was submitted
        elif not new_pass:
            return apology("must provide new_pass", 403)

        elif not new_pass == confirmation:
            return apology("new passwords do not match", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE id = :id",
            id=user_id,
        )

        if not check_password_hash(rows[0]["hash"], old_pass):
            return apology("old password is wrong", 403)
        else:
            pass_hash = generate_password_hash(new_pass)
            db.execute(
                "UPDATE users SET hash=? WHERE id=?",
                pass_hash,
                user_id,
            )

        # Remember which user has logged in
        # session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")
    else:
        return render_template("change_pass.html")


@app.route("/refill", methods=["GET", "POST"])
@login_required
def refill():
    if request.method == "POST":
        user_id = session["user_id"]
        refill = request.form.get("refill")
        # Ensure refill is > 0
        try:
            refill = float(refill)
        except:
            return apology("must provide correct amount", 403)

        if not refill or refill <= 0:
            return apology("must provide correct amount", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE id = :id",
            id=user_id,
        )

        cash = rows[0]["cash"]

        db.execute(
            "UPDATE users SET cash=? WHERE id=?",
            cash + refill,
            user_id,
        )

        # Redirect user to home page
        return redirect("/")
    else:
        return render_template("refill.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

if __name__ == "__main__":
    app.run(debug=True)
