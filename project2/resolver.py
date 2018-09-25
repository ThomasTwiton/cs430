#!/usr/bin/env python3

import sys
import struct
from random import randint, choice, seed
from socket import socket, SOCK_DGRAM, AF_INET


PORT = 53

DNS_TYPES = {
    'A': 1,
    'AAAA': 28,
    'CNAME': 5,
    'MX': 15,
    'NS': 2,
    'PTR': 12,
    'TXT': 16
}

PUBLIC_DNS_SERVER = [
    '1.0.0.1',  # Cloudflare
    '1.1.1.1',  # Cloudflare
    '8.8.4.4',  # Google
    '8.8.8.8',  # Google
    '8.26.56.26',  # Comodo
    '8.20.247.20',  # Comodo
    '9.9.9.9',  # Quad9
    '64.6.64.6',  # Verisign
    '208.67.222.222',  # OpenDNS
    '208.67.220.220'  # OpenDNS
]


def val_to_2_bytes(value: int) -> list:
    '''Split a value into 2 bytes'''
    bytelist = [None, None]
    bytelist[1] = value & 0xFF
    bytelist[0] = value >> 8 & 0xFF
    return bytelist

def val_to_n_bytes(value: int, n_bytes: int) -> list:
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

def get_2_bits(bytes_lst: list) -> int:
    '''Extract first two bits of a two-byte sequence'''
    return (bytes_lst[0] & 0xC0) >> 6

def get_offset(bytes_lst: list) -> int:
    '''Extract size of the offset from a two-byte sequence'''
    return ((bytes_lst[0] & 0x3f) << 8) + bytes_lst[1]

def parse_cli_query(filename, q_type, q_domain, q_server=None) -> tuple:
    '''Parse command-line query'''
    if q_type in ['A', 'AAAA']:
        parsed_type = DNS_TYPES[q_type]
    elif q_type in ['MX', 'CNAME', 'NS', 'PTR', 'TXT']:
        raise ValueError("Unknown query type")
    else:
        raise Exception("Invalid DNS type")

    parsed_domain = q_domain.split('.')

    if q_server == None:
        parsed_server = PUBLIC_DNS_SERVER[randint(0,9)]
    else:
        parsed_server = q_server

    return (parsed_type, parsed_domain, q_server)

def format_query(q_type: int, q_domain: list) -> bytearray:
    '''Format DNS query'''
    query = bytearray()

    #trans id
    trans_id = randint(0,65535)
    query.extend(val_to_2_bytes(trans_id))

    #flags(0100), questions(0001), RRs (3x 0000)
    query.extend([1,0,0,1,0,0,0,0,0,0])

    #domain name
    for domain in q_domain:
        query.extend([len(domain)])
        byte_domain = bytes(domain, 'utf-8')
        query.extend(byte_domain)
    query.extend([0])

    #type
    query.extend(val_to_2_bytes(q_type))

    #class IN
    query.extend([0,1])

    return query


def send_request(q_message: bytearray, q_server: str) -> bytes:
    '''Contact the server'''
    client_sckt = socket(AF_INET, SOCK_DGRAM)
    client_sckt.sendto(q_message, (q_server, PORT))
    (q_response, _) = client_sckt.recvfrom(2048)
    client_sckt.close()
    
    return q_response

def parse_response(resp_bytes: bytes):
    '''Parse server response'''
    print(get_offset(resp_bytes))
    

def parse_answers(resp_bytes: bytes, offset: int, rr_ans: int) -> list:
    '''Parse DNS server answers'''
    raise NotImplementedError

def parse_address_a(addr_len: int, addr_bytes: bytes) -> str:
    '''Extract IPv4 address'''
    raise NotImplementedError

def parse_address_aaaa(addr_len: int, addr_bytes: bytes) -> str:
    '''Extract IPv6 address'''
    raise NotImplementedError

def resolve(query: str) -> None:
    '''Resolve the query'''
    q_type, q_domain, q_server = parse_cli_query(*query[0])
    query_bytes = format_query(q_type, q_domain)
    response_bytes = send_request(query_bytes, q_server)
    answers = parse_response(response_bytes)
    print('DNS server used: {}'.format(q_server))
    for a in answers:
        print('Domain: {}'.format(a[0]))
        print('TTL: {}'.format(a[1]))
        print('Address: {}'.format(a[2]))

def main(*query):
    '''Main function'''
    if len(query[0]) < 3 or len(query[0]) > 4:
        print('Proper use: python3 resolver.py <type> <domain> <server>')
        exit()
    resolve(query)


if __name__ == '__main__':
    main(sys.argv)
