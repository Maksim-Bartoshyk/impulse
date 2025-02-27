# This is the main sript for running the program
# Navigate to this file from the teminal and type python3 run.py

import functions as fn
import webbrowser
import logging
from threading import Timer
import launcher
from server import app
import warnings

warnings.filterwarnings('ignore')

# The following three lines limit output to errors
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Define default `8050` port
port = 8050 
# Application must be started from (__main__)
if __name__ == '__main__':
    Timer(1, fn.open_browser(port)).start();
    app.run_server(debug=False, threaded=True, port=port)