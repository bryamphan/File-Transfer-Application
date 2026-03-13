# serv.py — FTP Server that listens for client connections and handles file commands (ls, get, put, quit) over a raw TCP socket, storing all files in the uploads/ folder.

import socket
import sys
import os
import threading

UPLOAD_DIR = "uploads"


def ensure_upload_dir():
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)


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


def handle_client(conn, addr):
    print(f"[+] Connected: {addr[0]}:{addr[1]}")
    try:
        while True:
            raw = recv_msg(conn)
            if raw is None:
                break

            message = raw.decode(errors="replace").strip()
            print(f"  [{addr[0]}] Command: {message}")

            # ── ls ──────────────────────────────────────────────────────────
            if message == "ls":
                files = []
                for fname in sorted(os.listdir(UPLOAD_DIR)):
                    fpath = os.path.join(UPLOAD_DIR, fname)
                    if os.path.isfile(fpath):
                        size = os.path.getsize(fpath)
                        files.append(f"{fname}  ({size:,} bytes)")
                listing = "\n".join(files) if files else "(no files on server)"
                send_msg(conn, listing)

            # ── get <filename> ──────────────────────────────────────────────
            elif message.startswith("get "):
                filename = os.path.basename(message[4:].strip())
                fpath = os.path.join(UPLOAD_DIR, filename)
                if not os.path.isfile(fpath):
                    send_msg(conn, "ERROR: File not found")
                else:
                    with open(fpath, "rb") as f:
                        file_data = f.read()
                    send_msg(conn, f"OK:{len(file_data)}")
                    ack = recv_msg(conn)
                    if ack and ack.decode() == "READY":
                        send_msg(conn, file_data)
                        print(f"  Sent: {filename} ({len(file_data):,} bytes)")

            # ── put <filename> ──────────────────────────────────────────────
            elif message.startswith("put "):
                filename = os.path.basename(message[4:].strip())
                send_msg(conn, "READY")
                file_data = recv_msg(conn)
                if file_data is None:
                    send_msg(conn, "ERROR: No data received")
                else:
                    save_path = os.path.join(UPLOAD_DIR, filename)
                    with open(save_path, "wb") as f:
                        f.write(file_data)
                    send_msg(conn, f"OK: Uploaded {filename} ({len(file_data):,} bytes)")
                    print(f"  Received: {filename} ({len(file_data):,} bytes)")

            # ── quit ─────────────────────────────────────────────────────────
            elif message == "quit":
                send_msg(conn, "Goodbye!")
                break

            else:
                send_msg(conn, f"ERROR: Unknown command '{message}'")

    except Exception as e:
        print(f"  Error with {addr}: {e}")
    finally:
        conn.close()
        print(f"[-] Disconnected: {addr[0]}:{addr[1]}")


def start_server(port):
    ensure_upload_dir()
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("", port))
    server_socket.listen(10)
    print(f"FTP Server listening on port {port}")
    print(f"Files stored in: {os.path.abspath(UPLOAD_DIR)}/")

    while True:
        conn, addr = server_socket.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
        thread.start()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python serv.py <PORT>")
        sys.exit(1)
    PORT = int(sys.argv[1])
    start_server(PORT)
