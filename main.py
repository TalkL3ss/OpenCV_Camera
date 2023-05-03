#import RPi.GPIO as GPIO
import cv2
import time
from datetime import datetime
from flask import Flask, render_template_string, Response, request

app = Flask(__name__)

# Set up camera
global filename
camera = cv2.VideoCapture(1)
time.sleep(2) # Warm up camera
frame_width = int(camera.get(3))
frame_height = int(camera.get(4))
video_writer = None
fourcc = cv2.VideoWriter_fourcc(*'XVID')
filename = None
start_record = False
file_set = False


# Set up servo motor
#GPIO.setmode(GPIO.BOARD)
#GPIO.setup(11, GPIO.OUT)
#pwm = GPIO.PWM(11, 50)
#pwm.start(0)

# Set up motion detection
motion_detector = cv2.createBackgroundSubtractorMOG2(history=100, varThreshold=500,detectShadows=True)

# Set up video writer
recording_start_time = None

# Main route
@app.route('/')
def index():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Video Stream</title>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <style>
        #video-stream {
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <div id="video-stream">
        <img src="{{ url_for('video_feed') }}" style="width: 640px; height: 480px;">
    </div>
    <div id="servo-control">
        <input type="range" min="0" max="180" value="90" class="slider" id="servo-angle">
    </div>
    <button id="record" onclick="record_on_motion()">Record on Motion</button>
    <script>
        function control_servo() {
            var angle = $('#servo-angle').val();
            $.ajax({
                url: '/servo',
                type: 'POST',
                data: { angle: angle },
                success: function(response) {
                    console.log(response);
                },
                error: function(error) {
                    console.log(error);
                }
            });
        }

        function record_on_motion() {
            $.ajax({
                url: '/record',
                type: 'GET',
                success: function(response) {
                    console.log(response);
                },
                error: function(error) {
                    console.log(error);
                }
            });
        }

        $(document).ready(function() {
            $('#servo-angle').on('input', function() {
                control_servo();
            });
        });
    </script>
</body>
</html>""")

# Video feed route
def gen():
    print("I'm Here")
    global recording_start_time, start_record
    start_record=False
    while True:
        ret, frame = camera.read()
        if not ret:
            break
        else:
            # Apply motion detection
            fg_mask = motion_detector.apply(frame)
            fg_mask = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)[1]
            fg_mask = cv2.erode(fg_mask, None, iterations=2)
            fg_mask = cv2.dilate(fg_mask, None, iterations=2)
            contours, hierarchy = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for c in contours:
                # Only record video when motion is detected
                if recording_start_time is None:
                    print('Motion detected')
                    if not start_record:
                      filename = datetime.now().strftime('recordings\%Y-%m-%d_%H-%M.mp4')
                      start_record=True
                    video_writer = cv2.VideoWriter(filename, fourcc, 20.0, (frame_width, frame_height))
                    recording_start_time = time.time()
                # Draw bounding box around moving object
                (x, y, w, h) = cv2.boundingRect(c)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                video_writer.write(frame)
            # Save video for 10 seconds after motion stops
            if recording_start_time is not None and time.time() - recording_start_time >= 10:
                print('Motion stopped')
                video_writer.release()
                recording_start_time = None
                start_record=False
            # Convert frame to JPEG and yield it to the video feed
            ret, jpeg = cv2.imencode('.jpg', frame)
            frame = jpeg.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

def gen2():
 global filename
 i = 0
 start_movment_time=0
 while camera.isOpened():
    # to read frame by frame
     _, img_1 = camera.read()
     _, img_2 = camera.read()

    # find difference between two frames
     diff = cv2.absdiff(img_1, img_2)

    # to convert the frame to grayscale
     diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

    # apply some blur to smoothen the frame
     diff_blur = cv2.GaussianBlur(diff_gray, (5, 5), 0)

    # to get the binary image
     _, thresh_bin = cv2.threshold(diff_blur, 20, 255, cv2.THRESH_BINARY)

    # to find contours
     contours, hierarchy = cv2.findContours(thresh_bin, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
     if contours == ():
      #print(i)
      i=i+1
      if i >= 6:
       if start_movment_time != 0 and (time.time() - start_movment_time) >= 30 and filename is not None:
         video_writer.release()
         start_movment_time = 0
         start_record=False
         filename = None
         print("Stop")
       elif start_movment_time !=0 and filename is None:
          #start_record=False
          #file_set = True
          filename = datetime.now().strftime('recordings\%Y-%m-%d_%H-%M-%S.avi')
          video_writer = cv2.VideoWriter(filename, fourcc, 100, (frame_width, frame_height))
          print("Start")
       elif filename is not None:
          i=0	   
      elif i < 20 and start_movment_time != 0 and (time.time() - start_movment_time) < 30 and filename is not None:
       video_writer.write(img_1)
	  #print(contours)
      #i=0

       
    # to draw the bounding box when the motion is detected
     for contour in contours:
         if cv2.contourArea(contour) >= 1:
             cv2.rectangle(img_1, (x, y), (x+w, y+h), (0, 255, 0), 2)
         if filename is not None:
           video_writer.write(img_2)
         if start_movment_time ==0:
          start_movment_time=time.time()
          
         #print("i=0")
         i=0
         x, y, w, h = cv2.boundingRect(contour)

    # cv2.drawContours(img_1, contours, -1, (0, 255, 0), 2)
    # display the output
     #cv2.imshow("Detecting Motion...", img_1)
     ret, jpeg = cv2.imencode('.jpg', img_1)
    # if start_movment_time != 0:
	  
     frame = jpeg.tobytes()
     yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


# Video feed endpoint
@app.route('/video_feed')
def video_feed():
    return Response(gen2(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# Servo control endpoint
@app.route('/move', methods=['POST'])
def move():
    duty_cycle = float(request.form['slider']) / 10.0
    pwm.ChangeDutyCycle(duty_cycle)
    return 'ok'

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

# Clean up when done
camera.release()
#cv2.destroyAllWindows()
#pwm.stop()
#GPIO.cleanup()
