#!/bin/sh

IP="127.0.0.1"
PORT = 3031

uwsgi --http-socket $IP:$PORT --wsgi-file server.py --callable app --enable-threads
