from kazoo.client import KazooClient
import string, time
from config import *

zk = KazooClient(string.join(ZOOKEEPER_ADDRESSES, ','))
zk.start()

children = zk.get_children('/server')
print children
for child in children:
    print child
    print zk.get('/server/' + child)

zk.stop()
