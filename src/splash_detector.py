from mss import mss
import numpy as np
import cv2 as cv
import math, time
from loguru import logger

def is_splash_whitepx(threshold, current):
  white_pixels = (current >= 245).sum()
  if white_pixels> threshold:
      print(f'>>> {white_pixels}')
      return True
  print(f'<<< {white_pixels}')
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
