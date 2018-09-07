'''
GEO TCP Server
'''
#!/usr/bin/env python3
from datetime import datetime
from socket import socket, AF_INET, SOCK_STREAM

FILE_NAME = 'geo_world.txt'
HOST = 'localhost'
PORT = 4300


def read_file(filename: str) -> dict:
    '''Read world territories and their capitals from the provided file'''
    print("Reading file...")
    
    starttime = datetime.now()
        
    world = dict()
    f = open(filename, 'r')
    for line in f:
        record = line.split('-')
        #print(record)
        country = record[0].rstrip()
        capital = record[1].strip()
        world[country] = capital
    #print(world)
    
    endtime = datetime.now()
    deltaT = endtime - starttime
    seconds = deltaT.microseconds * 10**(-6)
    
    print("Read in "+ str(seconds) + " seconds.")
    
    return world


def server(world: dict) -> None:
    '''Main server loop'''
    with socket(AF_INET, SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen(1)
        print('Listening on {}:{}'.format(HOST, PORT))
        
        conn, addr = s.accept()
        data = conn.recv(1024)
        print('Connected: {}'.format(addr[0]))  
        conn.sendall(">You are connected to the GEO101 server\n>Enter a country or BYE to quit".encode())
        
        #loop and a half--the half
        data = conn.recv(1024)
        request = data.decode()         
            
        while request != "BYE":
            print("User query: {}".format(request))
            if (request in world):
                conn.sendall(("+"+world[request] + "\n>Enter a country or BYE to quit").encode())
            else:
                conn.sendall("-There is no such country.\n>Enter a country or BYE to quit".encode())
            data = conn.recv(1024)
            request = data.decode()   
        print('Disconnected: {}'.format(addr[0]))
        conn.sendall(">BYE".encode())
        s.close()

def main():
    '''Main function'''
    world = read_file(FILE_NAME)
    server(world)


if __name__ == "__main__":
    main()
