# import RPi.GPIO as GPIO
import cv2
import time
from datetime import datetime
from flask import Flask, render_template_string, Response, request

app = Flask(__name__)

# Set up camera
global filename
camera = cv2.VideoCapture(0)
time.sleep(3)  # Warm up camera
frame_width = int(camera.get(3))
frame_height = int(camera.get(4))
video_writer = None
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
filename = None
start_record = False
file_set = False
stop_rec = 30

# Set up servo motor
# GPIO.setmode(GPIO.BOARD)
# GPIO.setup(11, GPIO.OUT)
# pwm = GPIO.PWM(11, 50)
# pwm.start(0)

# Set up motion detection
motion_detector = cv2.createBackgroundSubtractorMOG2(history=100, varThreshold=50, detectShadows=False)

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
        <img src="{{ url_for('video_feed') }}" style="width: 1024px; height: 768px;">
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
    global filename
    i = 0
    start_movement_time = 0
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
        _, thresh_bin = cv2.threshold(diff_blur, 25, 255, cv2.THRESH_BINARY)

        # to find contours
        contours, hierarchy = cv2.findContours(thresh_bin, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        if contours != () and filename is None:
            print("New name")
            start_movement_time = time.time()
            filename = datetime.now().strftime('recordings\\%Y-%m-%d_%H-%M-%S.mp4')
            video_writer = cv2.VideoWriter(filename, 0x7634706d, 70, (frame_width, frame_height))
            print("Start")
        elif contours == () and (time.time() - start_movement_time) >= stop_rec and i >= 200:
            video_writer.release()
            start_movement_time = 0
            filename = None
            print("Stop")
            i = 0
        elif contours == () and (time.time() - start_movement_time) >= stop_rec and filename is not None:
            print(i)
            video_writer.write(img_1)
            i = i + 1  # frame has been made in the frame
            # to draw the bounding box when the motion is detected

        for contour in contours:
            if cv2.contourArea(contour) >= 300:
                cv2.rectangle(img_1, (x, y), (x + w, y + h), (0, 255, 0), 2)
            if filename is not None:
                video_writer.write(img_2)
            i = 0
            x, y, w, h = cv2.boundingRect(contour)

        # display the output
        ret, jpeg = cv2.imencode('.jpg', img_1)
        frame = jpeg.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


# Video feed endpoint
@app.route('/video_feed')
def video_feed():
    return Response(gen(),
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
video_writer.release()
camera.release()
# cv2.destroyAllWindows()
# pwm.stop()
# GPIO.cleanup()
