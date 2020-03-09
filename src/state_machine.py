import time, sys, os
import random
import pyautogui as pag
from bob_finder import search_and_destroy
from splash_detector import seek_splash
from setup import initialize, get_single_loc
from clicker import bait
from settings import Settings
from loguru import logger

config = Settings()
current_bob_loc = (0,0)
current_bob_box = (0,0)
ui_is_hidden = True
time_attached = 0
round_count = 0
successes = 0

def init():
  logger.info("Initializing")
  initialize(config)
  move_state(attach_bait)

state_func = init

def hide_ui():
  global ui_is_hidden
  if not ui_is_hidden:
    logger.info("Hidding UI")
    ui_is_hidden = True
    pag.typewrite('b')
    pag.typewrite('c')

def show_ui():
  global ui_is_hidden
  if ui_is_hidden:
    logger.info("Showing UI")
    ui_is_hidden = False
    pag.typewrite('b')
    pag.typewrite('c')

def move_state(state):
  global state_func
  state_func = state

def attach_bait():
  global time_attached
  # 10 min = 10 * 60 sec
  if config.attach_bait and time.time() - time_attached > 600 and config.num_bait > 0:
    logger.info('Attaching bait...')
    show_ui()
    bait(config)
    config.num_bait = config.num_bait - 1
    time_attached = time.time()
    hide_ui()
  move_state(cast)


def cast():
  time.sleep(random.uniform(0.25,1))
  pag.moveTo(config.cast_location, duration=0.5)
  pag.click()
  logger.info("Clicked fishing ability")
  # move_state(search_bob)
  move_state(find_hover_wait)

def search_bob():
  global current_bob_loc, current_bob_box
  logger.info("In search of bob")
  time.sleep(1.65)
  bobber = search(config)
  current_bob_loc = bobber["center"]
  current_bob_box = bobber["box"]
  move_state(hover_bob)

def hover_bob():
  logger.info("Hovering bob")
  x, y =  current_bob_loc
  pag.moveTo(x, y, duration=.2)
  move_state(wait_for_splash)

def wait_for_splash():
  logger.info("Waiting for splash...")
  if seek_splash(config, current_bob_box):
    time.sleep(random.random()+.5)
    pag.rightClick()
    move_state(loot_fish)

def find_hover_wait():
  global round_count, successes
  time.sleep(1.65)
  result = search_and_destroy(config)
  round_count = round_count + 1
  successes = successes + (1 if result else 0)
  logger.info("Accuracy is %f%% (n=%d)" % (round(100 * successes/round_count), round_count) )
  move_state(loot_fish)

def loot_fish():
  logger.info("Looting")
  if not config.auto_loot:
    if config.loot_location:
      pag.moveTo(config.loot_location, duration=.75)
    else:
      config.loot_location = get_single_loc('loot')
      logger.info(f"Location is {config.loot_location}  for next time if you want to put it in config.loot_location")
    pag.rightClick()
  move_state(attach_bait)

while True:
  state_func()
  
