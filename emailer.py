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
import smtplib
import ssl
from email.message import EmailMessage
import logging
import logging.handlers
import os

# As a multiprocess Python script is hard to debug, but you can use pudb.remote
# You will need to import the pudb.remote module and set a breakpoint in code with
#from pudb.remote import set_trace
#set_trace(term_size=(80, 24))
# Then telnet to the port shown on screen

class Emailer(multiprocessing.Process):
    """ A class to Email the image captured when the pir is triggered
    """
    def __init__(self, *, config, log_queue, input_queue):
        """
        Initialise the Emailer class

        Keyword arguments:
        config -- A ConfigParser object

        log_queue -- A queue object to send log messages to

        input_queue -- A queue object containing the location of an image to email
        """
        super(Emailer, self).__init__()
        self.config = config
        self.log_queue = log_queue
        self.input_queue = input_queue

        self.stoprequest = multiprocessing.Event()

        # Setup logging
        h = logging.handlers.QueueHandler(self.log_queue)  # Just the one handler needed
        self.queue_logger = logging.getLogger(name='Emailer')
        self.queue_logger.addHandler(h)
        # apply this unit's logging level
        log_level = {'CRITICAL': logging.CRITICAL, 'ERROR': logging.ERROR, 'WARNING': logging.WARNING, 'INFO': logging.INFO, 'DEBUG': logging.DEBUG}
        self.queue_logger.setLevel(log_level[self.config['EMAILER']['log_level']])
    
    def run(self):
        self.queue_logger.info("Emailer started")
        print("Emailer started\n")
        input_queue_message = ""

        # Loop while not asked to exit
        while not self.stoprequest.is_set():
            # Handle if a video conversion is requested
            try:
                input_queue_message = self.input_queue.get(block=False)
            except queue.Empty:
                pass

            if input_queue_message != "":
                self.queue_logger.info(f"Emailing {input_queue_message}")
                # Create the container email message.
                msg = EmailMessage()
                msg['Subject'] = 'PIR Image'
                msg['From'] = self.config['EMAILER']['From']
                msg['To'] = self.config['EMAILER']['To']
                msg.preamble = 'PIR Image'

                # Add image as attachment
                with open(input_queue_message, 'rb') as fp:
                    img_data = fp.read()
                    filename = os.path.basename(input_queue_message)
                    msg.add_attachment(img_data, maintype='image', subtype='jpg', filename=filename)

                # Send the email via SMTP server.
                try:
                # Create a secure SSL context
                    context = ssl.create_default_context()

                    server = smtplib.SMTP(self.config['EMAILER']['Server'],int(self.config['EMAILER']['Port']))
                    server.ehlo()
                    server.starttls(context=context)
                    server.ehlo()
                    server.login(self.config['EMAILER']['User'], self.config['EMAILER']['Password'])
                    server.send_message(msg)
                except Exception as e:
                    # Log any Exception
                    self.queue_logger.error(f"{e}")
                finally:
                    server.quit() 

                # Clear the message
                input_queue_message = ""


            # Go to sleep for a bit so not a tight loop
            time.sleep(0.1)



    def join(self, timeout=None):
        self.queue_logger.info("Emailer asked to exit")
        self.stoprequest.set()
        super(Emailer, self).join(timeout)