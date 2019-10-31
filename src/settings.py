import cv2 as cv

class Settings():
  def __init__(self):
    self.is_testing = False
    self.area_of_interest = None
    self.attach_bait = False
    self.bait_location = None
    self.pole_location = None
    self.minimumConcurrentPoints = 25
    self.threshold = 0.34
    self.splash_threshold = 0.50
    self.splash_threshold_whitepx = 5
    self.top_left = (0,0)
    self.bot_right = (1000, 570)
    self.loot_loc= (50,50)
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
      self.templates.append(cv.Canny(cv.cvtColor(cv.imread(f), cv.COLOR_BGR2GRAY), 50, 150))

  def get_monitor(self):
    top = self.top_left[1]
    left = self.top_left[0]
    width = self.bot_right[0] - left
    height = self.bot_right[1] - top
    return {
      "top": top,
      "left": left,
      "width": width,
      "height": height
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


