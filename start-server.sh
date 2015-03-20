#!/bin/sh
uwsgi --http-socket 0.0.0.0:3031 --wsgi-file server.py --callable app --enable-threads
