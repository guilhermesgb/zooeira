from flask import Flask, request, make_response
from flask.ext.sqlalchemy import SQLAlchemy, Session
from kazoo.client import KazooClient
from kazoo.protocol.states import KazooState, EventType, KeeperState
from kazoo.exceptions import NoNodeError
from config import *
from random import shuffle
from request_utils import send_request
from multiprocessing import Process

import os, string, json, time, logging, socket
try:
    import uwsgi
except:
    pass
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 'postgresql:///local_database')
db = SQLAlchemy(app)

zk = KazooClient(string.join(ZOOKEEPER_ADDRESSES, ','))
ZNODE_SERVERS = '/server'
ZNODE_SERVER_PREFIX = '/s-'
ZNODE_MESSAGES = '/message'
ZNODE_MESSAGE_PREFIX = '/m-'
CURRENT_SERVER_ZNODE = None
IP = None
PORT = None

KNOWN_SERVERS_LIST = []
IS_LEADER = False
received_messages = {}

#processed messages are consistent among all servers
class ProcessedMessage(db.Model):

    __tablename__ = 'processed-messages'
    id = db.Column(db.Integer, primary_key=True)
    mid = db.Column(db.BigInteger, unique=True)
    message = db.Column(db.Text)

    def __init__(self, mid, message):
        self.mid = mid
        self.message = message

    def __repr__(self):
        return "ProcessedMessage %s" % self.mid

previous_state = None
def zk_state_listener(state):
    global previous_state

    if state == KazooState.LOST:
        logging.info('Connection to ZooKeeper lost')
    elif state == KazooState.SUSPENDED:
        logging.info('Connection to ZooKeeper suspended')
    else:
        if previous_state in (None, KazooState.LOST, KazooState.SUSPENDED) \
          and state == KazooState.CONNECTED:
            logging.info('Connection to ZooKeeper (re)established')
            zk.handler.spawn(prepare_server)
    previous_state = state

zk.add_listener(zk_state_listener)

def get_servers():

    dests = []
    servers = zk.get_children(ZNODE_SERVERS)
    for server in servers:
        data = json.loads(zk.get(ZNODE_SERVERS + '/' + server)[0])
        ip = data['ip']
        port = int(data['port'])
        dests.append((ip, port))
    dests = list(set(dests))
    shuffle(dests)
    return dests

def prepare_and_send_request(ip, port, \
  method, endpoint, payload=None):

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    response = send_request(method, 'http://%s:%d%s' % (ip, port, endpoint),
        payload=payload, headers=headers)
    return response

def atomic_diffusion(sender_ip, sender_port, message, group, loopback, deliver):

    logging.info('Processing atomic diffusion from %s:%d' % (sender_ip, sender_port))

    for server_address in group:
        dest_ip = server_address[0]
        dest_port = server_address[1]
        if ( sender_ip == dest_ip
          and sender_port == dest_port
          and not loopback ):
            continue
        logging.info('Relaying message from %s:%d to %s:%d...' % (
            sender_ip, sender_port, dest_ip, dest_port
        ))
        response = prepare_and_send_request(dest_ip, dest_port, 'POST',
          '/receive', payload=message)
        logging.info('response status: %s (%s)' % (response['code'], response['content']))

    if deliver:
        logging.info('Storing processed message [%s]: %s' % (message['id'], message['message']))
        db.session.add(ProcessedMessage(message['id'], message['message']))
        db.session.commit()

@app.route('/', methods=['GET', 'POST'])
def index():

    messages = []
    for entry in ProcessedMessage\
      .query.order_by(ProcessedMessage.mid).all():
        messages.append({
            'id': entry.mid,
            'message': entry.message
        })
    payload = {
        'server': 'retrieved all processed messages',
        'messages': messages
    }
    payload['leader'] = IS_LEADER
    if IS_LEADER:
        payload['known_servers'] = KNOWN_SERVERS_LIST
    return make_response(json.dumps(payload), 200)

