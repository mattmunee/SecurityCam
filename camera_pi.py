import time
import io
import threading
import picamera
import datetime


class Camera(object):
	streamThread = None  # background thread that reads frames from camera
	recordThread = None
	saveThread = None
	frame = None  # current frame is stored here by background thread
	last_access = 0  # time of last client access to the camera
	camera = None
	streamPort = 0
	filePort = 2
	keepRecording = False
	circStream = None
	
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
		Camera.circStream = picamera.PiCameraCircularIO(Camera.camera,size = None, seconds = 10,splitter_port = Camera.filePort)
		
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
		if Camera.recordThread is None:
			Camera.keepRecording = True
			Camera.recordThread = threading.Thread(target = Camera._recordThread)
			Camera.recordThread.start()	
		time.sleep(2)
		if Camera.saveThread is None:
			Camera.saveThread = threading.Thread(target = Camera._writeThread)
			Camera.saveThread.start()

	def stopRecording(self):
		print 'stopRecording'
		Camera.keepRecording = False
		
	@staticmethod
	def writeVideo(filename):
		print 'writeVideo'
		with Camera.circStream.lock:
			stream = Camera.circStream
		for frame in stream.frames:
			if frame.frame_type == picamera.PiVideoFrameType.sps_header:
				stream.seek(frame.position)
				break
		with io.open(filename,'wb') as output:
			output.write(stream.read())
	
	@classmethod
	def _recordThread(cls):
		print '_recordThread'
		cls.camera.start_recording(cls.circStream,format = 'h264', resize = None, splitter_port = cls.filePort)
		while(cls.keepRecording):
			cls.camera.annotate_text = datetime.datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
			cls.camera.wait_recording(0.5,splitter_port = cls.filePort)
			print 'recording'
		cls.camera.stop_recording(splitter_port = cls.filePort)
		print 'about to write'
		cls.writeVideo('StoppedRecording.h264')
		
	@classmethod
	def _writeThread(cls):
		print '_writeThread'
		while cls.keepRecording:
			time.sleep(10)
			print 'begin write'
			Camera.writeVideo('CurrentVideo.h264')
			print 'write end'
