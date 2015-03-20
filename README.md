# zooeira

##Group communication using ZooKeeper

Universidade Federal de Campina Grande - Distributed Systems project - 2014.2

**OBS:** This guide is meant for _Ubuntu_.

###Get the latest version of the project:

    sudo apt-get install git
    git clone http://github.com/guilhermesgb/zooeira.git

###Setup:

    cd zooeira

We're assuming you're going to try this project out with user `ubuntu`.
Otherwise, open the `setup.sh` file:

    vim setup.sh

Then replace `ubuntu` with your user in the following line:

    sudo -u postgres createuser ubuntu

Then, you can go ahead and start the setup script!

    ./setup.sh

This script will get all the dependencies and create the database used by the Application Server.

###Start a local ZooKeeper server in the background

    ./start-zookeeper.sh &

###Start a local Application Server in the background

    ./start-server.sh &
    
###Finally start another local Application Server!

First open the `start-server.sh` script and change the variable `PORT` value to something other than `3031`.
Then:

    ./start-server.sh
