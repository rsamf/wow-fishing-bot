# wow-fishing-bot
A fishing bot for World of Warcraft created with OpenCV. 

## How it Works
This program captures a portion of the screen and simulates mouse and
keyboard events. No GPU needed since this doesn't use object detection. 
It detects the fishing bobber using [template matching](https://docs.opencv.org/master/d4/dc6/tutorial_py_template_matching.html),
and then clicks on it once there are enough white pixels, which is perceived as a splash. This is possible with these simple 
methods because the fishing bobber has a predicable rotation and the image of the splash is always expected to have brighter 
pixels in grayscale. 

## How to Use
You may follow the steps below. You can also watch a demo video here: [coming soon...]()
#### Steps
1. Turn liquid quality to ultra.
1. Find a body of water that is not reflecting the sun.
1. Run the program as administrator.
1. Look in first person, and start drawing the border to the area of interest. This area is the body of water where the fishing bobber may appear.
 You will draw it by placing at least 3 points that define the shape, and these points are placed when the cursor hasn't 
 moved for 1 second. Leaving the cursor at the ending point will finish the shape.
1. Now, point to the casting ability
1. It will start fishing on its own, but you're not done...
1. On the first round of fishing, it won't know where to loot, so hold the cursor at the appropriate when your loot pops up.
1. Now, you're done!

Note: Once a splash is detected, there is an added click delay that ranges .5 - 1 seconds. This is
intended to show human-like reaction to any admin that may suspect you for botting. Also, I wouldn't fish for more
than a couple of hours.

## Why?
Because World of Warcraft fishing mechanism is pretty simple, this can easily be automated with a program. I decided 
to take this challenge on as an educational opportunity and to practice my skills with OpenCV. If you decide to use this 
program, use at your own risk because I believe it does not abide with their rules, so if you get banned it's not on me.
I think I had an encounter with an admin as I was working and testing this program, but since I was supervising it, I was able to 
take command and show human-like reactions.

## Todo:
- ~~Find best bob location, continually (not on first frame)~~
- Create programmatic way to capture new templates
- ~~Create documentation: how to use, how it works, etc...~~
- Create demo video
- If splash wasn't detected for casting time length, then recast. This means it fails. <- Statistic opportunity here.
