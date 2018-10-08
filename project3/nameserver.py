'''
DNS Name Server
'''
#!/usr/bin/env python3

import sys
from random import randint, choice
from socket import socket, SOCK_DGRAM, AF_INET


HOST = "localhost"
PORT = 43053

DNS_TYPES = {
    1: 'A',
    2: 'NS',
    5: 'CNAME',
    12: 'PTR',
    15: 'MX',
    16: 'TXT',
    28: 'AAAA'
}

TTL_SEC = {
    '1s': 1,
    '1m': 60,
    '1h': 60*60,
    '1d': 60*60*24,
    '1w': 60*60*24*7,
    '1y': 60*60*24*365
    }


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


def get_left_bits(bytes_lst: list, n_bits: int) -> int:
    '''Extract left n bits of a two-byte sequence'''
    val = bytes_to_val(bytes_lst)

    binstring = '0b' + ''.join(['1'] * n_bits + ['0'] * (16-n_bits))
    
    return (val & int(binstring, 2)) >> (16-n_bits)


def get_right_bits(bytes_lst: list, n_bits) -> int:
    '''Extract right n bits bits of a two-byte sequence'''
    val = bytes_to_val(bytes_lst)

    binstring = '0b' + ''.join(['0'] * (16-n_bits) + ['1'] * n_bits)
  
    return int(('0b'+(bin(val & int(binstring, 2))[2:])),2)


def read_zone_file(filename: str) -> tuple:
    '''Read the zone file and build a dictionary'''
    zone = dict()
    with open(filename) as zone_file:
        origin = zone_file.readline().split()[1].rstrip('.')
        default = TTL_SEC[zone_file.readline().split()[1].rstrip('.')]

        domain = ''
        answers = []
        for line in zone_file:
            record = line.split()
            #print(line.split())
            if record[0] not in TTL_SEC and record[0] != 'IN':
                domain = record[0]
                answers = []
                if record[1] != 'IN':
                    ttl = TTL_SEC[record[1]]
                    rec_class = record[2]
                    rec_type = record[3]
                    rec_address = record[4]
                    answers.append((ttl, rec_class, rec_type, rec_address))
                else:
                    ttl= default
                    rec_class = record[1]
                    rec_type = record[2]
                    rec_address = record[3]
                    answers.append((ttl, rec_class, rec_type, rec_address))
            elif record[0] != 'IN':
                ttl = TTL_SEC[record[0]]
                rec_class = record[1]
                rec_type = record[2]
                rec_address = record[3]
                answers.append((ttl, rec_class, rec_type, rec_address))
            else:
                ttl= default
                rec_class = record[0]
                rec_type = record[1]
                rec_address = record[2]
                answers.append((ttl, rec_class, rec_type, rec_address))
            zone[domain] = answers
    #print(zone)
    return (origin, zone)


def parse_request(origin: str, msg_req: bytes) -> tuple:
    '''Parse the request'''
    request_string = msg_req.hex()
    request_list_str16 = [request_string[i:i+2] for i in range(0, len(request_string),2)]
    request_list_10 = [int(request_list_str16[i],16) for i in range(0, len(request_list_str16))]

    trans_id = bytes_to_val(request_list_10[0:2])

    index = 12
    domains = []
    while request_list_10[index] != 0:
        name_length = request_list_10[index]
        name_string = (request_list_10[index+1:(index + name_length +1)])
        name_string = [chr(name_string[i]) for i in range(0, len(name_string))]
        domains.append(''.join(name_string))

        index = index+name_length+1
    
    if '.'.join(domains[-3:]) != origin:
        raise ValueError('Unknown zone')
    
    domain = domains[0]
    
    req_type = bytes_to_val(request_list_10[index+1:index+3])
    if req_type not in DNS_TYPES:
        raise ValueError('Unknown query type')

    if bytes_to_val(request_list_10[index+3:index+5]) != 1:
        raise ValueError('Unknown class')
    
    query = bytes(request_list_10[12:])

    return (trans_id, domain, req_type, query)
    


def format_response(zone: dict, trans_id: int, qry_name: str, qry_type: int, qry: bytearray) -> bytearray:
    '''Format the response'''
    response = bytearray()
    answers = zone[qry_name]
    print(answers)
    #trans id
    trans_id = randint(0,65535)
    response.extend(val_to_bytes(trans_id, 2))

    #flags(8180), questions(0001), answers (varies), authority and additional (2x 0000)
    response.extend([129,128,0,1])

    num_answers = 0
    for answer in answers:
        if answer[2] == DNS_TYPES[qry_type]:
            num_answers+=1
    response.extend(val_to_bytes(num_answers,2))

    response.extend([0,0,0,0])

    #original query
    response.extend(qry)

    #answers
    for answer in answers:
        if answer[2] == DNS_TYPES[qry_type]:
            #print(answer)
            #name pointer
            response.extend([192, 12])
            #type
            if answer[2] == 'A':
                response.extend([0,1])
            elif answer[2] == 'AAAA':
                response.extend(val_to_bytes(28,2))
            else:
                raise ValueError('Unknown query type')
            #class
            if answer[1] == 'IN':
                response.extend([0,1])
            else:
                raise ValueError('Unknown class')
            #ttl
            response.extend(val_to_bytes(answer[0],4))
            #datalength and address
            if answer[2] == DNS_TYPES[1]:
                ip4 = answer[3].split('.')
                data_length = len(ip4)
                ip4 = [int(ip4[i]) for i in range(0, data_length)]
                response.extend(val_to_bytes(data_length,2))
                for i in range(0, data_length):
                    response.extend(val_to_bytes(ip4[i], 1))
            elif answer[2] == DNS_TYPES[28]:
                ip6 = answer[3].split(':')
                data_length = len(ip6)
                print(ip6)
                ip6 = [int(ip6[i],16) for i in range(0, data_length)]
                print(ip6)
                response.extend(val_to_bytes(data_length*2,2))
                for i in range(0, len(ip6)):
                    response.extend(val_to_bytes(ip6[i], 2))
            else:
                raise ValueError('Unknown address type')
    
    print(response)
    return response


def run(filename: str) -> None:
    '''Main server loop'''
    server_sckt = socket(AF_INET, SOCK_DGRAM)
    server_sckt.bind((HOST, PORT))
    origin, zone = read_zone_file(filename)
    print("Listening on %s:%d" % (HOST, PORT))

    while True:
        (request_msg, client_addr) = server_sckt.recvfrom(512)
        try:
            trans_id, domain, qry_type, qry = parse_request(origin, request_msg)
            msg_resp = format_response(zone, trans_id, domain, qry_type, qry)
            server_sckt.sendto(msg_resp, client_addr)
        except ValueError as ve:
            print('Ignoring the request: {}'.format(ve))
    server_sckt.close()


def main(*argv):
    '''Main function'''
    if len(argv[0]) != 2:
        print('Proper use: python3 nameserver.py <zone_file>')
        exit()
    run(argv[0][1])


if __name__ == '__main__':
    main(sys.argv)
