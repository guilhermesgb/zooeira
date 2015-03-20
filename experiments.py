import sys, time, os
from request_utils import send_request
from multiprocessing import Process

IP = sys.argv[1]
PORT = int(sys.argv[2])
NUM = int(sys.argv[3])
P_CODE = sys.argv[4]

def prepare_and_send_request(ip, port, \
  method, endpoint, payload=None):

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    response = send_request(method, 'http://%s:%d%s' % (ip, port, endpoint),
        payload=payload, headers=headers)
    return response

def run(run_num):
    total = 0
    for x in range(NUM):
        start = time.time()
        message = {
            'message': 'Message (%d) from (%s)' % (NUM, P_CODE)
        }
        response = prepare_and_send_request(IP, PORT, 'POST', '/broadcast', payload=message)
        partial = time.time() - start
        total = total + partial
    total = total / NUM
    f = open('experiments/%s-%d_%d' % (P_CODE, NUM, run_num), 'w')
    f.write(str(total))
    f.close()

ps = []
for run_num in range(3):
    p = Process(target=run, args=(run_num,))
    p.daemon = True
    p.start()
    ps.append(p)

for p in ps:
    p.join()
