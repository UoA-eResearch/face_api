#!/usr/bin/env python
import grequests
import base64
import sys
import time
import numpy as np
import config
import pprint
import cv2
import datetime
import os
import imghdr

races = ["asian", "black", "hispanic", "other", "white"]
scale = 0.5

def exception_handler(request, exception):
  print(request, exception)

def req_facepp(image):

  attr="gender,age,smiling,emotion,headpose,facequality,blur,eyestatus,ethnicity,beauty,mouthstatus,skinstatus"

  payload = {
    "api_key": config.FACEPP_API_KEY,
    "api_secret": config.FACEPP_API_SECRET,
    "image_base64": image,
    "return_attributes": attr
  }

  r = grequests.post("https://api-us.faceplusplus.com/facepp/v3/detect", data=payload)
  return r

def req_omc(image):
  r = grequests.post(config.OMC_SERVER, data=image)
  return r

def race(obj):
  d = { k: v for k, v in obj.items() if k in races }
  racelist = []
  for k in sorted(d, key=d.get, reverse=True):
    if d[k] > .01:
      racelist.append("{}: {:.0%}".format(k, d[k]))
  return ", ".join(racelist)

def emote(obj):
  s = sorted(obj, key=obj.get, reverse=True)
  if obj[s[0]] > 60:
    return "{}: {:.0f}%".format(s[0], obj[s[0]])
  else:
    emotes = []
    for k in s:
      if k > 1:
        emotes.append("{}: {:.0f}%".format(k, obj[k]))
    return ", ".join(emotes)

def to_text(obj):
  s = ""
  if obj['fpp']:
    s += """Age: {}
Gender: {}
Ethnicity: {}
Emotion: {}
Smile: {:.0f}%
Beauty: F:{:.0f}%, M:{:.0f}%
""".format(
  obj['fpp']['attributes']['age']['value'],
  obj['fpp']['attributes']['gender']['value'],
  obj['fpp']['attributes']['ethnicity']['value'],
  emote(obj['fpp']['attributes']['emotion']),
  obj['fpp']['attributes']['smile']['value'],
  obj['fpp']['attributes'].get('beauty', {}).get('female_score'),
  obj['fpp']['attributes'].get('beauty', {}).get('male_score')
)
  if obj['of']:
    s+= """Recognition confidence: {:.2%}
UPI: {}
Name: {}
Position: {}
Department: {}
Reports to: {}
""".format(
  obj['of']['confidence'],
  obj['of']['uid'],
  obj['of']['data']['fullName'],
  obj['of']['data']['positions'][0]['position'],
  obj['of']['data']['positions'][0]['department']['name'],
  obj['of']['data']['positions'][0].get('reportsTo', {'name': 'Unknown'})['name'],
)
  return s

def downscale(binary_data):
  img_array = np.asarray(bytearray(binary_data), dtype=np.uint8)
  image_data = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
  print(image_data.shape)
  height, width, channels = image_data.shape
  image_data = cv2.resize(image_data, (0, 0), fx=scale, fy=scale)
  print(image_data.shape)
  ret, buf = cv2.imencode(".jpg", image_data)
  return buf.tostring()

def save_image(binary_data):
  if config.IMAGE_DIR:
    now = datetime.datetime.now()
    ftype = imghdr.what("", binary_data)
    filename = os.path.join(config.IMAGE_DIR, "{}.{}".format(now, ftype))
    with open(filename, 'w') as f:
      f.write(binary_data)

def req_all(binary_data):
  save_image(binary_data)
  print("Got image of size {}".format(len(binary_data)))
  binary_data = downscale(binary_data)
  print("Resized to {}".format(len(binary_data)))
  b64image = base64.b64encode(binary_data)
  fpp = req_facepp(b64image)
  requests = [fpp]
  if hasattr(config, 'OMC_SERVER'):
    omc = req_omc(binary_data)
    requests.append(omc)
  # req all concurrently
  results = grequests.map(requests, exception_handler=exception_handler)
  try:
    fpp = results[0].json()
  except:
    print(results[0].content)
    fpp = {'faces':[]}
  if hasattr(config, 'OMC_SERVER'):
    try:
      omc = results[-1].json()
    except:
      print(results[-1])
      omc = []
  else:
    omc = []
  faces = []
  # rescale pixel coordinates
  for ff in fpp['faces']:
    for key in ff['face_rectangle']:
      ff['face_rectangle'][key] *= 1.0 / scale
  for of in omc:
    for key in of['face_rectangle']:
      of['face_rectangle'][key] *= 1.0 / scale
  for ff in fpp['faces']:
    ffc = np.array((ff['face_rectangle']['left'] + ff['face_rectangle']['width'] / 2, ff['face_rectangle']['top'] + ff['face_rectangle']['height'] / 2))
    minD = 9999
    minOMC = None
    for of in omc:
      ofc = np.array((of['face_rectangle']['left'] + of['face_rectangle']['width'] / 2, of['face_rectangle']['top'] + of['face_rectangle']['height'] / 2))
      d = np.linalg.norm(ofc - ffc)
      if d < minD:
        minD = d
        minOMC = of
    attrs = {
      "kairos": {
        "topLeftX": ff['face_rectangle']['left'],
        "topLeftY": ff['face_rectangle']['top'],
        "width": ff['face_rectangle']['width'],
        "height": ff['face_rectangle']['height']
      },
      "fpp": ff,
      "of": minOMC
    }
    attrs['text'] = to_text(attrs)
    faces.append(attrs)
  return faces


if __name__ == "__main__":
  with open(sys.argv[1]) as f:
    image = f.read()
  s = time.time()
  result = req_all(image)
  print("{} faces in image".format(len(result)))
  pprint.pprint(result)
  for f in result:
    print(f['text'])
  print("got attrs, took {}s".format(time.time() - s))

