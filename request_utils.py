from requests import Request, Session
from requests.exceptions import Timeout, SSLError
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager
import json


class SSLAdapter(HTTPAdapter):
    def __init__(self, ssl_version=None, **kwargs):
        self.ssl_version = ssl_version
        super(SSLAdapter, self).__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(num_pools=connections,
            maxsize=3000, block=block,
            ssl_version=self.ssl_version)

def send_request(method, url, payload=None, headers=None, reattempt=0):

    s = Session()
    s.mount('https://', SSLAdapter('TLSv1'))

    if ( payload == None ):
        request = Request(method, url, headers=headers)
        r = s.prepare_request(request)
    else:
        if ( headers == None ):
            headers = {}
        request = Request(method, url,
            data=json.dumps(payload), headers=headers)
        r = s.prepare_request(request)

    try:
        response = s.send(r, verify=False, timeout=3)
    except (Timeout, SSLError) as e:
        if reattempt < 1:
            return send_request(method, url, payload,
              reattempt=reattempt + 1)
        else:
            return {
                'failure': 'could not send request',
                'code': -1,
                'content': '{%s}' % str(e)
            }

    return {
        'success': response.ok,
        'code': response.status_code,
        'content': response.content
    }
