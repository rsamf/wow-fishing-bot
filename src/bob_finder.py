import time, sys
import cv2 as cv
import numpy as np
from mss import mss
from splash_detector import is_splash_whitepx
import pyautogui as pag

METHOD = cv.TM_CCOEFF_NORMED

def search(settings):
  monitor = settings.get_monitor()
  threshold = settings.threshold
  # mask = np.zeros((monitor["height"], monitor["width"]), np.uint8)
  # cv.fillConvexPoly(mask, settings.area_of_interest, 255)

  with mss() as sct:
    while "Screen capturing":
      if cv.waitKey(25) & 0xFF == ord("q"):
        break
      img = cv.cvtColor(np.array(sct.grab(monitor)), cv.COLOR_BGRA2GRAY)
      img = cv.Canny(img, settings.canny_thresholds[0], settings.canny_thresholds[1])
      # img = cv.bitwise_and(img, mask)
      cv.imshow('img', img)
      highest_val = 0
      target = None
      for template in settings.templates:
        h, w = template.shape
        res = cv.matchTemplate(img, template, METHOD)
        _, max_val, _, max_loc = cv.minMaxLoc(res)
        if max_val > highest_val:
          highest_val = max_val
          target = max_loc
      if highest_val > threshold:
        center = (int(target[0] + w/2 + settings.get_left()), int(target[1] + h/2 + settings.get_top()))
        print("Threshold reached with a value of", highest_val, "at", center)
        cv.destroyAllWindows()
        return {
          "box": {
            "top": int(center[1] - h / 2),
            "left": int(center[0] - w / 2),
            "width": int(w),
            "height": int(h)
          },
          "center": center
        }
      print("Leading value is", highest_val)
  cv.destroyAllWindows()

def get_updated_bobber_loc(settings, img):
  highest_val = 0
  target = None
  for template in settings.templates:
    h, w = template.shape
    res = cv.matchTemplate(img, template, METHOD)
    _, max_val, _, max_loc = cv.minMaxLoc(res)
    if max_val > highest_val:
      highest_val = max_val
      target = max_loc
  center = (int(target[0] + w / 2 + settings.get_left()), int(target[1] + h / 2 + settings.get_top()))
  return {
    "box": {
      "top": int(center[1] - h / 2),
      "left": int(center[0] - w / 2),
      "width": int(w),
      "height": int(h)
    },
    "center": center,
    "value": highest_val
  }

def search_and_destroy(settings):
  monitor = settings.get_monitor()
  threshold = settings.threshold

  with mss() as sct:
    best_target = None
    best_target_value = 0
    while "Screen capturing":
      if cv.waitKey(25) & 0xFF == ord("q"):
        break
      img = cv.cvtColor(np.array(sct.grab(monitor)), cv.COLOR_BGRA2GRAY)
      img = cv.Canny(img, settings.canny_thresholds[0], settings.canny_thresholds[1])
      cv.imshow('img', img)

      updated_bobber = get_updated_bobber_loc(settings, img)
      if (updated_bobber["value"] > best_target_value):
        best_target_value = updated_bobber["value"]
        best_target = updated_bobber
        x, y = best_target["center"]
        pag.moveTo(x, y, duration=.2)
        print("New bobber at", (x, y), "with value of", best_target_value)

      img = cv.cvtColor(np.array(sct.grab(best_target["box"])), cv.COLOR_BGRA2GRAY)
      print("Checking splash")
      is_splashed = is_splash_whitepx(settings.splash_threshold_whitepx, img)
      if is_splashed:
        pag.rightClick()
        return True

  cv.destroyAllWindows()
  return False