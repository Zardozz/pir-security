#!/usr/bin/python3

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
import signal
import sys
import configparser
import logging
import logging.handlers
import time

# As a multiprocess Python script is hard to debug, but you can use pudb.remote
# You will need to import the pudb.remote module and set a breakpoint in code with
#from pudb.remote import set_trace
#set_trace(term_size=(80, 24))
# Then telnet to the port shown on screen

import record
import log_listener
import mp4_convert

def signal_handler(sig, frame):
    # Wait for the recording and logging units to complete
    record_unit.join()
    # Give mp4_unit time to convert last video
    time.sleep(5)
    mp4_unit.join()
    # Send a None message to logger as this has a different method to shutdown
    log_queue.put_nowait(None)
    logging_unit.join()
    print("Exited cleanly")
    sys.exit(0)

if __name__ == '__main__':
    # Read the config file
    config = configparser.ConfigParser()
    config.read('security.ini')

    # Set SIGINT to be ignored before child units are created
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    # Create logging queue
    log_queue = multiprocessing.Queue()
    # Create logging unit
    logging_unit = log_listener.Log_listener(config=config, log_queue=log_queue)
    # Start this early to capture all logs
    logging_unit.start()

    # Create input and output queues to communicate to record unit
    record_input = multiprocessing.Queue()
    record_notification_output = multiprocessing.Queue()
    record_video_output = multiprocessing.Queue()

    # Create record unit
    record_unit = record.Record(config=config, log_queue=log_queue, input_queue=record_input, notification_output_queue=record_notification_output, video_output_queue=record_video_output)

    # Create the Mp4_convert unit
    mp4_unit = mp4_convert.Mp4_convert(config=config, log_queue=log_queue, input_queue=record_video_output)

    # Start all units
    record_unit.start()
    mp4_unit.start()

    # Add signal handler back
    signal.signal(signal.SIGINT, signal_handler)
    print("Press Ctrl+C to cleanly exit (this could take up to a minute to happen)")
    signal.pause()
