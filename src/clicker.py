import pyautogui as pag
import time

def bait(settings):
  pag.moveTo(settings.bait_location, duration = 1)
  pag.rightClick()
  pag.moveTo(settings.pole_location, duration = 1)
  pag.click()
  time.sleep(8)