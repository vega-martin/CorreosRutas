from app import create_app
import subprocess
import atexit

server = subprocess.Popen(['python3', 'server/server.py'])

def close_socket():
    print("Cerrando servidor de algoritmos")
    server.terminate()

atexit.register(close_socket)

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)