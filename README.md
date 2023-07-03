Для деплою на render.com:
в requirements додати gunicorn. також додав бібліотеку yfinance, просто не побачило при білдінгу з імпорту.
стартова команда "gunicorn application:app" (як розумію: application - стартова програма на пітоні)