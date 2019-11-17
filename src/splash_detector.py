from mss import mss
import numpy as np
import cv2 as cv
import math, time

#NOT USED
def is_splash(threshold, og, current):
  count = 0
  value = 0
  H, W = og.shape
  i = 0
  while i < H:
    j = 0
    while j < W:
      currPX = int(current[i][j])
      ogPX = int(og[i][j])
      diff_norm = abs(currPX - ogPX)/255
      value = count/(count+1) * value + 1/(count+1) * diff_norm
      count = count+1
      j = j + 1
    i = i + 1
  return value > threshold

#NOT USED
def is_splash_whitepx(threshold, current):
  H, W = current.shape
  white_pixels = 0
  i = 0
  while i < H:
    j = 0
    while j < W:
      if current[i][j] > 180:
        white_pixels = white_pixels + 1
      if white_pixels > threshold:
        return True
      j = j + 1
    i = i + 1
  # print(white_pixels, threshold)
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
          print("SPLASHED!")
          return True

      # print("fps %f" % (1/(time.time()-start_time)))
      # cv.imshow('bob', img)
      key_bit = cv.waitKey(25) & 0xFF
      if key_bit == ord("q"):
        cv.destroyAllWindows()
        break
