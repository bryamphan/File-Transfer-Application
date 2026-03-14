# File Transfer Application
### Socket Programming Project - CPSC 471

---

## Report

### Architecture Diagram

```
[ cli.py ] <---- TCP Socket ----> [ serv.py ]
                                       |
                                   uploads/
```

The client (`cli.py`) connects to the server (`serv.py`) over a TCP socket. The server stores and retrieves files from the `uploads/` directory.

---

### Socket Type

**TCP** (`socket.SOCK_STREAM`)

TCP was used because file transfer requires reliable, ordered delivery of data.

---

### Port Configuration

The port is passed as a command-line argument when starting the server and client:

```bash
python serv.py <PORT>
python cli.py <server> <PORT>
```

Example:
```bash
python serv.py 1234
python cli.py 127.0.0.1 1234
```

---

### Deployment Steps

1. Start the server:
   ```bash
   python serv.py 1234
   ```
2. Connect with the client:
   ```bash
   python cli.py 127.0.0.1 1234
   ```
3. Use the `ftp>` prompt to transfer files:
   ```
   ftp> ls
   ftp> put <filename>
   ftp> get <filename>
   ftp> quit
   ```

---

### Cloud Networking Setup (Phase Two)

1. Launch an AWS EC2 instance
2. Open the chosen port in the Security Group inbound rules (Custom TCP)
3. Run the server on the EC2 instance:
   ```bash
   python serv.py 1234
   ```
4. Connect from a local machine using the EC2 public IP:
   ```bash
   python cli.py <EC2-public-IP> 1234
   ```

---

## Authors
- Bryan Pham
- Ezra Gale
- Syon Chau
- Jordan Mai
- Ashley Park
