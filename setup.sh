#!/bin/sh

USER=ubuntu

sudo apt-get install python-pip
sudo pip install flask
sudo pip install Flask-SQLAlchemy
sudo pip install kazoo
sudo pip install requests
sudo pip install uwsgi
sudo apt-get install postgresql postgresql-contrib
sudo apt-get install build-essential python-dev
sudo apt-get install python-psycopg2
sudo -u postgres createuser $USER
sudo -u postgres createdb local_database
