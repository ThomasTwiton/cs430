"""Python Web server implementation"""
from socket import socket, AF_INET, SOCK_STREAM
from datetime import datetime
import sys

server = socket(AF_INET, SOCK_STREAM)

ADDRESS = "127.0.0.2"  # Local client is going to be 127.0.0.1
PORT = 4300  # Open http://127.0.0.2:4300 in a browser
LOGFILE = "webserver.log"


def main():
    """Main loop"""
    #create server socket
    server.bind((ADDRESS, PORT))
    server.listen(1)
    while True:
        #get the info
        conn, addr = server.accept()
        client_address = addr[0]
        data = conn.recvfrom(1024)

        #process the info
        #first line
        datalist = str(data[0]).split('\\r\\n')
        if len(datalist) < 4: #sometimes Chrome sends me an empty string (b'')
            conn.sendall("HTTP/1.1 404 Not Found \r\n \r\n".encode())
        else:
            first_line = datalist[0][2:]
            #print(datalist)
            print(first_line) 
            first_line = first_line.split()
            http_type = first_line[ 0]
            file_req =  first_line[1]
            version = first_line[2]

            #headers
            headers = {}
            for i in range(1, len(datalist)):
                keyval = datalist[i].split(':')
                if len(keyval) >= 2: #the last couple lines are junk
                    headers[keyval[0]] = keyval[1]

            #record to log file
            log = open(LOGFILE, 'a')
            log.write(str(datetime.now())+' | '+file_req+' | '+client_address+' | '+headers['User-Agent']+'\n')
            log.close()

            #if not a GET request, we don't know what to do
            if http_type != "GET":
                #return 405
                conn.sendall("HTTP/1.1 405 Method Not Allowed \r\n".encode())
            elif file_req != "/alice30.txt":
                #return 404
                conn.sendall("HTTP/1.1 404 Not Found \r\n".encode())
            else:
                #return the text file
                alice_file =  open("alice30.txt", 'r')
                alice = alice_file.read()  

                response = "HTTP/1.1 200 OK \r\n"
                response += ("Content-Length:" + str(len(alice)) + '\r\n')
                response += ("Content-Type: text/plain; charset=utf-8 \r\n")
                response += ("Date:" + str(datetime.now()) + '\r\n')
                response += ("Last-Modified: Wed Aug 29 11:00:00 2018 \r\n")
                response += ("Server: CS430-THOMAS \r\n")
                response += ("\r\n\r\n")
                response += alice
                conn.sendall(response.encode())
        conn.close()

    server.close()
    print("We did it")

if __name__ == "__main__":
    main()
