import pytz
import csv
import datetime

from cs50 import SQL
from flask import Flask, redirect, render_template, request, session, send_from_directory
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers2 import login_required, lookup, usd, stock_analysis, query_api, results



# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance2.db")


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
    """Show portfolio of stocks"""

    shsy_ls = db.execute("SELECT SUM(shares) AS sum_shr,"
                            f"symbol FROM transactions WHERE userId = ? GROUP BY symbol",
                            session["user_id"]
                        )

    total2 = 0
    shsy_els = []
    for i in range(0, len(shsy_ls)):

        symbol = shsy_ls[i]["symbol"]

        if shsy_ls[i]["sum_shr"] > 0:
            d = 7
            current_price = lookup(symbol,d)["price"]
            shares = shsy_ls[i]["sum_shr"]
            total = current_price * shares
            total2 += total

            shsy_els.append({"cprice": usd(current_price),
                                    "total" : usd(total),
                                    "sum_shr" : shares,
                                    "symbol" : symbol
                            })

    cash_ls = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
    cash = usd(cash_ls[0]["cash"])
    total2 = usd(total2 + cash_ls[0]["cash"])

    return render_template("index.html", shsy_els = shsy_els, cash = cash, total2 = total2)



@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        try:
            symbol = request.form.get("symbol")
            shares = int(request.form.get("shares"))
            d = 7
            price_dict = lookup(symbol,d)
            pr = price_dict["price"]
            total = pr * shares
            usr = session["user_id"]
            cash_tb = db.execute("SELECT cash FROM users WHERE id = ?", usr)
            cash_vl = cash_tb[0]["cash"]
            diff = cash_vl - total

            if  diff < 0:
                return render_template("buy.html",
                                       error_message="Insufficient funds, make a deposit to buy stocks"
                                       )

            else:
                db.execute("UPDATE users SET cash = ? WHERE id = ?", diff, session["user_id"])
                db.execute("CREATE TABLE IF NOT EXISTS transactions ("
                            f"id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,"
                            f"userId INTEGER NOT NULL, symbol TEXT NOT NULL,"
                            f"price REAL NOT NULL,"
                            f"shares INTEGER NOT NULL,"
                            f"type TEXT NOT NULL,"
                            f"year INTEGER, month INTEGER, day INTEGER, hour INTEGER, minute INTEGER,"
                            f"span INTEGER, change REAL)"
                )

                yr = datetime.datetime.now(pytz.timezone("US/Eastern")).year
                mo = datetime.datetime.now(pytz.timezone("US/Eastern")).month
                dy = datetime.datetime.now(pytz.timezone("US/Eastern")).day
                hr = datetime.datetime.now(pytz.timezone("US/Eastern")).hour
                mi = datetime.datetime.now(pytz.timezone("US/Eastern")).minute

                db.execute("INSERT INTO transactions ("
                            f"userId, symbol, price, shares, type,"
                            f"year, month, day, hour, minute,"
                            f"span, change)"
                            f" VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            usr, symbol.upper(), pr, shares, "buy", yr, mo, dy, hr, mi, 0, 0.0
                )

            # Redirect user
            return redirect("/")

        except ValueError:
            return render_template("buy.html",
                                   error_message= "The symbol and/or the number of shares is incorrect"
                                   )

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("buy.html")


@app.route("/history", methods=["GET", "POST"])
@login_required
def history():
    """Show history of transactions"""
    if request.method == "POST":

        #format: Year-month-day
        date_since = request.form.get("since")
        date_to = request.form.get("to")

        if (not date_since) or (not date_to):
            return redirect("/history")

        since_ls = date_since.split("-")
        to_ls = date_to.split("-")

        ehist_tb = db.execute("SELECT * FROM transactions WHERE userId = ?", session["user_id"])

        aux_tab = []
        for row in ehist_tb:
            if (int(since_ls[0]) <= row["year"] <= int(to_ls[0])):
                if (int(since_ls[1]) <= row["month"] <= int(to_ls[1])):
                    if (int(since_ls[2]) <= row["day"] <= int(to_ls[2])):
                        aux_tab.append(row)

        return render_template("history.html", ehist_tb = aux_tab)


    else:
        aux_tb = db.execute("SELECT SUM(shares) AS sum_shr,"
                            f"symbol FROM transactions WHERE userId = ? GROUP BY symbol", session["user_id"])
        hist_tb = db.execute("SELECT * FROM transactions WHERE userId = ?", session["user_id"])

        for row in hist_tb:
            if row["type"] == "buy":
                symbol = row["symbol"]
                #purchase price
                ppr = row["price"]
                #current price
                pr_dict = lookup(symbol,7)
                cpr = pr_dict["price"]
                #purchase date
                pdate = str(row["day"]) + "/" + str(row["month"]) + "/" + str(row["year"])
                pddate = datetime.datetime.strptime(pdate, "%d/%m/%Y")
                #current date
                yr = datetime.datetime.now(pytz.timezone("US/Eastern")).year
                mo = datetime.datetime.now(pytz.timezone("US/Eastern")).month
                dy = datetime.datetime.now(pytz.timezone("US/Eastern")).day
                cdate = str(dy) + "/" + str(mo) + "/" + str(yr)
                cddate = datetime.datetime.strptime(cdate, "%d/%m/%Y")

                span = (cddate - pddate).days
                row["span"] = span
                change = round((cpr/ppr - 1)*100, 1)
                row["change"] = change

                db.execute("UPDATE transactions SET span=?, change=? WHERE id= ?",
                           row["id"], span, change)

            else:
                row["span"] = "-"
                row["change"] = "-"

        ehist_tb = []
        for row in hist_tb:
            for e in aux_tb:
                if (e["sum_shr"] != 0) and (e["symbol"] == row["symbol"]):
                        ehist_tb.append(row)

        return render_template("history.html", ehist_tb = ehist_tb)



