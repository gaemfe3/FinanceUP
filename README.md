# Searching keywords in PDFs
    #### Video Demo:  <https://youtu.be/lbLe7EygxIU>
    #### Description:

    The goal of this web-based application is to simulate a stock exchange. The following explains how it works:

    The web application has been developed using Flask, Javascript and SQLite. It supports registration, login, logout, password change, search for current and historical quotes (through IEX API), cash deposit, purchase and sale of shares, visualization of returns, statistical analysis of the performance of shares of interest and visualization of purchase and sale history,

    The main page invites you to log in. If you do not have an account, you will find a button in the navigation bar to register. If the account you create already exists, the app will let you know (showing you a message on the same page). In the same way, it will let you know if the username or password is entered incorrectly when logging in.

    When you have logged in correctly you will see your portfolio (initially empty). You'll also see the amount of cash on hand and a total that represents the valuation of your assets (in cash or stock at the time of purchase).
    Once you've bought a stock you'll see it in a table in your portfolio along with a form to buy more or sell it.

    After logging in you can see a navigation bar with the following options:

    -Quote: look for the price of the stock you want. If the searched action does not exist you will see an error message. Otherwise you will see the current share price and a historical graph (10 years of closing prices).

    -Buy: Buy shares indicating their symbol and the desired amount. If you press the "buy" button without having filled out these fields, an error message will appear on the same page. An error message also appears if the symbol does not exist or the number of shares is incorrect (excess or negative).

    -Sell: sell shares indicating their symbol (in a droplist) and the desired amount. If you press the "sell" button without having filled out these fields, an error message will appear on the same page. An error message also appears if the symbol does not exist or the number of shares is incorrect (excess or negative).

    -Deposit: deposit the amount of fictitious money you want by completing the field with a number greater than zero, if not you will get an error message.

    -History: in this section you can see a record of all the purchases and sales you have made as well as the change in price and filter by date. The app paints changes greater than 3.5% in yellow, suggesting that perhaps (depending on the number of days that have passed) it is an appropriate time to sell said shares.

    -Analysis: in this section you can do a statistical analysis by introducing the symbol of the action of interest. The results Q1 and Q3 (the first and third quartiles) of the waiting time to obtain a return greater than 3.5%. The Q1 and Q3 of the return obtained in said period is also shown.

    -Returns: in this section you can view the returns you have obtained when selling your shares and filter by date. Total performance, days to sale, and daily return.

    -Account: in this section you can change your password. You will need to enter your current password and your new password twice. If you do not enter the data correctly, an error message will appear.

    _Logout: just click and log out. It will redirect you to the page to log in.








