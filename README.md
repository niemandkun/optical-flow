# Optical flow

Control vehicle to avoid obstacles using webcam

### How to

* Run `python3 capture.py`
* Run `python3 game.py`
* If you only knew the power of the dark side
* ...
* Enjoy!

### Content

capture.py - detects optical flow and sends its average magnitude via socket
game.py - receives magnitude from socket and uses it to control vehicle
