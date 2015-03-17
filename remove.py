from kazoo.client import KazooClient
import string
from config import *

zk = KazooClient(string.join(ZOOKEEPER_ADDRESSES, ','))
zk.start()

children = zk.get_children('/server')
zk.delete('/server', recursive=True)
