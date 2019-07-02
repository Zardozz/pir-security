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

try:
    import RPi.GPIO as GPIO
except RuntimeError:
    print("Error importing RPi.GPIO!  This is probably because you need superuser privileges.  You can achieve this by using 'sudo' to run your script")

# As a multiprocess Python script is hard to debug, but you can use pudb.remote
# You will need to import the pudb.remote module and set a breakpoint in code with
#from pudb.remote import set_trace
#set_trace(term_size=(80, 24))
# Then telnet to the port shown on screen

class Pir(multiprocessing.Process):
    """ A class to handle all pir based actions
        Adds a message to the record input queue to trigger it to generate an image
    """
    def __init__(self, *, config, log_queue, output_queue):
        """
        Initialise the pir class

        Keyword arguments:
        config -- A ConfigParser object

        log_queue -- A queue object to send log messages to

        output_queue -- A queue object containing a message for the record class to generate a image when the pir sensor is triggered
        """
        super(Pir, self).__init__()
        self.config = config
        self.log_queue = log_queue
        self.output_queue = output_queue

        self.stoprequest = multiprocessing.Event()

        # Setup logging
        h = logging.handlers.QueueHandler(self.log_queue)  # Just the one handler needed
        self.queue_logger = logging.getLogger(name='Pir')
        self.queue_logger.addHandler(h)
        # apply this unit's logging level
        log_level = {'CRITICAL': logging.CRITICAL, 'ERROR': logging.ERROR, 'WARNING': logging.WARNING, 'INFO': logging.INFO, 'DEBUG': logging.DEBUG}
        self.queue_logger.setLevel(log_level[self.config['PIR']['log_level']])
    
    def run(self):
        self.queue_logger.info("PIR started")
        print("PIR started\n")
        
        # Setup GPIO
        GPIO.setmode(GPIO.BOARD)
        self.PIR = int(self.config['PIR']['pin'])
        GPIO.setup(self.PIR, GPIO.IN, GPIO.PUD_DOWN)

        # Loop until PIR indicates nothing is happening
        while GPIO.input(self.PIR)==1:
            pass
        self.queue_logger.info("PIR Sensor Ready")
        
        # add rising edge detection on a channel but only once per minute detection
        GPIO.add_event_detect(self.PIR, GPIO.RISING, bouncetime=int(self.config['PIR']['min_trigger_seconds'])*1000)  

        # Loop while not asked to exit
        while not self.stoprequest.is_set():
            # Check if PIR was triggered
            if GPIO.event_detected(self.PIR):
                self.queue_logger.info("PIR Sensor Triggered")
                if not os.path.isfile(self.config['PIR']['disable']):
                    # Add message to the output queue
                    self.output_queue.put("generate_notify_file")
                else:
                    self.queue_logger.info("PIR Sensor real time disabled")



            # Go to sleep for a bit so not a tight loop
            time.sleep(0.1)

        # Asked to exit so do GPIO cleanup
        GPIO.cleanup()



    def join(self, timeout=None):
        self.queue_logger.info("PIR asked to exit")
        self.stoprequest.set()
        super(Pir, self).join(timeout)