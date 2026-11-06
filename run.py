import threading
import webbrowser

from platform_app.http_server import run


if __name__ == "__main__":
    threading.Timer(0.8, lambda: webbrowser.open("http://127.0.0.1:8000")).start()
    run()
