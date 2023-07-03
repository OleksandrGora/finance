Для деплою на render.com:
в requirements додати gunicorn.
Також додав бібліотеку yfinance, без цього не побачило при білдінгу просто при наявності інструкції import.
Стартова команда "gunicorn application:app" (application - стартова програма на пітоні, app - завжди.)