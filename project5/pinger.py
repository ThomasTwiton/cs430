"""Python Pinger"""
#!/usr/bin/env python3
# encoding: UTF-8

import binascii
import os
import select
import struct
import sys
import time
import socket
from statistics import mean, stdev

ECHO_REQUEST_TYPE = 8
ECHO_REPLY_TYPE = 0
ECHO_REQUEST_CODE = 0
ECHO_REPLY_CODE = 0
REGISTRARS = ["afrinic.net", "apnic.net", "arin.net", "lacnic.net", "ripe.net"]
# REGISTRARS = ["example.com"]


def print_raw_bytes(pkt: bytes) -> None:
    """Printing the packet bytes"""
    for i in range(len(pkt)):
        sys.stdout.write("{:02x} ".format(pkt[i]))
        if (i + 1) % 16 == 0:
            sys.stdout.write("\n")
        elif (i + 1) % 8 == 0:
            sys.stdout.write("  ")
    sys.stdout.write("\n")


def checksum(pkt: bytes) -> int:
    """Calculate checksum"""
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


def parse_reply(
    my_socket: socket.socket, req_id: int, timeout: int, addr_dst: str
) -> tuple:
    """Receive an Echo reply"""
    time_left = timeout
    while True:
        started_select = time.time()
        what_ready = select.select([my_socket], [], [], time_left)
        how_long_in_select = time.time() - started_select
        if what_ready[0] == []:  # Timeout
            raise TimeoutError("Request timed out after 1 sec")

        time_rcvd = time.time()
        pkt_rcvd, addr = my_socket.recvfrom(1024)
        if addr[0] != addr_dst:
            version_length = pkt_rcvd[0] #should be 4     
            ipheader_length = version_length & 0xF
            icmp_index = ipheader_length * 4
            rep_type = pkt_rcvd[icmp_index]
            if rep_type == 3: #type of 3 means Destination Unavailable
                #in the case of ripe.net
                #seems to be sent from 80.249.208.71 after 3 unsuccesful requests
                #not a Wrong Sender error, just ripe.net trying to tell us to shut up
                raise TimeoutError("Request timed out after 1 sec")
            raise ValueError(f"Wrong sender: {addr[0]}")
        # TODO: Extract ICMP header from the IP packet and parse it
        
        #print_raw_bytes(pkt_rcvd)

        #IPv4
        version_length = pkt_rcvd[0] #should be 4
        #print(version_length)
        version = version_length >> 4
        #print(version)
        ipheader_length = version_length & 0xF
        #print(ipheader_length)
        total_length = pkt_rcvd[2:4]
        ip_id = pkt_rcvd[4:6]
        ttl = pkt_rcvd[8]
        protocol = pkt_rcvd[9] #1 == ICMP
        ip_checksum = pkt_rcvd[10:12]
        dest_ip = pkt_rcvd[12:16] #who we pinged, technically the 'source' of this reply
        source_ip = pkt_rcvd[16:20] #us, techincally the 'destination' of this reply
        
        #ICMP 
        icmp_index = ipheader_length * 4
        rep_type = pkt_rcvd[icmp_index]
        #print(rep_type)
        if rep_type != ECHO_REPLY_TYPE:
            raise ValueError(f"Wrong type: {ECHO_REPLY_TYPE}")
        rep_code = pkt_rcvd[icmp_index + 1]
        #print(rep_code)
        if rep_code != ECHO_REPLY_CODE:
            raise ValueError(f"Wrong code: {ECHO_REPLY_CODE}")


        #ICMP checksum
        rep_checksum = pkt_rcvd[(icmp_index +2):(icmp_index+4)]
        packet_checksum = rep_checksum[0] * 16 ** 2 + rep_checksum[1]
        #print("Packet's checksum:", packet_checksum)
        pkt_precheck = pkt_rcvd[0:icmp_index+2] + pkt_rcvd[icmp_index+4:]
        #print(pkt_precheck)
        calc_checksum = checksum(pkt_precheck)
        #print("Calculated checksum:",calc_checksum)  
        if packet_checksum != calc_checksum:
            raise ValueError(f"Wrong checksum: {calc_checksum}")
        #print(rep_checksum)


        rep_id = pkt_rcvd[(icmp_index +4):(icmp_index +6)]
        #print(rep_id)
        rep_seq = pkt_rcvd[(icmp_index +6):(icmp_index+8)]
        #print(rep_seq)
        #rep_timestamp = pkt_rcvd[(icmp_index+8):(icmp_index+16)]
        #print(rep_timestamp)
                
        # DONE: End of ICMP parsing
        time_left = time_left - how_long_in_select
        if time_left <= 0:
            raise TimeoutError("Request timed out after 1 sec")
        
        dest_address = str(dest_ip[0]) + "." + str(dest_ip[1]) + "." + str(dest_ip[2]) + "." + str(dest_ip[3]) 
        packet_size = total_length[0] * 16**2 + total_length[1]
        sequence_num = rep_seq[0]
        rtt = round(how_long_in_select* 10**3, 2)  #in milliseconds

        reply = (dest_address, packet_size, rtt, ttl, sequence_num)
        #print(reply)
        return reply


