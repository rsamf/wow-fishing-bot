import time
import pyautogui as pag
import math
import numpy as np

def distance(p1, p2):
  return math.sqrt( (p1[0] - p2[0])**2 + (p1[1] - p2[1])**2 )

def get_single_loc(settings, name):
  point = None
  last_point = (0,0)
  start_time = time.time()
  print("Point to location of %s for 1 sec" % name)
  while True:
    x, y = pag.position()
    if last_point == (x,y):
      if time.time() - start_time > 1:
        print( x-settings.get_left(), y-settings.get_top() )
        return (x-settings.get_left(), y-settings.get_top())
    else:
      start_time = time.time()
      curr_time = start_time
    time.sleep(0.05)
    last_point = (x, y)

def get_pole_loc(settings):
  pag.typewrite('c')
  l = get_single_loc(settings, 'fishing pole')
  pag.typewrite('c')
  return l

def get_area_of_interest(settings):
  points = []
  last_point = (0,0)
  count = 0
  print("Start drawing area of interest")
  while True:
    x, y = pag.position()
    if(last_point == (x, y)):
      count = count + 1
    else:
      count = 0
    last_point = (x, y)
    if count > settings.minimumConcurrentPoints:
      nx, ny = (x-settings.get_left(), y-settings.get_top())
      n = len(points)
      if n > 1 and points[n-1] == (nx, ny):
        return np.array(points, dtype=np.int32)
      points.append((nx, ny))
      count = 0
      print(points)
    time.sleep(0.05)



def setup(settings):
  if settings.attach_bait:
    settings.bait_location = get_single_loc(settings, 'bait')
    settings.pole_location = get_pole_loc(settings)
  settings.area_of_interest = get_area_of_interest(settings)



