#!/bin/sh
sudo apt-get update
sudo apt-get install build-essential python-dev python-pip postgresql postgresql-contrib python-psycopg2 default-jre
sudo pip install flask Flask-SQLAlchemy kazoo requests uwsgi
sudo pip install --upgrade requests
sudo -u postgres createuser ubuntu
sudo -u postgres createdb local_database
