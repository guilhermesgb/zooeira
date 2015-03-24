#!/bin/sh

ISOLATED_IP=54.207.38.217
DISTRIBUTED_IPS=54.94.199.2,54.94.197.98,54.207.20.143

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
