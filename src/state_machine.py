import time, sys
from bob_finder import search_and_destroy
from splash_detector import seek_splash
from setup import initialize, get_single_loc
from clicker import bait
import pyautogui as pag
from settings import Settings
import random

config = Settings()
current_bob_loc = (0,0)
current_bob_box = (0,0)
ui_is_hidden = False
time_attached = 0
round_count = 0
successes = 0

##
## Set this to True to attach bait every 10 min
##
config.attach_bait = False


def init():
  print("in init")
  initialize(config)
  move_state(attach_bait)

state_func = init

def hide_ui():
  global ui_is_hidden
  if not ui_is_hidden:
    ui_is_hidden = True
    pag.hotkey('alt', 'z')

def show_ui():
  global ui_is_hidden
  if ui_is_hidden:
    print("showing ui")
    ui_is_hidden = False
    pag.hotkey('alt', 'z')
    pag.typewrite('b')

def move_state(state):
  global state_func
  state_func = state

def attach_bait():
  global time_attached
  print('in bait')
  show_ui()
  # 10 min = 10 * 60 sec
  if config.attach_bait and time.time() - time_attached > 600:
    bait(config)
    time_attached = time.time()
  move_state(cast)


def cast():
  print("in cast")
  show_ui()
  x,y = config.cast_location
  pag.moveTo(x, y, duration=0.5)
  pag.click()
  print("clicked")
  # move_state(search_bob)
  move_state(find_hover_wait)

def search_bob():
  global current_bob_loc, current_bob_box
  print("in search bob")
  hide_ui()
  time.sleep(1.65)
  bobber = search(config)
  current_bob_loc = bobber["center"]
  current_bob_box = bobber["box"]
  move_state(hover_bob)

def hover_bob():
  print("in hover bob")
  hide_ui()
  x, y =  current_bob_loc
  pag.moveTo(x, y, duration=.2)
  move_state(wait_for_splash)

def wait_for_splash():
  print("waiting for splash")
  hide_ui()
  if seek_splash(config, current_bob_box):
    time.sleep(random.random()+.5)
    pag.rightClick()
    move_state(loot_fish)

def find_hover_wait():
  global round_count, successes
  print("finding, hovering, then waiting")
  hide_ui()
  time.sleep(1.65)
  result = search_and_destroy(config)
  round_count = round_count + 1
  successes = successes + (1 if result else 0)
  print( "accuracy is %f%%" % (round(100 * successes/round_count)) )
  move_state(loot_fish)

def loot_fish():
  print("looting fish")
  show_ui()
  if config.loot_location:
    x, y = config.loot_location
    pag.moveTo(x, y, duration=.75)
  else:
    config.loot_location = get_single_loc('loot')
    print("Location is " + str(config.loot_location) + \
          " for next time if you want to put it in config.loot_location")
  pag.rightClick()
  move_state(attach_bait)

while True:
  state_func()
