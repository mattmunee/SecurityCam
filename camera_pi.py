import time
import io
import threading
import picamera
import datetime
import os
import datetime


class Camera(object):
	streamThread = None  # background thread that reads frames from camera
	recordThread = None
	frame = None  # current frame is stored here by background thread
	last_access = 0  # time of last client access to the camera
	camera = None
	streamPort = 0
	filePort = 2
	keepRecording = False
	circStream = None
	logDirectory = "./ImageLog"
	frameRateHz = 10;
	videoLengthSec = 86400;
	mostNumFrames = 0;
	
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
		Camera.mostNumFrames = Camera.frameRateHz*Camera.videoLengthSec
		
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
		for foo in cls.camera.capture_continuous(networkStream, 'jpeg',use_video_port=True,resize=None,splitter_port=cls.streamPort):
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


	def startRecording(self):
		print 'start recording'
		if not os.path.exists(self.logDirectory):
			os.makedirs(self.logDirectory)
		else:
			filelist = os.listdir(self.logDirectory)
			for f in filelist:
				os.remove(os.path.join(self.logDirectory,f))
		if Camera.recordThread is None:
			Camera.keepRecording = True
			Camera.recordThread = threading.Thread(target = Camera._recordThread)
			Camera.recordThread.start()	
		time.sleep(2)

	def stopRecording(self):
		print 'stopRecording'
		Camera.keepRecording = False
	
	@classmethod
	def _recordThread(cls):
		print '_recordThread'
		lastFrameTime = time.time();
		oldestFrameName = None
		oldestFrameTime = lastFrameTime
		numFrames = 0
		while(cls.keepRecording):
			curTime = time.time()
			if curTime-lastFrameTime > 1/cls.frameRateHz:
				dt = datetime.datetime.now();
				cls.camera.annotate_text = dt.strftime('%Y-%m-%d %I:%M:%S %p')
				nameString = "still_%02d%02d%02d_%02d-%02d-%02d-%05d.jpg" % (dt.year,dt.month,dt.day,dt.hour,dt.minute,dt.second,dt.microsecond)
				filename = os.path.join(cls.logDirectory,nameString)
				cls.camera.capture(filename,'jpeg', use_video_port = True,resize = None, splitter_port = cls.filePort)
				lastFrameTime = time.time()
				numFrames = numFrames+1;
				if numFrames>cls.mostNumFrames:
					filelist = sorted([os.path.join(cls.logDirectory,f) for f in os.listdir(cls.logDirectory)],key = os.path.getctime)
					os.remove(filelist[0])
					numFrames = numFrames-1;
				print filename
			else:
				time.sleep(0.005)
				


