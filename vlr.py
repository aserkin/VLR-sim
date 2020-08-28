#!/usr/bin/env python3
# This is a try to simulate basic SGs procedures of VLR for MME
# In case you don't have VLR but need to test your MME installation for voice centric UEs
# and CS Fallback - this is your friend.
# The program accepts SCTP connection from MME and answers four basic SGs messages initiated
# by MME:
# - Location Update request
# - EPS detach indication
# - IMSI detach indication
# - MME failure
# Other messages are silently ignored
#
import sys
import socket
import selectors
import signal
import types
import sctp
from   sctp import *
from hexdump import *
import logging

# create logger
loglevel = logging.INFO
logger = logging.getLogger(sys.argv[0])
logger.setLevel(loglevel)
# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(loglevel)
# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# add formatter to ch
ch.setFormatter(formatter)
# add ch to logger
logger.addHandler(ch)

# Initiate selector for multiple connections
sel = selectors.DefaultSelector()

# Set SGs message index to 0
sgsidx = 0

#Initialize IEs and answers
imsi=''
mmename=''
lai=''
iename = ''
vlr_name=b'fucking.psycho'
rejectCause=8

# SGs statistics
loc_upd = 0
eps_det = 0
imsi_det = 0
reset_ind = 0
other_req = 0

def init():
  imsi=b''
  mmename=b''
  lai=b''

# SGs Information Element handlers
def imsi_ie(binmsg,sgsidx,iename):
  logger.debug("processing IMSI IE. sgsidx= "+str(sgsidx))
  imsi = bytes(binmsg)[sgsidx:sgsidx+binmsg[sgsidx+1]+2]
  sgsidx = sgsidx+binmsg[sgsidx+1]+2
  iename = "imsi"
  return sgsidx,imsi,iename

def vlrname_ie(binmsg,sgsidx,iename):
  logger.debug("processing VLR name IE")
  sgsidx = sgsidx+binmsg[sgsidx+1]+2
  iename = "vlrname"
  return sgsidx,vlrname,iename

def lai_ie(binmsg,sgsidx,iename):
  logger.debug("processing LAI IE. sgsidx= "+str(sgsidx))
  lai = bytes(binmsg)[sgsidx:sgsidx+binmsg[sgsidx+1]+2]
  sgsidx = sgsidx+binmsg[sgsidx+1]+2
  iename = "lai"
  return sgsidx,lai,iename

def mmename_ie(binmsg,sgsidx,iename):
  logger.debug("processing MME name IE. sgsidx= "+str(sgsidx))
  mmename=bytes(binmsg)[sgsidx:sgsidx+binmsg[sgsidx+1]+2]
  sgsidx = sgsidx+binmsg[sgsidx+1]+2
  iename = "mmename"
  return sgsidx,mmename,iename

def default_ie(binmsg,sgsidx,iename):
  logger.debug("not interesting IE. sgsidx= "+str(sgsidx))
  dummyie=bytes(binmsg)[sgsidx:sgsidx+binmsg[sgsidx+1]+2]
  sgsidx = sgsidx+binmsg[sgsidx+1]+2
  iename = "dummyie"
  return sgsidx,dummyie,iename

ie_names = {
1: "imsi",
2: "vlrname",
3: "tmsi",
4: "lai",
5: "channel needed",
6: "eMLPP priority",
7: "TMSI status",
8: "SGs cause",
9: "mmename",
10: "EPS LU type",
11: "global cn-id",
14: "mobile identity",
15: "reject cause",
16: "IMSI detach from EPS",
17: "IMSI detach from non-EPS",
21: "IMEISV",
22: "NAS message container",
23: "MM info",
27: "Erroneous message",
28: "CLI",
29: "LCS client identity",
30: "LCS indicator",
31: "SS code",
32: "Service indicator",
33: "UE time zone",
34: "Mobile station classmark 2",
35: "Tracking Area Identity",
36: "E0UTRAN Cell Global Identity",
37: "UE EMM mode",
}

#VLR Answer message codes
location_update_request = 9
location_update_accept = 10
location_update_reject = 11
eps_detach_acknoledge = 18
imsi_detach_acknoledge = 20
reset_acknoledge = 22

dispatch_ie = {
1: imsi_ie,
2: vlrname_ie,
4: lai_ie,
9: mmename_ie,
}

def check_lua (answer):
  if answer[1] == 1 and answer[1+2+answer[2]]==4:
    return 0
  else:
    return 1

# SGs request handlers
def loc_update(binmsg,sgsidx,iename):
  global loc_upd
  logger.info("location update request received")
  logger.debug("received message length = "+str(len(binmsg)))
  #hexdump(bytes(binmsg))
  loc_upd += 1
  sgsidx = 0
  sgsidx += 1
  answer = b''
  logger.debug("start processing IEs. sgsidx=  "+str(sgsidx))
  init()
  answer += bytes([location_update_accept])
  while (iename != "lai" and sgsidx<len(binmsg)):
    sgsidx,ie,iename = dispatch_ie.get(binmsg[sgsidx], default_ie)(binmsg,sgsidx,iename)
    if iename != "lai" and iename != "imsi":
        pass
    else:
      answer += ie
  if (check_lua(answer) == 1):
    answer = bytes([location_update_reject,1,8,9,0,0,0,0,0,0,0,11,1,8])
    logger.warning("rejected - invalid mandatory information")
  else:
    if (check_lua(answer) == 0):
      logger.info("location update accepted")
      pass
  return answer

