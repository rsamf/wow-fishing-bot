import time, math, sys, json, os
import pyautogui as pag
import numpy as np
from pynput.keyboard import Listener, Key
from pywinauto import Application
from loguru import logger



def distance(p1, p2):
  return math.sqrt( (p1[0] - p2[0])**2 + (p1[1] - p2[1])**2 )

def countdown(secs):
  while secs > 0:
    logger.info(str(secs) + "...")
    time.sleep(1)
    secs = secs - 1

def get_single_loc(name):
  logger.info("Point to location of %s for 1 sec in..." % name)
  countdown(3)
  point = None
  last_point = (0,0)
  start_time = time.time()
  while True:
    x, y = pag.position()
    if last_point == (x,y):
      if time.time() - start_time > 1:
        logger.info(f"Casting location at {x}, {y}")
        return (x, y)
    else:
      start_time = time.time()
      curr_time = start_time
    time.sleep(0.05)
    last_point = (x, y)

def get_pole_loc():
  pag.typewrite('c')
  l = get_single_loc('fishing pole')
  pag.typewrite('c')
  return l

def get_area_of_interest():
  logger.info("Start drawing area of interest in...")
  countdown(3)
  points = []
  last_point = (0,0)
  last_time = time.time()
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
          logger.info("Must draw at least 3 points")
          last_time = time.time()
      else:
        points.append((x, y))
        last_time = time.time()
        logger.info(points)
    time.sleep(0.05)

def focus_wow_window():
  wow = Application().connect(path="WowClassic.exe", title="World of Warcraft")
  wow.WorldofWarcraft.set_focus()

def exit_bot(key):
  if key is Key.esc: 
    logger.info("Manual override... Exiting bot!")
    os._exit(0)

def initialize(settings):
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
  
  # listen for manual override
  listener = Listener(
    on_release=exit_bot)
  listener.start()

  focus_wow_window()

  try:
    with open('./config/config.json') as f:
      data = json.load(f)
      settings.attach_bait = data["attachBait"]
      settings.auto_loot = data["autoLoot"]
      settings.img_dir = data["imgDir"]
      settings.bait_location = data["baitLocation"]["x"], data["baitLocation"]["y"]
      settings.pole_location = data["poleLocation"]["x"], data["poleLocation"]["y"]
      settings.cast_location = data["castLocation"]["x"], data["castLocation"]["y"]
      settings.loot_location = data["lootLocation"]["x"], data["lootLocation"]["y"]
      settings.time_before_logout = data["timeInSecsBeforeLogout"]
      settings.graceful_exit = data["gracefulExit"]

      if settings.graceful_exit:
        settings.hearthstone_location = data["hearthstoneLocation"]["x"], data["hearthstoneLocation"]["y"]

      # add all the points of interest
      if len(data["areaOfInterest"]) > 2:
        settings.area_of_interest = []
        for el in data["areaOfInterest"]:   
          settings.area_of_interest.append((el["x"], el["y"]))
      else:
        logger.error("Your area of interest contains less than 3 points... Please redefine")
        settings.area_of_interest = get_area_of_interest()
        
  except IOError:
    logger.info("No configuration file found.")

    if settings.attach_bait:
      settings.bait_location = get_single_loc('bait')
      settings.pole_location = get_pole_loc()
    settings.area_of_interest = get_area_of_interest()
    settings.cast_location = get_single_loc('cast action')

  min_x = get_extreme(settings.area_of_interest, 0, less)
  min_y = get_extreme(settings.area_of_interest, 1, less)
  max_x = get_extreme(settings.area_of_interest, 0, greater)
  max_y = get_extreme(settings.area_of_interest, 1, greater)
  settings.top_left = (min_x, min_y)
  settings.bot_right = (max_x, max_y)
  settings.load_images()

