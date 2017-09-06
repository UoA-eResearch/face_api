#!/usr/bin/env python
from get_attributes import req_both
from bottle import *
import base64
import json
BaseRequest.MEMFILE_MAX = 1e8

@get('/')
def default_get():
  return static_file("index.html", ".")


@post('/')
def default_post():
  if request.files.get('pic'):
      binary_data = request.files.get('pic').file.read()
  else:
      binary_data = request.body.read()
  image = base64.b64encode(binary_data)
  results = req_both(image)
  response.content_type = 'application/json'
  return json.dumps(results, indent=4)

port = int(os.environ.get('PORT', 8080))

if __name__ == "__main__":
    run(host='0.0.0.0', port=port, debug=True, server='gunicorn', workers=4)

app = default_app()