@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            message = "Provide an username"
        # Ensure password was submitted
        elif not request.form.get("password"):
            message = "Provide a password"
        else:
            message = "OK"

        if message != "OK":
            return render_template("login.html", error_message= message)
        else:
            # Query database for username
            rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
            # Ensure username exists and password is correct
            if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
                return render_template("login.html", error_message= "Invalid username and/or password")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")



@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        symbol = request.form.get("symbol")
        d = 10*360 #days

        try:
            quotes = query_api(symbol, d)

            # Specify the file name
            csv_file_path = "static/files/" + symbol.upper() + ".csv"
            # Writing to the CSV file
            with open(csv_file_path, mode='w', newline='') as csv_file:
                fieldnames = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
                # Create a DictWriter object
                csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                # Write the header to the CSV file
                csv_writer.writeheader()
                # Write the data to the CSV file
                csv_writer.writerows(quotes)

            #placeholder jinja
            price = float(quotes[len(quotes)-1]["Close"])

            return render_template("quote.html", price=usd(price), symbol=symbol.upper())

        except (AttributeError, TypeError):
            return render_template("quoted.html", error_message= "Invalid symbol")

    else:
        return render_template("quoted.html")



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            message = "Must provide username"

        # Ensure password was submitted
        elif not request.form.get("password"):
            message = "Must provide password"

        # Ensure confirmation was submitted
        elif not request.form.get("confirmation"):
            message = "Must provide confirmation"

        # Ensure confirmation coincides with password
        elif request.form.get("confirmation") != request.form.get("password"):
            message = "Password and confirmation doesn't coincide"
        else:
            message = "OK"

        if message == "OK":

            # Query database for username
            rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

            # Ensure username doesn't exists
            if len(rows) == 1:
                message = "The username already exists"
                return render_template("register.html", error_message = message)
            else:
                username = request.form.get("username")
                pass_hash = generate_password_hash(request.form.get("password"))
                db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username, pass_hash)
        else:
            return render_template("register.html", error_message = message)

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")



