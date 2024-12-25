from server_simple import *

if __name__ == "__main__":
    server = Server('127.0.0.1', 5000)
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()  # 确保