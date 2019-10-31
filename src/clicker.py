import pyautogui as pag
import time

def loot():
  pag.moveTo(25, 150, duration=.75)
  pag.rightClick()

def bait(settings):
  x, y = settings.bait_location
  pag.moveTo(x, y, duration = .5)
  pag.rightClick()
  pag.typewrite('c')
  x, y = settings.pole_location
  pag.moveTo(x, y, duration = .5)
  pag.click()
  print("Waiting for cast")
  time.sleep(10)
  pag.typewrite('c')