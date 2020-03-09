import time, sys, os
import cv2 as cv
import numpy as np
from mss import mss, exception as MSSException
from splash_detector import is_splash_whitepx
import pyautogui as pag
import random
from loguru import logger

METHOD = cv.TM_CCOEFF_NORMED

def get_updated_bobber_loc(settings, img):
  highest_val = -1
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
  start_time = time.time()

  with mss() as sct:
    best_target = None
    best_target_value = 0
    last_process_time = 0
    while "Screen capturing":
      # timer
      bot_time = int(time.perf_counter())
      if last_process_time != bot_time:
        logger.info(f"Time fishing: {bot_time} seconds")
      last_process_time = bot_time

      if settings.time_before_logout > bot_time:
        if time.time() - start_time > 30:
          return False
        if cv.waitKey(25) & 0xFF == ord("q"):
          break
        img = None
        try:
          img = cv.cvtColor(np.array(sct.grab(monitor)), cv.COLOR_BGRA2GRAY)
        except (MSSException.ScreenShotError):
          continue
        img = cv.Canny(img, settings.canny_thresholds[0], settings.canny_thresholds[1])

        updated_bobber = get_updated_bobber_loc(settings, img)
        if (updated_bobber["value"] > best_target_value):
          best_target_value = updated_bobber["value"]
          best_target = updated_bobber
          x, y = best_target["center"]
          pag.moveTo(x, y, duration=.2)
          logger.info(f"New bobber at ({x}, {y}) with value of {best_target_value}")

        try:
          img = cv.cvtColor(np.array(sct.grab(best_target["box"])), cv.COLOR_BGRA2GRAY)
        except (MSSException.ScreenShotError):
          continue
        is_splashed = is_splash_whitepx(settings.splash_threshold_whitepx, img)
        if is_splashed:
          pag.rightClick()
          return True
      else:
        logger.info("Maximum fishing time has beenr reached. Exiting bot.")
        if settings.graceful_exit:
          # graceful exit means the bot will hearth before leaving the game
          pag.moveTo(settings.hearthstone_location, duration=1)
          pag.click()
          time.sleep(15)
        else:
          pag.hotkey('alt', 'f4')
        os._exit(0)


  cv.destroyAllWindows()
  return False