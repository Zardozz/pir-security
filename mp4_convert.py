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
import queue
import time
import re
import subprocess
import os
import logging
import logging.handlers

# As a multiprocess Python script is hard to debug, but you can use pudb.remote
# You will need to import the pudb.remote module and set a breakpoint in code with
#from pudb.remote import set_trace
#set_trace(term_size=(80, 24))
# Then telnet to the port shown on screen

class Mp4_convert(multiprocessing.Process):
    """ A class to handle the convertion of h264 files to mp4
        This makes them easier to view
        It removes the h264 files when done
    """
    def __init__(self, *, config, log_queue, input_queue):
        """
        Initialise the mp4_convert class

        Keyword arguments:
        config -- A ConfigParser object

        log_queue -- A queue object to send log messages to

        input_queue -- A queue object containing a message from the record class to the location of a newly generated h264 file to convert
        """
        super(Mp4_convert, self).__init__()
        self.config = config
        self.log_queue = log_queue
        self.input_queue = input_queue

        self.stoprequest = multiprocessing.Event()

        # Setup logging
        h = logging.handlers.QueueHandler(self.log_queue)  # Just the one handler needed
        self.queue_logger = logging.getLogger(name='Mp4_convert')
        self.queue_logger.addHandler(h)
        # apply this unit's logging level
        log_level = {'CRITICAL': logging.CRITICAL, 'ERROR': logging.ERROR, 'WARNING': logging.WARNING, 'INFO': logging.INFO, 'DEBUG': logging.DEBUG}
        self.queue_logger.setLevel(log_level[self.config['MP4_CONVERT']['log_level']])
    
    def run(self):
        self.queue_logger.info("MP4 convert started")
        print("MP4 convert started\n")
        input_queue_message = ""

        # Loop while not asked to exit
        while not self.stoprequest.is_set():
            # Handle if a video conversion is requested
            try:
                input_queue_message = self.input_queue.get(block=False)
            except queue.Empty:
                pass

            if input_queue_message != "":
                self.queue_logger.info(f"Converting {input_queue_message}")
                # Work out the output file name by replacing the .h264 extension
                output_file_name = re.sub("\.h264$","\.mp4", input_queue_message)

                # Call out to external utility to convert the h264 file to an MP4 file
                command = "MP4Box -quiet -noprog -add {} {}".format(input_queue_message, output_file_name)
                try:
                     output = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
                except subprocess.CalledProcessError as err:
                    self.queue_logger.error(f"cmd:{err.cmd} output:{err.output}")
                else:
                    # Remove original file as conversion was successful
                    self.queue_logger.debug(f"Deleting {input_queue_message}")
                    try:
                        os.remove(input_queue_message)
                    except OSError:
                        self.queue_logger.warning(f"Cannot Delete={f}")

                # Clear the message
                input_queue_message = ""

            # Go to sleep for a bit so not a tight loop
            time.sleep(0.1)



    def join(self, timeout=None):
        self.queue_logger.info("Mp4_convert asked to exit")
        self.stoprequest.set()
        super(Mp4_convert, self).join(timeout)