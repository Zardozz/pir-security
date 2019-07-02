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
import os
import logging
import logging.handlers

# As a multiprocess Python script is hard to debug, but you can use pudb.remote
# You will need to import the pudb.remote module and set a breakpoint in code with
#from pudb.remote import set_trace
#set_trace(term_size=(80, 24))
# Then telnet to the port shown on screen

class Cleanup(multiprocessing.Process):
    """ A class to handle deleting old video and images
    """
    def __init__(self, *, config, log_queue):
        """
        Initialise the cleanup class

        Keyword arguments:
        config -- A ConfigParser object

        log_queue -- A queue object to send log messages to
        """
        super(Cleanup, self).__init__()
        self.config = config
        self.log_queue = log_queue

        self.stoprequest = multiprocessing.Event()

        # Setup logging
        h = logging.handlers.QueueHandler(self.log_queue)  # Just the one handler needed
        self.queue_logger = logging.getLogger(name='Cleanup')
        self.queue_logger.addHandler(h)
        # apply this unit's logging level
        log_level = {'CRITICAL': logging.CRITICAL, 'ERROR': logging.ERROR, 'WARNING': logging.WARNING, 'INFO': logging.INFO, 'DEBUG': logging.DEBUG}
        self.queue_logger.setLevel(log_level[self.config['CLEANUP']['log_level']])
    
    def run(self):
        self.queue_logger.info("Cleanup started")
        print("Cleanup started\n")

        # Loop while not asked to exit
        while not self.stoprequest.is_set():
            notification_out_path = self.config['RECORD']['notification_out_path']
            video_out_path = self.config['RECORD']['video_out_path']
            # Calculate time limit for files
            time_limit = time.time() - (int(self.config['CLEANUP']['days_to_keep'])*60*60*24)
            self.queue_logger.debug(f"time_limit={time_limit}")
            # Check notification_out_path for images that are too old
            oldfiles = [f for f in os.listdir(notification_out_path) if os.path.isfile(os.path.join(notification_out_path, f)) and os.path.splitext(f)[1] == ".jpg" and os.path.getmtime(os.path.join(notification_out_path, f)) < time_limit]
            self.queue_logger.debug(f"oldfiles={oldfiles}")
            # Delete old files
            for f in oldfiles:
                full_f = os.path.join(notification_out_path, f)
                self.queue_logger.info(f"Deleting file={full_f}")
                try:
                    os.remove(full_f)
                except OSError:
                    self.queue_logger.warning(f"Cannot Delete={full_f}")

            # Check video_out_path for video that are too old
            for root, dirs, files in os.walk(video_out_path, topdown=False):
                # Process the files in the directory
                for f in files:
                    if os.path.splitext(f)[1] == ".h264" or os.path.splitext(f)[1] == ".mp4":
                        # check the age
                        full_f = os.path.join(root, f)
                        try:
                            file_time = os.path.getmtime(full_f)
                        except OSError:
                            self.queue_logger.warning(f"Cannot get modification time of File={full_f}")
                            continue

                        if file_time < time_limit:
                            self.queue_logger.info(f"Deleting file={full_f}")
                            try:
                                os.remove(full_f)
                            except OSError:
                                self.queue_logger.warning(f"Cannot Delete File={full_f}")

                # Process the directories to see if any are empty
                for d in dirs:
                    full_d = os.path.join(root, d)
                    if len(os.listdir(full_d)) == 0:
                        # Directory is empty try to delete it
                        self.queue_logger.info(f"Deleting directory={full_d}")
                        try:
                            os.rmdir(full_d)
                        except OSError:
                            self.queue_logger.warning(f"Cannot Delete Directory={full_d}")


            # Go to sleep for a bit so not a tight loop
            # As the record might take up to 1 minute to finish looping every 30 seconds should not delay exit much.
            time.sleep(30)



    def join(self, timeout=None):
        self.queue_logger.info("Cleanup asked to exit")
        self.stoprequest.set()
        super(Cleanup, self).join(timeout)