#!/bin/sh

ISOLATED_IP=54.207.108.96
DISTRIBUTED_IPS=54.207.82.27,54.207.81.194,54.94.212.240

python experiments.py $ISOLATED_IP 3031 2 3 Isolated
echo "First done"
python experiments.py $ISOLATED_IP 3031 4 3 Isolated
echo "Second done"
python experiments.py $ISOLATED_IP 3031 6 3 Isolated
echo "Third done"
python experiments.py $DISTRIBUTED_IPS 3031 2 3 Distributed
echo "Fourth done"
python experiments.py $DISTRIBUTED_IPS 3031 4 3 Distributed
echo "Fifth done"
python experiments.py $DISTRIBUTED_IPS 3031 6 3 Distributed
echo "Sixth done"
