import os
import select
import socket
import struct
import sys
import time

#!/usr/bin/env python3
"""Python traceroute implementation"""

ECHO_REQUEST_CODE = 0
ECHO_REQUEST_TYPE = 8
MAX_HOPS = 30
TIMEOUT = 1
ATTEMPTS = 3

"""Print the packet bytes"""
def print_raw_bytes(pkt: bytes) -> None:
    for i in range(len(pkt)):
        sys.stdout.write("{:02x} ".format(pkt[i]))
        if (i + 1) % 16 == 0:
            sys.stdout.write("\n")
        elif (i + 1) % 8 == 0:
            sys.stdout.write("  ")
    sys.stdout.write("\n")

"""Calculate and return checksum"""    
def checksum(pkt: bytes) -> int:
    csum = 0
    count = 0
    count_to = (len(pkt) // 2) * 2

    while count < count_to:
        this_val = (pkt[count + 1]) * 256 + (pkt[count])
        csum = csum + this_val
        csum = csum & 0xFFFFFFFF
        count = count + 2

    if count_to < len(pkt):
        csum = csum + (pkt[len(pkt) - 1])
        csum = csum & 0xFFFFFFFF

    csum = (csum >> 16) + (csum & 0xFFFF)
    csum = csum + (csum >> 16)
    result = ~csum
    result = result & 0xFFFF
    result = result >> 8 | (result << 8 & 0xFF00)

    return result       

"""Format an Echo request"""
def format_request(icmp_type: int, icmp_code: int, req_id: int, seq_num: int) -> bytes:
    
    chk_header = struct.pack("bbHHh", icmp_type, icmp_code, 0, req_id, seq_num)
    data = struct.pack("d", time.time())

    calculated_checksum = socket.htons(checksum(chk_header + data))

    header = struct.pack(
        "bbHHh", icmp_type, icmp_code, calculated_checksum, req_id, seq_num
    )    

    return header + data

"""Send an Echo Request"""
def send_request(packet: bytes, addr_dst: str, ttl: int) -> socket:
    proto = socket.getprotobyname("icmp")
    my_icmp_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, proto)

    my_icmp_socket.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, struct.pack("I", ttl))

    my_icmp_socket.sendto(packet, (addr_dst, 1))

    return my_icmp_socket

"""Receive an ICMP reply"""
def receive_reply(open_socket: socket, timeout: int = 1) -> tuple:
    time_left = timeout
    started_select = time.time()
    what_ready = select.select([open_socket], [], [], time_left)
    how_long_in_select = time.time() - started_select
    if not what_ready[0]:
        raise TimeoutError("Request timed out")
    
    pkt_rcvd, addr = open_socket.recvfrom(1024)

    time_left = time_left - how_long_in_select
    if time_left <= 0:
        raise TimeoutError("Request timed out")

    return (pkt_rcvd, addr[0])

"""Parse an ICMP reply"""    
def parse_reply(packet: bytes) -> bool:
    expected_types = [0, 3, 11]

    icmp_data = packet[28:]
    icmp_header = packet[20:28]
    icmp_msg_type, icmp_msg_code, check_sum_rcvd, repl_id, sequence = struct.unpack(
        "bbHHh", icmp_header
    )

    if icmp_msg_type not in expected_types:
        raise ValueError(
            f"Incorrect type: {icmp_msg_type}. Expected {', '.join([str(x) for x in expected_types])}."
        )

    pseudo_header = bytearray()
    pseudo_header.extend(icmp_header[0:2])
    pseudo_header.append(0)
    pseudo_header.append(0)    
    pseudo_header.extend(icmp_header[4:])
    
    check_sum_comptd = checksum(pseudo_header + icmp_data)
    if check_sum_rcvd != socket.htons(check_sum_comptd):
        raise ValueError(f"Incorrect checksum: {check_sum_rcvd}")

    return True

"""Trace the route to a domain"""
def traceroute(hostname: str) -> None:
    my_id = os.getpid() & 0xFFFF
    delim = " "

    dest_addr = socket.gethostbyname(hostname)
    print(
        f"Tracing route to {hostname} [{dest_addr}] over a maximum of {MAX_HOPS} hops\n"
    )    
    
    for ttl in range(1, MAX_HOPS + 1):  
        print(f"{ttl:<5d}", end="")      
        for att in range(ATTEMPTS):
            received_success = 0
            parsed_success = 0
            to_error_msg = ""
            v_error_msg = ""

            packet = format_request(ECHO_REQUEST_TYPE, ECHO_REQUEST_CODE, my_id, att)
            time_sent = time.time()
            my_icmp_socket = send_request(packet, hostname, ttl)
            try:
                pkt_rcvd, responder = receive_reply(my_icmp_socket, TIMEOUT)
                received_success += 1
            except TimeoutError as te:
                to_error_msg = str(te)
                if to_error_msg:
                    print("{:>5s} {:2s}".format("TIME", " "), end="")
                continue
            try:
                parse_reply(pkt_rcvd)
                parsed_success += 1
            except ValueError as ve:
                v_error_msg = str(ve)
                if v_error_msg:
                    print("{:>5s} {:2s}".format("ERR", " "), end="")
                continue
            finally:
                my_icmp_socket.close()

            time_rcvd = time.time()
            rtt = (time_rcvd - time_sent) * 1000

            print(f"{rtt:>5.0f} ms", end="")            
        
        if to_error_msg:
            print(f"{delim:3s} {to_error_msg}")        
        elif v_error_msg:
             print(f"{delim:3s} {v_error_msg}")        
        else:               
            print(f"{delim:3s} {responder}")   

        if responder == dest_addr:
            break

    print("\nTrace complete.")
            
            
def main(args):
    try:
        traceroute(args[1])
    except IndexError:
        print(f"Usage: {args[0]} <hostname>")
        sys.exit(1)

if __name__ == "__main__":
    main(sys.argv)