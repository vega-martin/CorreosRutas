import socket

HOST = '127.0.0.1'
PORT = 5001

def process_data(data):
    return f'Procesando datos'

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    print(f'Servidor escuchando en {HOST}: {PORT}')
    
    while True:
        conn, addr = s.accept()
        with conn:
            print(f'Conexion realizada desde {addr}')
            data = conn.recv(1024*1024*64) #64MB
            if data:
                result = process_data(data)
                conn.sendall(result.encode('utf-8'))