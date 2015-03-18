from flask import Flask, request, make_response
from flask.ext.sqlalchemy import SQLAlchemy, Session
#from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from kazoo.client import KazooClient
from kazoo.protocol.states import KazooState
from kazoo.exceptions import NoNodeError
from config import *
from random import shuffle
from request_utils import send_request
from multiprocessing import Process

import os, string, json, time, logging, socket
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

def zk_state_listener(state):
    if state == KazooState.LOST:
        #connection lost, should kill? or try to connect again?
        pass
    elif state == KazooState.SUSPENDED:
        #disconnected, should kill this server then
        pass
    else:
        #connected, that's great, tell others I'm a new guy in town
        pass
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


if __name__ == "__main__":

    IP = os.environ.get("IP", None)
    if ( IP is None ):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        IP = s.getsockname()[0]
        s.close()
    PORT = int(os.environ.get("PORT", 5000))
    settings = {'ip': IP, 'port': PORT}

    zk.start()
    zk.create(ZNODE_SERVERS + ZNODE_SERVER_PREFIX,
      value=json.dumps(settings), ephemeral=True,
      sequence=True, makepath=True)

    zk.ensure_path(ZNODE_MESSAGES)

    logging.info('Loading messages processed before shutdown')
    db.create_all()
    for entry in ProcessedMessage\
      .query.order_by(ProcessedMessage.mid).all():
        received_messages[entry.mid] = entry.message

    logging.info('Synchronizing processed messages with ZooKeeper messages log')
    znodes = zk.get_children(ZNODE_MESSAGES)
    for znode in znodes:
        data = zk.get(ZNODE_MESSAGES + '/' + znode)
        message = data[0]
        mid = data[1].creation_transaction_id
        if not mid in received_messages:
            db.session.add(ProcessedMessage(mid, message))
    db.session.commit()
        
    app.run(host="0.0.0.0", port=PORT, debug=True)
