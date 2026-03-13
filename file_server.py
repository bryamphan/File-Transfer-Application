# file_server.py — HTTP API server that powers the web UI, exposing endpoints to list, upload, download, and delete files stored in the uploads/ folder

import socket
import sys
import os
import threading
import json
import urllib.parse

UPLOAD_DIR = "uploads"


def ensure_upload_dir():
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)


def send_response(client_socket, status, content_type, body, extra_headers=""):
    if isinstance(body, str):
        body = body.encode()
    response = (
        f"HTTP/1.1 {status}\r\n"
        f"Content-Type: {content_type}\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"Access-Control-Allow-Origin: *\r\n"
        f"Access-Control-Allow-Methods: GET, POST, DELETE, OPTIONS\r\n"
        f"Access-Control-Allow-Headers: Content-Type\r\n"
        f"Connection: close\r\n"
        f"{extra_headers}"
        f"\r\n"
    ).encode() + body
    client_socket.sendall(response)


def handle_list_files(client_socket):
    files = []
    for fname in sorted(os.listdir(UPLOAD_DIR)):
        fpath = os.path.join(UPLOAD_DIR, fname)
        if os.path.isfile(fpath):
            size = os.path.getsize(fpath)
            files.append({"name": fname, "size": size})
    send_response(client_socket, "200 OK", "application/json", json.dumps(files))


def handle_upload(client_socket, headers, body_start, raw_data):
    content_length = 0
    content_type = ""
    for line in headers:
        if line.lower().startswith("content-length:"):
            content_length = int(line.split(":", 1)[1].strip())
        if line.lower().startswith("content-type:"):
            content_type = line.split(":", 1)[1].strip()

    # Read full body
    body = raw_data[body_start:]
    while len(body) < content_length:
        chunk = client_socket.recv(65536)
        if not chunk:
            break
        body += chunk

    # Parse multipart boundary
    boundary = None
    for part in content_type.split(";"):
        part = part.strip()
        if part.startswith("boundary="):
            boundary = part[len("boundary="):].strip().encode()
            break

    if not boundary:
        send_response(client_socket, "400 Bad Request", "text/plain", "Missing multipart boundary")
        return

    delimiter = b"--" + boundary
    parts = body.split(delimiter)
    saved = []

    for part in parts:
        if part in (b"", b"--\r\n", b"--"):
            continue
        if part.startswith(b"\r\n"):
            part = part[2:]
        if b"\r\n\r\n" not in part:
            continue

        header_section, file_data = part.split(b"\r\n\r\n", 1)
        if file_data.endswith(b"\r\n"):
            file_data = file_data[:-2]

        filename = None
        for h in header_section.decode(errors="replace").split("\r\n"):
            if "filename=" in h:
                fname_part = h.split("filename=", 1)[1]
                filename = fname_part.strip().strip('"').split('"')[0]
                break
        if not filename:
            continue

        safe_name = os.path.basename(filename)
        save_path = os.path.join(UPLOAD_DIR, safe_name)
        with open(save_path, "wb") as f:
            f.write(file_data)
        saved.append(safe_name)
        print(f"  Uploaded: {save_path} ({len(file_data):,} bytes)")

    if saved:
        send_response(client_socket, "200 OK", "application/json",
                      json.dumps({"message": f"Uploaded: {', '.join(saved)}"}))
    else:
        send_response(client_socket, "400 Bad Request", "text/plain", "No valid files found in request")


def handle_download(client_socket, filename):
    filename = urllib.parse.unquote(filename)
    safe_name = os.path.basename(filename)
    fpath = os.path.join(UPLOAD_DIR, safe_name)
    if not os.path.isfile(fpath):
        send_response(client_socket, "404 Not Found", "text/plain", "File not found")
        return
    with open(fpath, "rb") as f:
        file_data = f.read()
    extra = f"Content-Disposition: attachment; filename=\"{safe_name}\"\r\n"
    send_response(client_socket, "200 OK", "application/octet-stream", file_data, extra)
    print(f"  Downloaded: {safe_name} ({len(file_data):,} bytes)")


def handle_delete(client_socket, filename):
    filename = urllib.parse.unquote(filename)
    safe_name = os.path.basename(filename)
    fpath = os.path.join(UPLOAD_DIR, safe_name)
    if not os.path.isfile(fpath):
        send_response(client_socket, "404 Not Found", "text/plain", "File not found")
        return
    os.remove(fpath)
    send_response(client_socket, "200 OK", "application/json",
                  json.dumps({"message": f"{safe_name} deleted."}))
    print(f"  Deleted: {safe_name}")


def handle_client(client_socket, addr):
    try:
        raw_data = b""
        while b"\r\n\r\n" not in raw_data:
            chunk = client_socket.recv(4096)
            if not chunk:
                return
            raw_data += chunk

        header_end = raw_data.index(b"\r\n\r\n")
        header_bytes = raw_data[:header_end].decode(errors="replace")
        body_start = header_end + 4

        lines = header_bytes.split("\r\n")
        request_line = lines[0]
        headers = lines[1:]

        parts = request_line.split(" ")
        if len(parts) < 2:
            return
        method = parts[0]
        path = parts[1]

        print(f"[{addr[0]}:{addr[1]}] {method} {path}")

        # CORS preflight
        if method == "OPTIONS":
            send_response(client_socket, "204 No Content", "text/plain", "")
            return

        if method == "GET" and path == "/files":
            handle_list_files(client_socket)
        elif method == "POST" and path == "/upload":
            handle_upload(client_socket, headers, body_start, raw_data)
        elif method == "GET" and path.startswith("/download/"):
            handle_download(client_socket, path[len("/download/"):])
        elif method == "DELETE" and path.startswith("/delete/"):
            handle_delete(client_socket, path[len("/delete/"):])
        else:
            send_response(client_socket, "404 Not Found", "text/plain", "Not Found")

    except Exception as e:
        print(f"  Error handling {addr}: {e}")
    finally:
        client_socket.close()


def start_file_server(host, port):
    ensure_upload_dir()
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(10)
    print(f"File API server running on http://{host}:{port}")
    print(f"Files stored in: {os.path.abspath(UPLOAD_DIR)}/")

    while True:
        client_socket, addr = server_socket.accept()
        thread = threading.Thread(target=handle_client, args=(client_socket, addr), daemon=True)
        thread.start()


if __name__ == "__main__":
    HOST = "127.0.0.1"
    PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    start_file_server(HOST, PORT)
