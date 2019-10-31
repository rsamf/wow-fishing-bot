import cv2 as cv
import numpy as np
import time
from mss import mss

def get_yolo_shape(shape, size):
  y, x, _ = shape
  if size == "small":
    return(320/y, 320/x)
  if size == "medium":
    return (416/y, 416/x)
  else:
    return (609/y, 609/x)

net = cv.dnn.readNet("../yolo/yolov3-tiny.weights", "../yolo/yolov3-tiny.cfg")
classes = []
with open("../yolo/coco.names", "r") as f:
    classes = [line.strip() for line in f.readlines()]
layer_names = net.getLayerNames()
output_layers = [layer_names[i[0] - 1] for i in net.getUnconnectedOutLayers()]
colors = np.random.uniform(0, 255, size=(len(classes), 3))

img = cv.imread("../images/dog.jpg")
new_shape = get_yolo_shape(img.shape, "medium")
img = cv.resize(img, None, fx=new_shape[1], fy=new_shape[0])
height, width, channels = img.shape
print(img.shape)

start_time = time.time()
blob = cv.dnn.blobFromImage(img, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
net.setInput(blob)
outs = net.forward(output_layers)
print("done in  %f sec" % (time.time()-start_time))
class_ids = []
confidences = []
boxes = []
for out in outs:
  for detection in out:
    scores = detection[5:]
    class_id = np.argmax(scores)
    confidence = scores[class_id]
    if confidence > 0.5:
      # Object detected
      center_x = int(detection[0] * width)
      center_y = int(detection[1] * height)
      w = int(detection[2] * width)
      h = int(detection[3] * height)
      # Rectangle coordinates
      x = int(center_x - w / 2)
      y = int(center_y - h / 2)
      cv.rectangle(img, (x, y), (x + w, y + h), (255,122,23), 2)
      boxes.append([x, y, w, h])
      confidences.append(float(confidence))
      class_ids.append(class_id)
print(boxes)
cv.imshow("result",img)
cv.waitKey(0)
cv.destroyAllWindows()