def format_request(req_id: int, seq_num: int) -> bytes:
    """Format an Echo request"""
    my_checksum = 0
    header = struct.pack(
        "bbHHh", ECHO_REQUEST_TYPE, ECHO_REQUEST_CODE, my_checksum, req_id, seq_num
    )
    data = struct.pack("d", time.time())
    my_checksum = checksum(header + data)

    if sys.platform == "darwin":
        my_checksum = socket.htons(my_checksum) & 0xFFFF
    else:
        my_checksum = socket.htons(my_checksum)

    header = struct.pack(
        "bbHHh", ECHO_REQUEST_TYPE, ECHO_REQUEST_CODE, my_checksum, req_id, seq_num
    )
    packet = header + data
    return packet


def send_request(addr_dst: str, seq_num: int, timeout: int = 1) -> tuple:
    """Send an Echo Request"""
    result = None
    proto = socket.getprotobyname("icmp")
    my_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, proto)
    my_id = os.getpid() & 0xFFFF

    packet = format_request(my_id, seq_num)
    my_socket.sendto(packet, (addr_dst, 1))

    try:
        result = parse_reply(my_socket, my_id, timeout, addr_dst)
    except ValueError as ve:
        print(f"Packet error: {ve}")
    finally:
        my_socket.close()
    return result


def ping(host: str, pkts: int, timeout: int = 1) -> None:
    """Main loop"""
    # TODO: Implement the main loop
    print("---Ping",host,"(", socket.gethostbyname(host),") using Python--- \n")
    num_notdropped = 0
    rtt_list = []
    for i in range (1, pkts+1):
        try:
            result = send_request(socket.gethostbyname(host), i, timeout)
            dest_address, packet_size, rtt, ttl, sequence_num = result
            print(str(packet_size), "bytes from", dest_address, ": icmp_seq=", sequence_num, "TTL=", ttl, "time=", rtt, "ms")
            num_notdropped +=1
            rtt_list.append(rtt)
        except  TimeoutError as te:
            print(f"No response: Request timed out after", timeout, "sec") 

    print("\n---",host, "ping statistics---")
    print(str(pkts), "packets transmitted,", str(num_notdropped), "received,", (str(round(num_notdropped/pkts * 100)) + "% received"))
    if len(rtt_list) > 0:
        stat_string = str(min(rtt_list)) + "/" + str(round(mean(rtt_list),2)) + "/" + str(max(rtt_list)) + "/" + str(round(stdev(rtt_list),2))
        print("rtt min/avg/max/mdev =", stat_string, "ms\n")
    return


if __name__ == "__main__":
    for rir in REGISTRARS:
        ping(rir, 5)