def epc_detach_ack(binmsg,sgsidx,iename): 
  global eps_det
  logger.info("EPS detach indication received")
  logger.debug("received message length = "+str(len(binmsg)))
  #hexdump(bytes(binmsg))
  eps_det += 1
  sgsidx = 1
  answer = b''
  logger.debug("start processing IEs. sgsidx=  "+str(sgsidx))
  init()
  answer += bytes([eps_detach_acknoledge])
  if iename != "imsi":
      pass
  else:
    sgsidx,ie,iename = dispatch_ie.get(binmsg[sgsidx], default_ie)(binmsg,sgsidx,iename)
    if len(ie) > 0:
      answer += ie
      logger.info("EPS detach acknoledged")
  return answer

def imsi_detach_ack(binmsg,sgsidx,iename):
  global imsi_det
  logger.info("IMSI detach indication received")
  logger.debug("received message length = "+str(len(binmsg)))
  #hexdump(bytes(binmsg))
  imsi_det += 1
  sgsidx = 1
  answer = b''
  logger.debug("start processing IEs. sgsidx=  "+str(sgsidx))
  init()
  answer += bytes([imsi_detach_acknoledge])
  if iename != "imsi":
      pass
  else:
    sgsidx,ie,iename = dispatch_ie.get(binmsg[sgsidx], default_ie)(binmsg,sgsidx,iename)
    if len(ie) > 0:
      answer += ie
      logger.info("IMSI detach acknoledged")
  return answer

def reset_ack(binmsg,sgsidx,iename):
  global reset_ind
  logger.info("MME reset indication received")
  reset_ind += 1
  answer = bytes([reset_acknoledge])
  answer += bytes([2])
  answer += bytes([len(vlr_name)])
  answer += bytes(vlr_name)
  logger.info("MME reset indication acknoledged")
  return answer

def dummy(binmsg,sgsidx,iename):
  global other_req
  logger.info("bullshit received. ignoring..")
  #hexdump(bytes(binmsg))
  other_req += 1
  return b''

# This will be dictionary of SGs request handlers
dispatch = {
9: loc_update,
17: epc_detach_ack,
19: imsi_detach_ack,
21: reset_ack,
}


def accept_wrapper(sock):
    conn, addr = sock.accept()  # Should be ready to read
    logger.warning("accepted connection from "+str(addr))
    conn.setblocking(False)
    data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"")
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sel.register(conn, events, data=data)


def service_connection(key, mask):
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(1024)  # Should be ready to read
        if recv_data:
            data.outb += recv_data
        else:
            logger.warning("closing connection to "+str(data.addr))
            sel.unregister(sock)
            sock.close()
    if mask & selectors.EVENT_WRITE:
        if data.outb:
            init()
            sgsidx = 0
            answer = dispatch.get(list(data.outb)[sgsidx], dummy)(list(data.outb),sgsidx,ie_names[list(data.outb)[sgsidx+1]])
            if len(answer) > 0:
              #hexdump(answer)
              data.outb = answer
              sent = sock.send(data.outb)
              data.outb = data.outb[sent:]
            else:
              data.outb = b''
              sent = len(data.outb)
              data.outb = data.outb[sent:]

def dumpStats():
    global loc_upd
    global eps_det
    global imsi_det
    global reset_ind
    global other_req
    logger.error("SGs Statistics")
    logger.error("Location Update Requests received: "+str(loc_upd))
    logger.error("  EPS detach indications received: "+str(eps_det))
    logger.error(" IMSI detach indications received: "+str(imsi_det))
    logger.error("       Reset indications received: "+str(reset_ind))
    logger.error("          Other messages received: "+str(other_req))

def receiveSignal(signalNumber, frame):
    if signalNumber == 2:
        logger.error("Exiting on Ctrl-C")
        sel.close()
        sys.exit(0)
    if signalNumber == 10:
        logger.error("Dumping statistics on signal "+str(signalNumber))
        dumpStats()
        return
    logger.error("Received signal "+str(signalNumber))
    return

# Main
if len(sys.argv) != 3:
    logger.error("usage:", sys.argv[0], "<host> <port>")
    sys.exit(1)

host, port = sys.argv[1], int(sys.argv[2])
lsock = sctpsocket_tcp(socket.AF_INET)
lsock.bind((host, port))
lsock.listen()
logger.warning("listening on "+str(host)+":"+str(port))
lsock.setblocking(False)
sel.register(lsock, selectors.EVENT_READ, data=None)

#try:
while True:
        events = sel.select(timeout=None)
        for key, mask in events:
            if key.data is None:
                accept_wrapper(key.fileobj)
            else:
                service_connection(key, mask)
        signal.signal(signal.SIGHUP, receiveSignal)
        signal.signal(signal.SIGINT, receiveSignal)
        signal.signal(signal.SIGQUIT, receiveSignal)
        signal.signal(signal.SIGILL, receiveSignal)
        signal.signal(signal.SIGTRAP, receiveSignal)
        signal.signal(signal.SIGABRT, receiveSignal)
        signal.signal(signal.SIGBUS, receiveSignal)
        signal.signal(signal.SIGFPE, receiveSignal)
        #signal.signal(signal.SIGKILL, receiveSignal)
        signal.signal(signal.SIGUSR1, receiveSignal)
        signal.signal(signal.SIGSEGV, receiveSignal)
        signal.signal(signal.SIGUSR2, receiveSignal)
        signal.signal(signal.SIGPIPE, receiveSignal)
        signal.signal(signal.SIGALRM, receiveSignal)
        signal.signal(signal.SIGTERM, receiveSignal)
