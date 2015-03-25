import sys, time, os
from request_utils import send_request
from multiprocessing import Process

IPs = sys.argv[1].split(",")
PORT = int(sys.argv[2])
NUM_MESSAGES = int(sys.argv[3])
NUM_RUNS = int(sys.argv[4])
P_CODE = sys.argv[5]

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
    for x in range(NUM_MESSAGES):
        start = time.time()
        message = 'Process %d sending it\'s message %d to %s (%s)' % (run_num, x, IPs[x % len(IPs)], P_CODE)
        message = {
            'message': message
        }
        response = prepare_and_send_request(IPs[x % len(IPs)], PORT, 'POST', '/broadcast', payload=message)
        print 'response status: %s (%s)' % (response['code'], response['content'])
        partial = time.time() - start
        total = total + partial
    total = total / NUM_MESSAGES
    f = open('experiments/%s-%d_%d' % (P_CODE, (NUM_RUNS * NUM_MESSAGES), run_num), 'w')
    f.write(str(total))
    f.close()

ps = []
for run_num in range(NUM_RUNS):
    p = Process(target=run, args=(run_num,))
    p.daemon = True
    p.start()
    print "started process %d" % run_num
    ps.append(p)

for p in ps:
    p.join()
    print "one process finished"
