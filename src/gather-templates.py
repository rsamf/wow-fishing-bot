import pyautogui as pag
import time, sys, os
import cv2 as cv
import numpy as np
from loguru import logger
from mss import mss
from pynput.keyboard import Key, Listener


width = 50
height = 50
directory = '../images'
count = 0


def capture(img):
  global count
  import os
  if not os.path.exists(directory):
    os.makedirs(directory)
  cv.imwrite(directory + '/template' + str(count) + '.PNG', img)
  count = count + 1

def main():
  with mss() as sct:
    while True:
      x, y = pag.position()
      area = {
        "top": int(y - height / 2),
        "left": int(x - width / 2),
        "width": int(width),
        "height": int(height)
      }
      logger.info(f"({x}, {y})")
      im = np.array(sct.grab(area))
      cv.imshow('preview', im)

      key_bit = cv.waitKey(25) & 0xFF
      if key_bit == ord("q"):
        break
      with Listener(on_release=cap):
        capture(im)
  cv.destroyAllWindows()

main()
