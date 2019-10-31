import time, sys
from bob_finder import search
from splash_detector import seek_splash
from setup import setup
from clicker import loot, bait
import pyautogui as pag
from settings import Settings
import random

config = Settings()
current_bob_loc = (0,0)
current_bob_box = (0,0)
ui_is_hidden = False
time_attached = 0

def init():
  print("in init")
  config.attach_bait = True
  setup(config)
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
  pag.moveTo(145, 550, duration=0.5)
  pag.click()
  move_state(search_bob)

def search_bob():
  global current_bob_loc, current_bob_box
  print("in search bob")
  hide_ui()
  time.sleep(1.65)
  current_bob_box = search(config)
  bb = current_bob_box
  current_bob_loc = (int(bb["left"] + bb["width"]/2),
                     int(bb["top"] + bb["height"]/2))
  move_state(hover_bob)

def hover_bob():
  print("in hover bob")
  hide_ui()
  x, y =  current_bob_loc
  left, top = config.top_left
  pag.moveTo(x - left, y - top, duration=.2)
  move_state(wait_for_splash)

def wait_for_splash():
  print("waiting for splash")
  hide_ui()
  if seek_splash(config, current_bob_box):
    time.sleep(random.random()/2+.2)
    pag.rightClick()
    move_state(loot_fish)

def loot_fish():
  print("looting fish")
  show_ui()
  loot()
  move_state(attach_bait)

while True:
  # print(pag.position())
  # time.sleep(1)
  state_func()
  # search_bob()