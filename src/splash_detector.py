from mss import mss
import numpy as np
import cv2 as cv
import math, time
from loguru import logger

def is_splash_whitepx(threshold, current):
  H, W = current.shape
  white_pixels = 0
  i = 0
  while i < H:
    j = 0
    while j < W:
      if current[i][j] > 245:
        white_pixels = white_pixels + 1
      if white_pixels > threshold:
        return True
      j = j + 1
    i = i + 1
  return False

def seek_splash(config, area_of_interest):
  og = None
  with mss() as sct:
    while True:
      start_time = time.time()
      img = cv.cvtColor(np.array(sct.grab(area_of_interest)), cv.COLOR_BGRA2GRAY)
      splashed = False
      if og is None:
        og = img
      else:
        splashed = is_splash_whitepx(config.splash_threshold_whitepx, img)
        if splashed:
          logger.info("SPLASHED!")
          return True
      key_bit = cv.waitKey(25) & 0xFF
      if key_bit == ord("q"):
        cv.destroyAllWindows()
        break
