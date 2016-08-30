#! /usr/bin/env python
# coding=utf-8

import socket

HOST = '139.129.4.219'  # The remote host
PORT = 8082  # The same port as used by the server
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))

try:
    while True:
        message = raw_input('SEND < ')
        s.sendall(message + '\n')
        data = s.recv(1024)
        print 'RECV > ', repr(data)
except KeyboardInterrupt as e:
    s.close()
