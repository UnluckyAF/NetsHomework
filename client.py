#!/usr/bin/env python3
from time import sleep

import argparse
import logging
import socket
import sys

BUF_SIZE=1024


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
    logging.info("set socket")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

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

            for batch in getBatches(data, BUF_SIZE):
                batch = batch.encode('utf-8')
                num = sock.sendto(batch, (host, port))
                logging.info("%d bytes sent", num)
        except:
            sock.close()
            logging.info("client shutdown: %s", sys.exc_info())
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
