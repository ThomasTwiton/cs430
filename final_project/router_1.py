"""Router implementation using UDP sockets"""
#!/usr/bin/env python3
# encoding: UTF-8


import os
import random
import select
from socket import socket, AF_INET, SOCK_DGRAM
import struct
import sys
import time

HOST_ID = os.path.splitext(__file__)[0].split("_")[-1]
THIS_NODE = f"127.0.0.{HOST_ID}"
PORT = 4300
NEIGHBORS = set()
CONNECTED_NEIGHBORS = set()
ROUTING_TABLE = {}
TIMEOUT = 5
MESSAGES = [
    "Cosmic Cuttlefish",
    "Bionic Beaver",
    "Xenial Xerus",
    "Trusty Tahr",
    "Precise Pangolin"
]

def val_to_bytes(value: int, n_bytes: int) -> list:
    '''Split a value into n bytes'''
    bytelist = [None] * n_bytes
    for i in range(0, n_bytes):
        bytelist[n_bytes - 1 - i] = (value >> (8*i)) & 0xFF
    return bytelist


def bytes_to_val(bytes_lst: list) -> int:
    '''Merge n bytes into a value'''
    sum = 0
    for i in range(0, len(bytes_lst)):
        sum += bytes_lst[len(bytes_lst) - 1 - i] << (8*i)
    return sum

def read_file(filename: str) -> None:
    """Read config file"""
    #print(filename)
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
                ROUTING_TABLE[linelist[0]] = [int(linelist[1]), linelist[0]]
                line= f.readline()
            #print("OH WE DUN NKOW")
        else:
            line = f.readline()
    
    #print(NEIGHBORS)
    #print(ROUTING_TABLE)

    f.close()

def format_update():
    """Format update message"""
    update = bytearray()
    update.extend([0])

    for route in ROUTING_TABLE:
        address = route.split(".")
        #print(address)
        for byte in address:
            update.extend([int(byte)])
        
        cost = ROUTING_TABLE[route][0]
        update.extend([cost])

    #print(update)
    return update

def parse_update(msg, neigh_addr):
    """Update routing table"""
    updated = False
    for i in range (1, len(msg),5):
        record = msg[i:i+5]
        #print(record)
        address = []
        for j in range(4):
            byte = record[j]
            address.append(str(byte))
        address = '.'.join(address) 
        #print(address)

        cost = int(record[4])
        #print(cost)

        if address == THIS_NODE:
            #print("Don't do it")
            pass
        #if we didn't know how to get here before, add it to the routing table, assume the neighbor who told us about this node knows best
        elif address not in ROUTING_TABLE:
            ROUTING_TABLE[address] = [cost +ROUTING_TABLE[neigh_addr[0]][0], neigh_addr[0]]
            updated = True
            print(time.ctime()[-13:-5], "| Table updated with information from", neigh_addr[0])
        else:
            mycost = ROUTING_TABLE[address][0]
            newcost =cost + ROUTING_TABLE[neigh_addr[0]][0]

            if newcost < mycost:
                ROUTING_TABLE[address][0] = newcost
                ROUTING_TABLE[address][1] = neigh_addr[0]
                updated = True
                print(time.ctime()[-13:-5], "| Table updated with information from", neigh_addr[0])

    return updated
    



def send_update(node):
    """Send update"""
    update = format_update()
    router = socket(AF_INET, SOCK_DGRAM)
    router.bind((THIS_NODE, PORT))
    dest = (node, int('430'+node[-1]))
    #print(dest)
    router.sendto(update, (node, int('430'+node[-1])))
    router.close()


def format_hello(msg_txt, src_node, dst_node):
    """Format hello message"""
    hello = bytearray()
    hello.extend([1])

    src_address = src_node.split(".")
    for byte in src_address:
        hello.extend([int(byte)])

    dst_address = dst_node.split(".")
    for byte in dst_address:
        hello.extend([int(byte)])

    hello.extend(msg_txt.encode())

    return hello


