from client_draw_copy import Client

if __name__ == "__main__":
    host = '127.0.0.1'  # 标准回环地址
    port = 5000  # 服务器正在监听的端口
    client = Client(host, port)
    client.run()