from kazoo.client import KazooClient
import string
from config import *

zk = KazooClient(string.join(ZOOKEEPER_ADDRESSES, ','))
zk.start()

children = zk.get_children('/server')
for child in children:
    print child
    print zk.get('/server/' + child)
