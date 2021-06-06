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


BUF_SIZE=4096
TIMEOUT = 1


class UDPWithExtraStepsClient():
    def __init__(self, host, port, buf_size=BUF_SIZE, timeout=TIMEOUT):
        self.buf_size = buf_size
        self.timeout = timeout
        self.host = host
        self.port = port
        logging.info("set socket\n")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.seq = 0
        self.retry_queue = queue.Queue()
        self.ack_queue = queue.PriorityQueue()
        self._stop = threading.Event()
        self.retrier = None
        self.receiver = None


    def handshake(self):
        logging.info("setting connection")
        packet = self.create_packet("HSH", self.seq)
        encoded_packet = packet.encode("utf-8")
        logging.info("send handshake")
        num = self.sock.sendto(encoded_packet, (self.host, self.port))
        self.sock.setblocking(False)
        logging.info("sended handshake")
        timeout = self.timeout

        while True:
            sleep(timeout)
            logging.info("recv handshake")
            #TODO
            ack = self.sock.recv(BUF_SIZE)
            logging.info("recved handshake")
            data = ack.decode("utf-8")
            packet = json.loads(data)
            seq = packet['seq']
            if self.seq == seq:
                break
            logging.info("send handshake")
            num = self.sock.sendto(encoded_packet, (self.host, self.port))
            logging.info("sended handshake")
            timeout += 1
            if timeout > 10:
                timeout = 10
            logging.warning("retry with %d s timeout\n", timeout)
        logging.info("connection set")
        self.sock.setblocking(True)


    def start(self):
        self.handshake()
        self.retrier = threading.Thread(target=self.retry)
        self.receiver = threading.Thread(target=self.receive_ack)
        self.retrier.start()
        self.receiver.start()


    def create_packet(self, data, seq):
        packet = {
                'data': data,
                'seq': seq
                }
        packet['csum'] = sys.getsizeof(packet)
        return json.dumps(packet)


    def receive_ack(self):
        while not self._stop.is_set():
            ack = self.sock.recv(BUF_SIZE)
            #host, port = address
            data = ack.decode("utf-8")
            packet = json.loads(data)
            self.ack_queue.put(packet['seq'])
        #success = seq == packet['seq']
        #print(success, seq, packet['seq'])


    #def receive_ack_with_timeout(self, seq, timeout):
    #    fl = False
    #    thread = threading.Thread(target=self.receive_ack, args=(seq, fl))
    #    logging.info("waiting for ack, seq: %d", seq)
    #    thread.start()
    #    thread.join(timeout)
        #print(fl)
        #return fl


    def get_ack(self):
        ack = None
        try:
            ack = self.ack_queue.get(block=False)
            self.ack_queue.task_done()
        except queue.Empty:
            ack = None
        return ack


    def retry(self):
        while not self._stop.is_set():
            timeout = self.timeout

            #packet = self.create_packet(data, self.seq)
            packet = self.retry_queue.get()
            encoded_packet = packet.encode('utf-8')
            packet = json.loads(packet)
            while True:
                sleep(timeout)
                #if self.receive_ack_with_timeout(packet['seq'], timeout):
                #    break
                #self.receive_ack_with_timeout(packet['seq'], timeout)
                ack = self.get_ack()
                while ack is not None and ack < packet["seq"]:
                    ack = self.get_ack()

                if ack is not None:
                    if packet['seq'] == ack:
                        self.retry_queue.task_done()
                        break
                    self.ack_queue.put(ack)
                num = self.sock.sendto(encoded_packet, (self.host, self.port))
                timeout += 1
                if timeout > 10:
                    timeout = 10
                logging.warning("retry with %d s timeout %d seq\n", timeout, packet['seq'])
            #self.seq += 1


    # send each batch and add seq + data to queue
    def send(self, data):
        for batch in getBatches(data, BUF_SIZE):
            #self.send_with_retry(data)
            #self.queue.put(self.create_packet(batch, self.seq))
            packet = self.create_packet(batch, self.seq)
            encoded_packet = packet.encode("utf-8")
            num = self.sock.sendto(encoded_packet, (self.host, self.port))
            logging.info("%d bytes sent, %d seq\n", num, self.seq)
            self.retry_queue.put(packet)
            self.seq += 1


    def shutdown(self):
        self.ack_queue.join()
        self.retry_queue.join()
        self._stop.set()
        self.receiver.join()
        self.retrier.join()
        self.sock.close()
        exc = sys.exc_info()
        logging.info("client shutdown: %s\n", exc)
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
    client.start()
    logging.info("send messages\n")
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
