# server.py: simple HTTP server that serves the index.html web UI to any browser that connects to it

import socket
import sys

def start_server(host, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"Server started on {host}:{port}")

    while True:
        client_socket, addr = server_socket.accept()
        print(f"Connection from {addr}")
        handle_client(client_socket)
        
def handle_client(client_socket):
    with client_socket:
        request = client_socket.recv(1024).decode()
        print(request)
        
        with open("index.html", "r") as f:
            content = f.read()
        
        response = f"""HTTP/1.1 200 OK\r
Content-Type: text/html\r
Content-Length: {len(content)}\r
\r
{content}
"""

        client_socket.sendall(response.encode())
            
if __name__ == "__main__":
    HOST = '127.0.0.1'
    if len(sys.argv) > 1:
        PORT = int(sys.argv[1])
    else:
        PORT = 65432
    start_server(HOST, PORT)