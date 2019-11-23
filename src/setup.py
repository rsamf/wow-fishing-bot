import time, math, sys
import pyautogui as pag
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
        print( x, y )
        return (x, y)
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
  last_time = time.time()
  print("Start drawing area of interest")
  while True:
    x, y = pag.position()
    if(last_point != (x, y)):
      last_time = time.time()
    last_point = (x, y)
    if time.time() - last_time > 1:
      if points != [] and points[-1] == (x, y):
        if len(points) > 2:
          return np.array(points, dtype=np.int32)
        else:
          print("Must draw at least 3 points")
          last_time = time.time()
      else:
        points.append((x, y))
        last_time = time.time()
        print(points)
    time.sleep(0.05)


def setup(settings):
  def get_extreme(arr, i, cmp):
    ext = arr[0][i]
    for el in arr[1:]:
      if cmp(el[i], ext):
        ext = el[i]
    return ext
  def less(a, b):
    return a < b
  def greater(a, b):
    return a > b

  if settings.attach_bait:
    settings.bait_location = get_single_loc(settings, 'bait')
    settings.pole_location = get_pole_loc(settings)
  settings.area_of_interest = get_area_of_interest(settings)
  settings.cast_location = get_single_loc(settings, 'cast action')

  min_x = get_extreme(settings.area_of_interest, 0, less)
  min_y = get_extreme(settings.area_of_interest, 1, less)
  max_x = get_extreme(settings.area_of_interest, 0, greater)
  max_y = get_extreme(settings.area_of_interest, 1, greater)
  settings.top_left = (min_x, min_y)
  settings.bot_right = (max_x, max_y)