@app.route('/send', methods=['POST'])
def send_message():

    logging.info('Processing /send endpoint')

    try:
        message_data = request.json
        if ( message_data == None ):
            response = make_response(json.dumps({'server':'payload must be valid json', 'code':'error'}), 200)
            response.headers["Content-Type"] = "application/json"
            return response
        message_data = dict(message_data)
        if ( message_data == None ):
            response = make_response(json.dumps({'server':'payload must be valid json', 'code':'error'}), 200)
            response.headers["Content-Type"] = "application/json"
            return response
    except:
        response = make_response(json.dumps({'server':'payload must be valid json', 'code':'error'}), 200)
        response.headers["Content-Type"] = "application/json"
        return response

    message = message_data.get('message', None)
    if message is None:
        return make_response(json.dumps({'server':'message missing', 'code':'error'}), 200)

    fullpath = zk.create(ZNODE_MESSAGES + ZNODE_MESSAGE_PREFIX,
      value=str(message), sequence=True)
    message_id = zk.get(os.path.join(ZNODE_MESSAGES,
      fullpath))[1].creation_transaction_id

    message_data = {
        'message': message,
	'os_ip': IP,
        'os_port': PORT,
        'id': message_id
    }

    servers_group = get_servers()
    p = Process(target=atomic_diffusion, args=(IP, PORT,
      message_data, servers_group, True, False))
    p.daemon = True
    p.start()
    return make_response(json.dumps({'server':'message sent', 'code':'ok'}), 200)

@app.route('/receive', methods=['POST'])
def receive_message():

    logging.info('Processing /receive endpoint')

    try:
        message_data = request.json
        if ( message_data == None ):
            response = make_response(json.dumps({'server':'payload must be valid json (1)', 'code':'error'}), 200)
            response.headers["Content-Type"] = "application/json"
            return response
        message_data = dict(message_data)
        if ( message_data == None ):
            response = make_response(json.dumps({'server':'payload must be valid json (2)', 'code':'error'}), 200)
            response.headers["Content-Type"] = "application/json"
            return response
    except:
        response = make_response(json.dumps({'server':'payload must be valid json (3)', 'code':'error'}), 200)
        response.headers["Content-Type"] = "application/json"
        return response

    message = message_data.get('message', None)
    if message is None:
        return make_response(json.dumps({'server':'message missing', 'code':'error'}), 200)

    message_id = message_data.get('id', None)
    if message_id is None:
        return make_response(json.dumps({'server':'message_id missing', 'code':'error'}), 200)

    message_os_ip = message_data.get('os_ip', None)
    if message_os_ip is None:
        return make_response(json.dumps({'server':'message original sender ip missing', 'code':'error'}), 200)

    message_os_port = message_data.get('os_port', None)
    if message_os_port is None:
        return make_response(json.dumps({'server':'message original sender port missing', 'code':'error'}), 200)
    message_os_port = int(message_os_port)

    if ( not message_id in received_messages ):

        received_messages[message_id] = message
        logging.info('Received message %s from %s:%d!' % (message, message_os_ip, message_os_port))

        if ( not (IP == message_os_ip and PORT == message_os_port) ):
            message_data = {
                'message': message,
                'os_ip': message_os_ip,
                'os_port': message_os_port,
                'id': message_id
            }
            servers_group = get_servers()
            p = Process(target=atomic_diffusion, args=(IP, PORT,
              message_data, servers_group, True, True))
            p.daemon = True
            p.start()

        else:
            logging.info('Storing processed message [%s]: %s' % (message_data['id'], message_data['message']))
            db.session.add(ProcessedMessage(
              message_data['id'], message_data['message']))
            db.session.commit()

    return make_response(json.dumps({'server':'message received', 'code':'ok'}), 200)

def close_zk_connection():
    logging.info('Stopping connection to ZooKeeper')
    zk.stop()
    zk.close()
    logging.info('Stopped connection to ZooKeeper')
