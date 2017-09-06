#!/usr/bin/env python
import grequests
import base64
import sys
import time
import numpy as np
import config

races = ["asian", "black", "hispanic", "other", "white"]

def req_kairos(image):
  headers = {
    "app_id": config.KAIROS_APP_ID,
    "app_key": config.KAIROS_APP_KEY
  }

  payload = {
    "image": image
  }

  r = grequests.post("https://api.kairos.com/detect", headers=headers, json=payload)
  return r

def req_facepp(image):

  attr="gender,age,smiling,emotion,headpose,facequality,blur,eyestatus,ethnicity,beauty"

  payload = {
    "api_key": config.FACEPP_API_KEY,
    "api_secret": config.FACEPP_API_SECRET,
    "image_base64": image,
    "return_attributes": attr
  }

  r = grequests.post("https://api-us.faceplusplus.com/facepp/v3/detect", data=payload)
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
  return """Age: {}
Gender: {}
Ethnicity: {}
Emotion: {}
Glasses: {}
Lips: {}
Smile: {:.0f}%
Beauty: F:{:.0f}%, M:{:.0f}%
""".format(
  obj['kairos']['attributes']['age'],
  obj['kairos']['attributes']['gender']['type'],
  race(obj['kairos']['attributes']),
  emote(obj['fpp']['attributes']['emotion']),
  obj['kairos']['attributes']['glasses'],
  obj['kairos']['attributes']['lips'],
  obj['fpp']['attributes']['smile']['value'],
  obj['fpp']['attributes']['beauty']['female_score'],
  obj['fpp']['attributes']['beauty']['male_score'],
)

def req_both(image):
  kairos = req_kairos(image)
  fpp = req_facepp(image)
  # req both concurrently
  results = grequests.map((kairos,fpp))
  kairos = results[0].json()
  fpp = results[1].json()
  faces = []
  for kf in kairos['images'][0]['faces']:
    minD = 9999
    minFF = None
    for ff in fpp['faces']:
      kfc = np.array((kf['topLeftX'] + kf['width'] / 2, kf['topLeftY'] + kf['height'] / 2))
      ffc = np.array((ff['face_rectangle']['left'] + ff['face_rectangle']['width'] / 2, ff['face_rectangle']['top'] + ff['face_rectangle']['height'] / 2))
      d = np.linalg.norm(kfc - ffc)
      if d < minD:
        minD = d
        minFF = ff
    attrs = {
      "kairos": kf,
      "fpp": minFF
    }
    attrs['text'] = to_text(attrs)
    faces.append(attrs)
  return faces


if __name__ == "__main__":
  with open(sys.argv[1]) as f:
    image = base64.b64encode(f.read())
  s = time.time()
  result = req_both(image)
  print("{} faces in image".format(len(result)))
  for f in result:
    print(f['text'])
  print("got attrs, took {}s".format(time.time() - s))

