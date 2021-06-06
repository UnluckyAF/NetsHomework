#!/usr/bin/env python3

import argparse
import json
import logging
import queue
import socket
import sys
import traceback

BUF_SIZE=4096


class UDPWithExtraStepsServer():
    def __init__(self, host, port, buf_size=BUF_SIZE):
        self.buf_size = buf_size
        logging.info("set socket")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        logging.info("bind to %s:%d", host, port)
        self.sock.bind((host, port))
        self.seq = 0
        self.seq_queue = queue.PriorityQueue()


    def create_ack_packet(self, seq):
        packet = {
                'seq': seq
                }
        return json.dumps(packet)


    def get_seq(self):
        seq = None
        try:
            seq = self.seq_queue.get(block=False)
            self.seq_queue.task_done()
        except queue.Empty:
            seq = None
        return seq


    def check_handshake(self, packet, address):
        if packet['data'] == "HSH":
            self.seq = packet['seq']
            self.seq_queue = queue.PriorityQueue()
            ack = self.create_ack_packet(packet['seq'])
            ack = ack.encode('utf-8')
            num = self.sock.sendto(ack, address)
            return True
        return False


    def check_sum(self, packet):
        tmp = {
                "data": packet["data"],
                "seq": packet["seq"]
                }
        if packet['csum'] != sys.getsizeof(tmp):
            return False
        return True


    def recv(self):
        json_data, address = self.sock.recvfrom(BUF_SIZE)
        data = json_data.decode("utf-8")
        packet = json.loads(data)
        logging.info("received %d seq", packet['seq'])
        if self.check_handshake(packet, address):
            return
        if not self.check_sum(packet):
            return

        ack = self.create_ack_packet(packet['seq'])
        ack = ack.encode('utf-8')
        num = self.sock.sendto(ack, address)
        logging.info("%d bytes ack sent, %d seq", num, packet['seq'])
        if packet['seq'] == self.seq:
            #logging.info("received %s", packet['data'])
            logging.info("received %d seq, mes: \n%s", packet['seq'], packet['data'])
            self.seq += 1
        elif packet['seq'] > self.seq:
            logging.info("saved %d seq", packet['seq'])
            self.seq_queue.put((packet['seq'], packet['data']))
            return
        else:
            logging.info("received old message %d", packet['seq'])
            return

        seq = self.get_seq()
        if seq is None:
            logging.info("seq is None, seq %d", self.seq)
        else:
            logging.info("seq %d, self.seq %d", seq[0], self.seq)
        while seq is not None and seq[0] < self.seq:
            logging.info("old %d seq", seq[0])
            seq = self.get_seq()
        while seq is not None and seq[0] == self.seq:
            logging.info("received %d seq, mes: \n%s", seq[0], seq[1])
            self.seq += 1
            while seq is not None and seq[0] < self.seq:
                logging.info("old %d seq", seq[0])
                seq = self.get_seq()
        if seq is not None:
            self.seq_queue.put(seq)

        

    def shutdown(self):
        self.seq_queue.join()
        self.sock.close()
        exc = sys.exc_info()
        logging.info("server shutdown: %s", exc)
        traceback.print_exception(*exc)


def runServer(host, port):
    server = UDPWithExtraStepsServer(host, port)
    logging.info("receive messages")
    while True:
        try:
            server.recv()
        except:
            server.shutdown()
            return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='http server doing something.')
    parser.add_argument("--host", default="127.0.0.1", help="Host where server located.")
    parser.add_argument("-p", "--port", type=int, default=8080, help="Post which server is listen to")
    parser.add_argument("--log-level", default=logging.INFO, type=lambda x: getattr(logging, x), help="Configure the logging level.")
    args = parser.parse_args()
    logging.basicConfig(level=args.log_level)

    runServer(args.host, args.port)
