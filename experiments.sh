#!/bin/sh

ISOLATED_IP=54.207.61.208
DISTRIBUTED_IPS=54.207.34.192,54.207.64.176,54.207.64.185

python experiments.py $ISOLATED_IP 3031 4 3 Isolated
echo "First done"
python experiments.py $ISOLATED_IP 3031 9 3 Isolated
echo "Second done"
python experiments.py $ISOLATED_IP 3031 17 3 Isolated
echo "Third done"
python experiments.py $DISTRIBUTED_IPS 3031 4 3 Distributed
echo "Fourth done"
python experiments.py $DISTRIBUTED_IPS 3031 9 3 Distributed
echo "Fifth done"
python experiments.py $DISTRIBUTED_IPS 3031 17 3 Distributed
