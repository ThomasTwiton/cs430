'''
GEO TCP Client
'''
#!/usr/bin/env python3

from socket import socket, AF_INET, SOCK_STREAM

HOST = 'localhost'
PORT = 4300


def client():
    '''Main client loop'''
    with socket(AF_INET, SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall("Initial handshake".encode())
        data = s.recv(1024)
        print(data.decode())
        while data.decode() != ">BYE":
            request = input()
            s.sendall(request.encode())
            data = s.recv(1024)
            print(data.decode())
        s.close()
        #print("SAFE!")

def main():
    '''Main function'''
    client()


if __name__ == "__main__":
    main()
