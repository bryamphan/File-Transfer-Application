# cli.py: FTP Client that connects to the server and lets the user transfer files using an interactive ftp> prompt with commands: ls, get, put, and quit.

import socket
import sys
import os


def send_msg(sock, data):
    """Send a length-prefixed message."""
    if isinstance(data, str):
        data = data.encode()
    length = len(data)
    sock.sendall(length.to_bytes(8, byteorder="big") + data)


def recv_msg(sock):
    """Receive a length-prefixed message."""
    raw_len = recvall(sock, 8)
    if not raw_len:
        return None
    length = int.from_bytes(raw_len, byteorder="big")
    return recvall(sock, length)


def recvall(sock, n):
    """Receive exactly n bytes."""
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            return None
        data += chunk
    return data


def run_client(server, port):
    print(f"Connecting to {server}:{port} ...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((server, port))
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

    print(f"Connected to {server}:{port}")
    print('Type "help" for available commands.\n')

    try:
        while True:
            try:
                cmd = input("ftp> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nInterrupted. Disconnecting...")
                send_msg(sock, "quit")
                break

            if not cmd:
                continue

            # help
            if cmd == "help":
                print("  ls              - List files on the server")
                print("  get <filename>  - Download a file from the server")
                print("  put <filename>  - Upload a file to the server")
                print("  quit            - Disconnect and exit")
                continue

            # ls
            if cmd == "ls":
                send_msg(sock, "ls")
                response = recv_msg(sock)
                if response:
                    print(response.decode(errors="replace"))

            # get <filename>
            elif cmd.startswith("get "):
                filename = cmd[4:].strip()
                if not filename:
                    print("Usage: get <filename>")
                    continue
                send_msg(sock, f"get {filename}")
                response = recv_msg(sock)
                if response is None:
                    print("Error: No response from server.")
                    continue
                response_str = response.decode(errors="replace")
                if response_str.startswith("ERROR"):
                    print(response_str)
                elif response_str.startswith("OK:"):
                    file_size = int(response_str.split(":")[1])
                    send_msg(sock, "READY")
                    file_data = recv_msg(sock)
                    if file_data is None:
                        print("Error: Did not receive file data.")
                        continue
                    save_name = os.path.basename(filename)
                    with open(save_name, "wb") as f:
                        f.write(file_data)
                    print(f"Downloaded: {save_name} ({file_size:,} bytes)")

            # put <filename>
            elif cmd.startswith("put "):
                filename = cmd[4:].strip()
                if not filename:
                    print("Usage: put <filename>")
                    continue
                if not os.path.isfile(filename):
                    print(f"Error: Local file '{filename}' not found.")
                    continue
                with open(filename, "rb") as f:
                    file_data = f.read()
                basename = os.path.basename(filename)
                send_msg(sock, f"put {basename}")
                response = recv_msg(sock)
                if response and response.decode() == "READY":
                    send_msg(sock, file_data)
                    confirmation = recv_msg(sock)
                    if confirmation:
                        print(confirmation.decode(errors="replace"))
                else:
                    print("Error: Server not ready for upload.")

            # quit
            elif cmd == "quit":
                send_msg(sock, "quit")
                response = recv_msg(sock)
                if response:
                    print(response.decode())
                break

            else:
                print(f"Unknown command: '{cmd}'. Type 'help' for available commands.")

    finally:
        sock.close()
        print("Connection closed.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python cli.py <server machine> <port>")
        print("Example: python cli.py ecs.fullerton.edu 1234")
        sys.exit(1)
    SERVER = sys.argv[1]
    PORT = int(sys.argv[2])
    run_client(SERVER, PORT)