try:
    uwsgi.atexit = close_zk_connection
except:
    pass

def send_presence_to_zk():
    global IP, PORT, CURRENT_SERVER_ZNODE

    IP = os.environ.get("IP", None)
    PORT = int(os.environ.get("PORT", 3031))
    if ( IP is None or PORT is None ):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        data = s.getsockname()
        IP = data[0]
        s.close()
    settings = {'ip': IP, 'port': PORT}

    zk.ensure_path(ZNODE_SERVERS)
    if CURRENT_SERVER_ZNODE is not None:
        zk.delete(ZNODE_SERVERS + CURRENT_ZNODE_SERVER)
    CURRENT_SERVER_ZNODE = zk.create(ZNODE_SERVERS + ZNODE_SERVER_PREFIX,
      value=json.dumps(settings), ephemeral=True, sequence=True)
    CURRENT_SERVER_ZNODE = CURRENT_SERVER_ZNODE.replace(ZNODE_SERVERS, "")
    zk.ensure_path(ZNODE_MESSAGES)

def prepare_server():

    logging.info('Preparing server...')
    send_presence_to_zk()

    logging.info('Loading messages processed before shutdown')
    db.create_all()
    for entry in ProcessedMessage\
      .query.order_by(ProcessedMessage.mid).all():
        received_messages[entry.mid] = entry.message

    logging.info('Synchronizing processed messages with ZooKeeper messages log')
    message_znodes = zk.get_children(ZNODE_MESSAGES)
    message_znodes = list(set(message_znodes))
    for message_znode in message_znodes:
        data = zk.get(ZNODE_MESSAGES + '/' + message_znode)
        message = data[0]
        mid = data[1].creation_transaction_id
        if not mid in received_messages:
            db.session.add(ProcessedMessage(mid, message))
    db.session.commit()

    def determine_leader():

        server_znodes = zk.get_children(ZNODE_SERVERS)
        server_znodes = [ "/" + x for x in server_znodes ]
        server_znodes = list(set(server_znodes))
        seq_nums = [ int(x.replace(ZNODE_SERVER_PREFIX, "").strip())\
          for x in server_znodes ]
        seq_nums.sort()
        current_seq_num = int(CURRENT_SERVER_ZNODE\
          .replace(ZNODE_SERVER_PREFIX, "").strip())
        seq_num_pos = seq_nums.index(current_seq_num)
        if ( seq_num_pos == 0 ):
            logging.info('This server is the leader')
            def update_servers_list():
                global KNOWN_SERVERS_LIST, IS_LEADER

                def watch_callback(event):
                    if event.type == EventType.CHILD:
                        update_servers_list()

                logging.info('Leader updating known servers list')
                KNOWN_SERVERS_LIST = []
                server_znodes = zk.get_children(ZNODE_SERVERS,\
                  watch=watch_callback)
                server_znodes = list(set(server_znodes))
                for server_znode in server_znodes:
                    data = json.loads(zk.get(ZNODE_SERVERS + '/'\
                      + server_znode)[0])
                    ip = data['ip']
                    port = int(data['port'])
                    KNOWN_SERVERS_LIST.append((ip, port))
                shuffle(KNOWN_SERVERS_LIST)

                logging.info('Leader letting other servers know it is leader')
                IS_LEADER = True

            update_servers_list()
        else:
            logging.info('This server is not the leader, watching out for leader failures')
            def watch_callback(event):
                if event.type == EventType.DELETED \
                  and ( event.state == KeeperState.CONNECTED
                  or event.state == KeeperState.CONNECTED_RO
                  or event.state == KeeperState.CONNECTING ):
                    logging.info('It\'s about time to determine the new leader')
                    determine_leader()

            zk.get(ZNODE_SERVERS + ZNODE_SERVER_PREFIX\
              + ('%010d' % seq_nums[seq_num_pos - 1]), watch=watch_callback)

    logging.info('Determining the leader among all servers')
    determine_leader()

zk.start()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)
