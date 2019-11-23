import pyautogui as pag
import time

def bait(settings):
  x, y = settings.bait_location
  pag.moveTo(x, y, duration = .5)
  pag.rightClick()
  pag.typewrite('c')
  x, y = settings.pole_location
  pag.moveTo(x, y, duration = .5)
  pag.click()
  time.sleep(8)
  pag.typewrite('c')