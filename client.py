#!/usr/bin/env python3
from time import sleep

import argparse
import json
import logging
import queue
import socket
import sys
import threading
import traceback


BUF_SIZE=1024
TIMEOUT = 1


class UDPWithExtraStepsClient():
    def __init__(self, host, port, buf_size=BUF_SIZE, timeout=TIMEOUT):
        self.buf_size = buf_size
        self.timeout = timeout
        self.host = host
        self.port = port
        logging.info("set socket")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.seq = 0
        self.queue = queue.Queue()


    def create_packet(self, data):
        packet = {
                'data': data,
                'seq': self.seq
                }
        return json.dumps(packet)


    def receive_ack(self, seq, success):
        ack, address = self.sock.recvfrom(BUF_SIZE)
        host, port = address
        data = ack.decode("utf-8")
        packet = json.loads(data)
        success = seq == packet['seq']
        print(success, seq, packet['seq'])


    def receive_ack_with_timeout(self, seq, timeout):
        fl = False
        thread = threading.Thread(target=self.receive_ack, args=(seq, fl))
        logging.info("waiting for ack, seq: %d", seq)
        thread.start()
        thread.join(timeout)
        print(fl)
        return fl


    def send_with_retry(self, data):
        timeout = self.timeout

        packet = self.create_packet(data)
        packet = packet.encode('utf-8')
        num = None
        while True:
            num = self.sock.sendto(packet, (self.host, self.port))
            if self.receive_ack_with_timeout(self.seq, timeout):
                break
            timeout *= 2
            if timeout > 30:
                timeout = 30
            logging.warn("retry with %d s timeout", timeout)
        self.seq += 1
        logging.info("%d bytes sent", num)


    def send(self, data):
        for batch in getBatches(data, BUF_SIZE):
            self.send_with_retry(data)



    def shutdown(self):
        self.sock.close()
        exc = sys.exc_info()
        logging.info("client shutdown: %s", exc)
        traceback.print_exception(*exc)


def getBatches(data, buf_size):
    num_batches = len(data) // buf_size
    if len(data) % buf_size > 0:
        num_batches += 1

    res = list()
    for i in range(num_batches):
        if i == num_batches - 1:
            res.append(data[i * buf_size:])
        else:
            res.append(data[i * buf_size:(i+1) * buf_size])
    return res


def runClient(host, port, without_user):
    client = UDPWithExtraStepsClient(host, port)
    logging.info("send messages")
    while True:
        try:
            data = ""
            if without_user:
                with open("/client/poem", "r") as f:
                    for line in f:
                        data += line
                sleep(5)
            else:
                data = input("Your message: ")
            client.send(data)
        except:
            client.shutdown()
            return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='http server doing something.')
    parser.add_argument("--without_user", default=False, help="Flag for tests without user.", action='store_true')
    parser.add_argument("--host", default="127.0.0.1", help="Host where server located.")
    parser.add_argument("-p", "--port", type=int, default=8080, help="Post which server is listen to")
    parser.add_argument("--log-level", default=logging.INFO, type=lambda x: getattr(logging, x), help="Configure the logging level.")
    args = parser.parse_args()
    logging.basicConfig(level=args.log_level)

    runClient(args.host, args.port, args.without_user)
