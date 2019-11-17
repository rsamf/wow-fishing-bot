# wow-fishing-bot
A fishing bot for World of Warcraft created with OpenCV. This program captures a portion of the screen and simulates mouse and
keyboard events. No GPU needed since this doesn't use object detection. 
It detects the fishing bobber using [template matching](https://docs.opencv.org/master/d4/dc6/tutorial_py_template_matching.html),
and then clicks on it once there are enough white pixels, which is perceived as a splash.

## How to Use
coming soon...

## Todo:
- ~~Find best bob location, continually (not on first frame)~~
- Create programmatic way to capture new templates
- Create documentation: how to use, how it works, etc...
