# Face API

This project acts as an aggregator for Face++ (https://www.faceplusplus.com/) and Kairos (https://www.kairos.com/), drawing on the strengths of both  

Kairos provides age, gender, ethnicity, glasses, lip status  
Face++ provides emotion, smile, and beauty score  

## Installation

`sudo pip install -r requirements.txt`  
Edit config.py, replacing my API keys with your own

## Test
Run get_attributes.py [filename] to test with a local file

## Run
Run web_server.py to run as a web service

## Test
You can use the command `curl -vv localhost:8080 --data-binary @file.png` to test the API functionality
