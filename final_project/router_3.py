"""Router implementation using UDP sockets"""
#!/usr/bin/env python3
# encoding: UTF-8


import os
import random
import select
import socket
import struct
import sys
import time

HOST_ID = os.path.splitext(__file__)[0].split("_")[-1]
THIS_NODE = f"127.0.0.{HOST_ID}"
PORT = 4300
NEIGHBORS = set()
ROUTING_TABLE = {}
TIMEOUT = 5
MESSAGES = [
    "Cosmic Cuttlefish",
    "Bionic Beaver",
    "Xenial Xerus",
    "Trusty Tahr",
    "Precise Pangolin"
]

def read_file(filename: str) -> None:
    """Read config file"""
    f = open(filename, 'r')
    #print(THIS_NODE)

    line = f.readline()
    while line != '':
        #print(line)
        if line.strip() == THIS_NODE:
            #print("ITS A ME! MAAAAAAAAAAARIO!")
            line = f.readline()
            while line != '\n' and line != '':
                #print(line)
                linelist = line.split()
                #print(linelist)
                NEIGHBORS.add(linelist[0])
                ROUTING_TABLE[linelist[0]] = [int(linelist[1]), THIS_NODE]
                line= f.readline()
            #print("OH WE DUN NKOW")
        else:
            line = f.readline()
    
    print(NEIGHBORS)
    print(ROUTING_TABLE)

    f.close()

def format_update():
    """Format update message"""
    raise NotImplementedError


def parse_update(msg, neigh_addr):
    """Update routing table"""
    raise NotImplementedError


def send_update(node):
    """Send update"""
    raise NotImplementedError


def format_hello(msg_txt, src_node, dst_node):
    """Format hello message"""
    raise NotImplementedError


def parse_hello(msg):
    """Send the message to an appropriate next hop"""
    raise NotImplementedError


def send_hello(msg_txt, src_node, dst_node):
    """Send a message"""
    raise NotImplementedError


def print_status():
    """Print status"""
    raise NotImplementedError


def main(args: list):
    """Router main loop"""
    read_file("network_1_config.txt")


if __name__ == "__main__":
    main(sys.argv)
