from mss import mss
import cv2 as cv
import numpy as np

out = cv.VideoWriter('../images/output.mp4', 0x00000021, 15.0, (1000,570))

with mss() as sct:
  # Part of the screen to capture
  monitor = {"top": 0, "left": 0, "width": 1000, "height": 570}

  while "Screen capturing":
    # Get raw pixels from the screen, save it to a Numpy array
    img = np.array(sct.grab(monitor))
    out.write(img)
    cv.imshow('vid', img)
    # Press "q" to quit
    if cv.waitKey(25) & 0xFF == ord("q"):
      cv.destroyAllWindows()
      break