__author__ = "Andrew Beck"
__copyright__ = "Copyright (C) 2019 Andrew Beck"
__license__ = "GNU General Public License v3"
__version__ = "0.1"


# This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

import multiprocessing
import time
import logging
import logging.handlers
import os

# As a multiprocess Python script is hard to debug, but you can use pudb.remote
# You will need to import the pudb.remote module and set a breakpoint in code with
#from pudb.remote import set_trace
#set_trace(term_size=(80, 24))
# Then telnet to the port shown on screen

class Log_listener(multiprocessing.Process):
    """ A class to recieve the log messages from other units
    """
    def __init__(self, *, config, log_queue):
        """
        Initialise the log_listener class

        Keyword arguments:
        config -- A ConfigParser object

        log_queue -- A queue object containing a log messages from other units
        """
        super(Log_listener, self).__init__()
        self.config = config
        self.log_queue = log_queue
    
    def run(self):
        print("Logging started\n")

        # Check to the directory for log_filename exist, if not create it
        log_dir = os.path.dirname(self.config['LOGGING']['log_filename'])
        if not os.path.isdir(log_dir):
            # Create all the directories needed
            os.makedirs(log_dir, exist_ok=True)

        # Configure the log listener
        root = logging.getLogger()
        h = logging.handlers.TimedRotatingFileHandler(self.config['LOGGING']['log_filename'], when='midnight', backupCount=int(self.config['LOGGING']['backup_count']))
        f = logging.Formatter('%(asctime)s %(process)d %(processName)-14s %(levelname)-8s %(message)s')
        h.setFormatter(f)
        root.addHandler(h)

        while True:
            try:
                # Block on get so log message is handled as soon as it arrives
                record = self.log_queue.get()
                if record is None:  # We send this as a sentinel to tell the listener to quit.
                    break
                root.handle(record)  # No level or filter logic applied - just do it!
            except Exception:
                import sys, traceback
                print('Whoops! Problem:', file=sys.stderr)
                traceback.print_exc(file=sys.stderr)