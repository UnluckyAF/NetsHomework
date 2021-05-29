#!/usr/bin/env python3

import argparse
import logging
import socket

BUF_SIZE=1024

def runServer(host, port):
    logging.info("set socket")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    logging.info("bind to %s:%d", host, port)
    sock.bind((host, port))

    logging.info("receive messages")
    while True:
        try:
            data = sock.recv(BUF_SIZE)
            logging.info("received %s", data.decode("utf-8"))
        except:
            sock.close()
            logging.info("server shutdown")
            return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='http server doing something.')
    parser.add_argument("--host", default="127.0.0.1", help="Host where server located.")
    parser.add_argument("-p", "--port", type=int, default=8080, help="Post which server is listen to")
    parser.add_argument("--log-level", default=logging.INFO, type=lambda x: getattr(logging, x), help="Configure the logging level.")
    args = parser.parse_args()
    logging.basicConfig(level=args.log_level)

    runServer(args.host, args.port)
