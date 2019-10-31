import time, sys
import cv2 as cv
import numpy as np
from mss import mss

METHOD = cv.TM_CCOEFF_NORMED

def search(settings):
  monitor = settings.get_monitor()
  threshold = settings.threshold
  mask = np.zeros((monitor["height"],monitor["width"]), np.uint8)
  cv.fillConvexPoly(mask, settings.area_of_interest, 255)

  with mss() as sct:
    # Part of the screen to capture
    while "Screen capturing":
      if cv.waitKey(25) & 0xFF == ord('q'):
        break
      img_color = cv.cvtColor(np.array(sct.grab(monitor)), cv.COLOR_BGRA2GRAY)
      img = cv.Canny(img_color, 60, 140)
      img = cv.bitwise_and(img, mask)
      # cv.imshow('canny', img)
      highest_val = 0
      target = None
      for template in settings.templates:
        start_time = time.time()
        h, w = template.shape
        res = cv.matchTemplate(img, template, METHOD)
        # set new position
        _, max_val, _, max_loc = cv.minMaxLoc(res)
        if max_val > highest_val:
          highest_val = max_val
          target = max_loc
        # cv.rectangle(img_color, max_loc, (max_loc[0] + w, max_loc[1] + h), 255, 2)
        # cv.imshow("Result",  img_color)
        # print("fps %f" % (1/ (time.time()-start_time)))
      if highest_val > threshold:
        center = (int(target[0] + w/2), int(target[1] + h/2))
        print("THRESHOLD REACHED!", highest_val)
        cv.destroyAllWindows()
        return {
          "top": target[1],
          "left": target[0],
          "width": w,
          "height": h
        }
  cv.destroyAllWindows()