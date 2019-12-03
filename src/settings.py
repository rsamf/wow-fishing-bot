import cv2 as cv

class Settings():
  def __init__(self):
    self.is_testing = False
    self.area_of_interest = None
    self.top_left = None
    self.bot_right = None
    self.attach_bait = False
    self.num_bait = 10
    self.bait_location = None
    self.pole_location = None
    self.cast_location = None
    self.loot_location = None
    # self.threshold = 0.30
    self.splash_threshold_whitepx = 5
    self.canny_thresholds = [80, 180]
    self.templateFiles = [
      '../images/bob-13.png',
      '../images/bob-14.png',
      '../images/bob-15.png',
      '../images/bob-16.png',
      '../images/bob-17.png',
      '../images/bob-18.png',
      '../images/bob-19.png',
      '../images/bob-20.png',
      '../images/bob-21.png',
      '../images/bob-22.png',
      '../images/bob-23.png',
      '../images/bob-24.png'
    ]
    self.templates = []
    for f in self.templateFiles:
      self.templates.append(cv.Canny(cv.cvtColor(cv.imread(f), cv.COLOR_BGR2GRAY), self.canny_thresholds[0], self.canny_thresholds[1]))

  def get_monitor(self):
    top = self.top_left[1]
    left = self.top_left[0]
    width = self.bot_right[0] - left
    height = self.bot_right[1] - top
    return {
      "top": int(top),
      "left": int(left),
      "width": int(width),
      "height": int(height)
    }

  def get_size(self):
    return (self.bot_right[0] - self.top_left[0], self.bot_right[1] - self.top_left[1])

  def get_left(self):
    return self.top_left[0]

  def get_right(self):
    return self.bot_right[0]

  def get_bot(self):
    return self.bot_right[1]

  def get_top(self):
    return self.top_left[1]


