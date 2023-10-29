import csv
import datetime
import pytz
import requests
import urllib
import uuid

from numpy import quantile
from flask import redirect, session
from functools import wraps


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol,d):
    """Look up quote for symbol."""
    symbol = symbol.upper()

    # CSV header: Date,Open,High,Low,Close,Adj Close,Volume
    try:
        quotes = query_api(symbol,d)
        quotes.reverse()
        price = round(float(quotes[0]["Adj Close"]), 2)

        return {
                "price": price,
                "symbol": symbol
                }
    except AttributeError:
        return None


def stock_analysis(symbol,d):

    #Analysis: how many day you have to wait to obtain a return of 3.5% or greater?
    symbol = symbol.upper()
    dt_ls = []
    rt_ls = []
    quotes = query_api(symbol,d)

    for i in range(len(quotes)-1):

        pp = float(quotes[i]["Adj Close"])

        for j in range (i+1, len(quotes)):

            ret = float(quotes[j]["Adj Close"])/pp - 1

            if ret > 0.035:
                dt_ls.append(j - i)
                rt_ls.append(ret*100)
                break

    return {"symbol": symbol,
            "dt_Q1": int(quantile(dt_ls, 0.25)),
            "dt_Q3": int(quantile(dt_ls, 0.75)),
            "rt_Q1": round(quantile(rt_ls, 0.25),1),
            "rt_Q3": round(quantile(rt_ls, 0.75),1),
            }


def query_api(symbol, d):

    """Query API"""

    # Prepare API request
    end = datetime.datetime.now(pytz.timezone("US/Eastern"))
    start = end - datetime.timedelta(days=d)

    # Yahoo Finance API
    url = (
        f"https://query1.finance.yahoo.com/v7/finance/download/{urllib.parse.quote_plus(symbol)}"
        f"?period1={int(start.timestamp())}"
        f"&period2={int(end.timestamp())}"
        f"&interval=1d&events=history&includeAdjustedClose=true"
    )

    # Query API
    try:
        response = requests.get(url, cookies={"session": str(uuid.uuid4())}, headers={"User-Agent": "python-requests", "Accept": "*/*"})
        response.raise_for_status()

        # CSV header: Date,Open,High,Low,Close,Adj Close,Volume
        quotes = list(csv.DictReader(response.content.decode("utf-8").splitlines()))

        return quotes

    except (requests.RequestException, ValueError, KeyError, IndexError):
        return None


def results(table):

    type_ls = []   # transaction type (sale/buy)
    tckr_ls = []       # ticker
    qnt_ls = []        # quantity (#stocks)
    dt_ls = []    # transaction date
    pr_ls = []      # stock price

    for i in range(len(table)):
        tckr_ls.append(table[i]["symbol"])
        pr_ls.append(table[i]["price"])
        qnt_ls.append(abs(table[i]["shares"]))
        type_ls.append(table[i]["type"])
        date = str(table[i]["day"]) + "/" + str(table[i]["month"]) + "/" + str(table[i]["year"])
        dt_ls.append(datetime.datetime.strptime(date, "%d/%m/%Y"))

    utckr_ls = [x for i, x in enumerate(tckr_ls) if x not in tckr_ls[:i]] #unique tickers int "tckr" list

    results_ls = []
    for tckr in utckr_ls:     #for each ticker in the unique ticker list

        for j in range(0, len(tckr_ls), 1):    #for each transaction

            if tckr_ls[j] == tckr:

                if type_ls[j] == "sell":
                    spr = pr_ls[j]

                    ls_ppr = []              #store available purchase prices
                    for n in range(0, j, 1):
                        if (type_ls[n] == "buy") and (tckr_ls[n] == tckr):
                            if qnt_ls[n] != 0:
                                ls_ppr.append(pr_ls[n])
                    ls_ppr.sort()

                    cnt = qnt_ls[j]
                    for ppr in ls_ppr:
                        for q in range(0, j, 1):
                            if (ppr == pr_ls[q]) and (tckr_ls[q] == tckr):
                                idx = q

                        if cnt <= qnt_ls[idx]:
                            cnt = qnt_ls[idx] - cnt
                            qnt_ls[idx] = cnt
                            ret = ((spr/ppr) - 1)*100
                            dy = (dt_ls[j] - dt_ls[idx]).days
                            if dy == 0:
                                dy=1
                            results_ls.append({"date": f"{dt_ls[j].month}-{dt_ls[j].day}-{dt_ls[j].year}",
                                               "symbol":tckr, "return":round(ret,1),
                                               "days":dy, "dy_ret":round(ret/dy,1)})
                            break
                        else:
                            cnt = cnt - qnt_ls[idx]
                            qnt_ls[idx] = 0
                            ret = ((spr/ppr) - 1)*100
                            dy = (dt_ls[j] - dt_ls[idx]).days
                            if dy == 0:
                                dy=1
                            results_ls.append({"date": f"{dt_ls[j].month}-{dt_ls[j].day}-{dt_ls[j].year}",
                                               "symbol":tckr,
                                               "return":round(ret,1),
                                               "days":dy, "dy_ret":round(ret/dy,1)})

    return results_ls



def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"
