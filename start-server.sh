#!/bin/sh
PORT=3031
export PORT=$PORT
uwsgi --http-socket 0.0.0.0:$PORT --wsgi-file server.py --callable app --enable-threads