@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        try:
            symbol = request.form.get("symbol")
            shares = int(request.form.get("shares"))

            if (not symbol) or (shares <= 0):
                raise ValueError

            shares_tb = db.execute("SELECT SUM(shares) AS sum_shr FROM transactions WHERE userId = ? AND symbol = ?",
                                   session["user_id"], symbol.upper())
            current_shares = shares_tb[0]["sum_shr"]
            diff = current_shares - shares

            if  diff < 0:
                raise ValueError
            else:
                d = 7 #days
                cash_tb = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
                cprice = lookup(symbol,d)["price"]
                total = shares * cprice
                cash_val = cash_tb[0]["cash"] + total
                db.execute("UPDATE users SET cash = ? WHERE id = ?", cash_val, session["user_id"])

                yr = datetime.datetime.now(pytz.timezone("US/Eastern")).year
                mo = datetime.datetime.now(pytz.timezone("US/Eastern")).month
                dy = datetime.datetime.now(pytz.timezone("US/Eastern")).day
                hr = datetime.datetime.now(pytz.timezone("US/Eastern")).hour
                mi = datetime.datetime.now(pytz.timezone("US/Eastern")).minute

                db.execute("INSERT INTO transactions ("
                           f"userId, symbol, price, shares, type, year, month, day, hour, minute) VALUES"
                           f"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           session["user_id"], symbol.upper(), cprice, -shares, "sell", yr, mo, dy, hr, mi)

            # Redirect user
            return redirect("/")

        except ValueError:
            message = "The number of shares is incorrect or excessive"
            symbol_ls = db.execute("SELECT SUM(shares) AS sum_shr, symbol FROM transactions WHERE userId = ? GROUP BY symbol",
                                   session["user_id"]
                                   )

            symbol_els = []
            for i in range(0, len(symbol_ls)):
                if symbol_ls[i]["sum_shr"] > 0:
                    symbol_els.append(symbol_ls[i]["symbol"])

            return render_template("sell.html", symbol_els = symbol_els, error_message = message)

    else:
        # User reached route via GET (as by clicking a link or via redirect)
        symbol_ls = db.execute("SELECT SUM(shares) AS sum_shr, symbol FROM transactions WHERE userId = ? GROUP BY symbol",
                               session["user_id"]
                               )

        symbol_els = []
        for i in range(0, len(symbol_ls)):
            if symbol_ls[i]["sum_shr"] > 0:
                symbol_els.append(symbol_ls[i]["symbol"])

        return render_template("sell.html", symbol_els = symbol_els)



@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():

    if request.method == "POST":

        try:
            deposit = float(request.form.get("deposit"))
            if deposit < 0:
                raise ValueError

            cnt_cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
            cash = cnt_cash[0]["cash"] + deposit

            db.execute("UPDATE users SET cash = ? WHERE id = ?", cash, session["user_id"])
            return redirect("/")

        except TypeError:
            message = "Insert the amount of money to deposit"
            return render_template("deposit.html", error_message = message)
        except ValueError:
            message = "Insert a valid number"
            return render_template("deposit.html", error_message = message)

    return render_template("deposit.html")



@app.route("/analysis", methods=["GET", "POST"])
@login_required
def stat_analysis():
    """Show statistical analysis"""

    if request.method == "POST":

        symbol = request.form.get("symbol")
        d = 30*360 #days

        if "remove" in symbol:
            remove_symbol = symbol.replace("remove","")
            db.execute("DELETE FROM analysis WHERE userId=? AND symbol=?",
                       session["user_id"], remove_symbol.upper())

        elif lookup(symbol, d) != None:

            db.execute("CREATE TABLE IF NOT EXISTS analysis"
                        f"(id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, userId INTEGER NOT NULL,"
                        f"symbol TEXT NOT NULL, Q1_dt INTEGER NOT NULL, Q3_dt INTEGER NOT NULL,"
                        f"Q1_rt REAL NOT NULL, Q3_rt REAL NOT NULL)"
                       )

            symbol_idb = db.execute("SELECT symbol FROM analysis WHERE userId=? AND symbol=?"
                                    , session["user_id"], symbol.upper())

            if not symbol_idb:
                dr_dict = stock_analysis(symbol, d)
                db.execute("INSERT INTO analysis (userId, symbol, Q1_dt, Q3_dt, Q1_rt, Q3_rt) VALUES(?, ?, ?, ?, ?, ?)",
                           session["user_id"], symbol.upper(), dr_dict["dt_Q1"], dr_dict["dt_Q3"],
                           dr_dict["rt_Q1"], dr_dict["rt_Q3"]
                          )

        return redirect("/analysis")

    else:
        analized_ls = db.execute("SELECT symbol, Q1_dt, Q3_dt, Q1_rt, Q3_rt FROM analysis WHERE userId = ?",
                                  session["user_id"])
        return render_template("analize.html", analized_ls = analized_ls)



@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    """Change your password"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        actual_hash = db.execute("SELECT hash FROM users WHERE id = ?", session["user_id"])
        actual_pass = request.form.get("actual_pass")
        new_pass = request.form.get("new_pass")
        confirmation = request.form.get("confirmation")
        # Ensure username was submitted
        if not actual_pass:
            message = "introduce your actual password"

        # Ensure actual password is correct
        elif not check_password_hash(actual_hash[0]["hash"], actual_pass):
            message = "your actual password is incorrect"

        # Ensure password was submitted
        elif not new_pass:
            message = "introduce your new password"

        # Ensure confirmation was submitted
        elif not confirmation:
            message = "confirm your new password"

        # Ensure confirmation coincides with password
        elif new_pass != confirmation:
            message = "your new password has not been confirmed"
        else:
            new_pass_hash = generate_password_hash(new_pass)
            db.execute("UPDATE users SET hash = ? WHERE id = ?", new_pass_hash, session["user_id"])
            return redirect("/login")

        return render_template("account.html", error_message= message)

    return render_template("account.html")


@app.route('/get_file/<filename>')
@login_required
def get_file(filename):
    return send_from_directory('static/files', filename)


@app.route("/returns", methods=["GET", "POST"])
@login_required
def returns():
    """calculate the returns (FIFO)"""

    if request.method == "POST":

        date_since = request.form.get("since")  #format: Year-month-day
        date_to = request.form.get("to")        #format: Year-month-day

        if (not date_since) or (not date_to):
            return redirect("/returns")

        since_ls = date_since.split("-")
        to_ls = date_to.split("-")

        hist_tb = db.execute("SELECT * FROM transactions WHERE userId = ?", session["user_id"])

        aux_tab = []
        for row in hist_tb:
            if (int(since_ls[0]) <= row["year"] <= int(to_ls[0])):
                if (int(since_ls[1]) <= row["month"] <= int(to_ls[1])):
                    if (int(since_ls[2]) <= row["day"] <= int(to_ls[2])):
                        aux_tab.append(row)

        if len(aux_tab) > 1:
            results_ls = results(aux_tab)
        else:
            results_ls = [{"date":"-", "symbol":"-", "return":"-", "days":"-", "dy_ret":"-"}]

        return render_template("returns.html", results = results_ls)


    else:
        hist_tb = db.execute("SELECT * FROM transactions WHERE userId = ?", session["user_id"])

        if len(hist_tb) > 1:

            results_ls = results(hist_tb)
        else:
            results_ls = [{"date":"-", "symbol":"-", "return":"-", "days":"-", "dy_ret":"-"}]

        return render_template("returns.html", results = results_ls)