def parse_hello(msg):
    """Send the message to an appropriate next hop"""
    src_bytes = msg[1:5]
    src_address = []
    for byte in src_bytes:
        src_address.append(str(byte))
    src_address = ".".join(src_address)

    dst_bytes = msg[5:9]
    dst_address = []
    for byte in dst_bytes:
        dst_address.append(str(byte))
    dst_address = ".".join(dst_address)

    msg_txt = msg[9:].decode()

    if dst_address == THIS_NODE:
        #this message belongs to us
        #print("THIS BELONGS TO US")
        print(time.ctime()[-13:-5], "| Received", msg_txt, "from", src_address)
    else:
        #print("FORWARDING ALONG")
        send_hello(msg_txt, src_address, dst_address)


def send_hello(msg_txt, src_node, dst_node):
    """Send a message"""
    hello = format_hello(msg_txt, src_node, dst_node)
    router = socket(AF_INET, SOCK_DGRAM)
    router.bind((THIS_NODE, PORT))   
    node_tosendto = ROUTING_TABLE[dst_node][1]  #via
    print(time.ctime()[-13:-5], "| Sending", msg_txt, "to", dst_node, "via", node_tosendto)
    port_tosendto = PORT + int(node_tosendto[-1])
    #print(port_tosendto)
    router.sendto(hello, (node_tosendto, port_tosendto))
    router.close()


def print_status():
    """Print status"""
    print("\t Host \t \t Cost \t Via")
    for route in ROUTING_TABLE:
        print("\t", route,  "\t", ROUTING_TABLE[route][0], "\t", ROUTING_TABLE[route][1])



def main(args: list):
    """Router main loop"""
    try:
        read_file(args[1])
    except:
        print(f"Usage: {args[0]} <configfile>")

    router = socket(AF_INET, SOCK_DGRAM)
    print(time.ctime()[-13:-5], "| Router", THIS_NODE , " here")
    RPORT = PORT + int(HOST_ID)
    print(time.ctime()[-13:-5], "| Binding to", THIS_NODE+':'+str(RPORT))
    router.bind((THIS_NODE, RPORT))    
    print(time.ctime()[-13:-5], "| Listening on", THIS_NODE+':'+str(RPORT))

    print_status()

    dummy = socket(AF_INET, SOCK_DGRAM) 
    
    inputs = [router]
    outputs = [dummy]
    hellos = 0

    while inputs:
        readable, writeable, exceptionable = select.select(inputs, outputs, [], TIMEOUT)

        for r in readable:
            #print('Reading')
            message, addr = r.recvfrom(2048)
            CONNECTED_NEIGHBORS.add(addr[0])
            if message[0] == 0:
                #print(addr)
                updated = parse_update(message, addr)
                if updated:
                    print_status() 
                    dummy = socket(AF_INET, SOCK_DGRAM)                    
                    outputs.append(dummy)
            elif message[0] == 1:
                parse_hello(message)
            else:
                print("Something is wrong")

        for r in writeable:
            #print("Writing")
            r.close()
            outputs.remove(r)
            for neighbor in NEIGHBORS:
                #print("Sending update to", neighbor)
                send_update(neighbor)

        for neighbor in NEIGHBORS:
            if neighbor not in CONNECTED_NEIGHBORS:
                dummy = socket(AF_INET, SOCK_DGRAM)                    
                outputs.append(dummy)

        if NEIGHBORS.issubset(CONNECTED_NEIGHBORS) and hellos < 2:
            msg_txt = random.choice(MESSAGES)
            dst_node = random.choice(tuple(CONNECTED_NEIGHBORS))
            if dst_node in CONNECTED_NEIGHBORS:
                send_hello(msg_txt, THIS_NODE, dst_node)
                hellos += 1     

        #time.sleep(1) 
                      
    router.close()


if __name__ == "__main__":
    main(sys.argv)
