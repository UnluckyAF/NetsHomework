#!/usr/bin/env python3

import argparse
import json
import logging
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


    def create_ack_packet(self, seq):
        packet = {
                'seq': seq
                }
        return json.dumps(packet)


    def recv(self):
        json_data, address = self.sock.recvfrom(BUF_SIZE)
        data = json_data.decode("utf-8")
        packet = json.loads(data)
        
        ack = self.create_ack_packet(packet['seq'])
        ack = ack.encode('utf-8')
        num = self.sock.sendto(ack, address)
        logging.info("%d bytes ack sent", num)
        if packet['seq'] == self.seq:
            self.seq += 1

        logging.info("received %s", packet['data'])


    def shutdown(self):
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
