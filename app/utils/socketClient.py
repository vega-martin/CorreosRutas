from config import HOST, PORT
import socket


def send_data_for_processing(data, host=HOST, port=PORT):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        s.sendall(data)
        response = s.recv(1024*1024*64)
    return response