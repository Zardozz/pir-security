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

import picamera
import multiprocessing
import queue
import datetime as dt
import os
import logging
import logging.handlers

# As a multiprocess Python script is hard to debug, but you can use pudb.remote
# You will need to import the pudb.remote module and set a breakpoint in code with
#from pudb.remote import set_trace
#set_trace(term_size=(80, 24))
# Then telnet to the port shown on screen

class Record(multiprocessing.Process):
    """ A class to handle all camera based recording actions
        Video files are 1 minute long and grouped by hour and by date in ISO format date
        e.g
        2019-01-01/01/01.h264
        2019-01-01/01/02.h264
        etc

        Note this rquiores Raspian buster for Python 3.7 or higher for fix for Python Issue29519
    """
    def __init__(self, *, config, log_queue, input_queue, notification_output_queue, video_output_queue):
        """
        Initialise the record class

        Keyword arguments:
        config -- A ConfigParser object

        log_queue -- A queue object to send log messages to

        input_queue -- A queue object containing command message strings
        e.g generate_notify_file (this will be a still image or short video)

        notification_output_queue -- A queue object containing the full path of generated notification files
        e.g  /tmp/notify.jpg

        video_output_queue -- A queue object containing the full path of generated video files
        e.g  /tmp/2019-01-01/02/03.h264
        """
        super(Record, self).__init__()
        self.config = config
        self.log_queue = log_queue
        self.input_queue = input_queue
        self.notification_output_queue = notification_output_queue
        self.video_output_queue = video_output_queue

        self.stoprequest = multiprocessing.Event()

        # Setup logging
        h = logging.handlers.QueueHandler(self.log_queue)  # Just the one handler needed
        self.queue_logger = logging.getLogger(name='Record')
        self.queue_logger.addHandler(h)
        # apply this unit's logging level
        log_level = {'CRITICAL': logging.CRITICAL, 'ERROR': logging.ERROR, 'WARNING': logging.WARNING, 'INFO': logging.INFO, 'DEBUG': logging.DEBUG}
        self.queue_logger.setLevel(log_level[self.config['RECORD']['log_level']])
    
    def run(self):
        self.queue_logger.info("Recording started")
        print("Recording started\n")

        # Check video_out_path exists and if not check that it can be created
        if not os.path.isdir(self.config['RECORD']['video_out_path']):
            # Create all the directories needed
            os.makedirs(self.config['RECORD']['video_out_path'], exist_ok=True)
        
        # Check notification_out_path exists and if not check that it can be created
        if not os.path.isdir(self.config['RECORD']['notification_out_path']):
            # Create all the directories needed
            os.makedirs(self.config['RECORD']['notification_out_path'], exist_ok=True)

        camera = picamera.PiCamera(sensor_mode=4, resolution='1640x1232', framerate=25)
        camera.hflip=bool(self.config['RECORD']['hflip'])
        camera.vflip=bool(self.config['RECORD']['vflip'])
        input_queue_message = ""
        while not self.stoprequest.is_set():
            # Get the current number of seconds so the recording can be aligned to the start of the minute
            date_time = dt.datetime.now()
            current_minute = date_time.minute
            self.queue_logger.info(f"current_minute={current_minute}")
            
            # Make right right directories
            current_hour_path = os.path.join(self.config['RECORD']['video_out_path'], date_time.strftime('%Y-%m-%d/%H'))
            os.makedirs(current_hour_path, exist_ok=True)
            h264_video_output_path = os.path.join(current_hour_path, date_time.strftime('%M.h264'))
            camera.start_recording(h264_video_output_path, bitrate=0, quality=int(self.config['RECORD']['video_quality']))

            # Loop to the end of a minute
            # Covers not starting on second 00 and if the wait_recording drifts a bit
            while dt.datetime.now().minute == current_minute:
                camera.annotate_background = picamera.Color('black')
                camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                # Handle if an image capture is requested
                try:
                    input_queue_message = self.input_queue.get(block=False)
                except queue.Empty:
                    pass
                if input_queue_message == "generate_notify_file":
                    output_path = os.path.join(self.config['RECORD']['notification_out_path'], dt.datetime.now().strftime('%Y-%m-%d-%H-%M-%S.jpg'))
                    camera.capture(output_path, use_video_port=True, quality=int(self.config['RECORD']['image_quality']))
                    input_queue_message = ""

                    # Add to notification_output_queue
                    self.notification_output_queue.put(output_path)

                # Wait
                camera.wait_recording(0.1)

            # Stop recording so ready for next minute
            camera.stop_recording()

            # Add to video_output_queue so the video gets converted to mp4
            self.video_output_queue.put(h264_video_output_path)


    def join(self, timeout=None):
        self.queue_logger.info("Recorder asked to exit")
        self.stoprequest.set()
        super(Record, self).join(timeout)