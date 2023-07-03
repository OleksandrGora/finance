import yfinance as yf

stock = yf.Ticker("ABC")
# price = stock.info['currentPrice']
# print(price)

# quote = stock.info()
print(stock.info())#["shortName"], float(quote["currentPrice"]), quote["symbol"])
