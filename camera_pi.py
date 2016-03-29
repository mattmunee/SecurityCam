import time
import io
import threading
import picamera
import datetime


class Camera(object):
	streamThread = None  # background thread that reads frames from camera
	frame = None  # current frame is stored here by background thread
	last_access = 0  # time of last client access to the camera
	camera = None
	
	def __init__(self):
		# camera setup
		print '__init__'
		Camera.camera = picamera.PiCamera()
		Camera.camera.resolution = (832, 624)
		Camera.camera.rotation = 270
		Camera.camera.hflip = True
		Camera.camera.vflip = True
		Camera.camera.annotate_background = picamera.Color('black')
		time.sleep(2)
		Camera.camera.start_preview()
		
	def get_frame(self):
		Camera.last_access = time.time()
		if Camera.streamThread is None:
			# start background frame thread
			Camera.streamThread = threading.Thread(target=self._streamThread)
			Camera.streamThread.start()

			# wait until frames start to be available
			while Camera.frame is None:
				time.sleep(0)
		return Camera.frame

	@classmethod
	def _streamThread(cls):
		# let camera warm up
		cls.camera.start_preview()
		time.sleep(2)
		networkStream = io.BytesIO()
		for foo in cls.camera.capture_continuous(networkStream, 'jpeg',
												use_video_port=True):
													 
			# store frame
			networkStream.seek(0)
			cls.camera.annotate_text = datetime.datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
			cls.frame = networkStream.read()

			# reset stream for next frame
			networkStream.seek(0)
			networkStream.truncate()

			# if there hasn't been any clients asking for frames in
			# the last 10 seconds stop the thread
			if time.time() - cls.last_access > 10:
				break
			
		cls.streamThread = None
