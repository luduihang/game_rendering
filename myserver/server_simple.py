import socket
import threading

import json
import time

from folder_manage import UserArchive
from game_room import GameRoom


class Server:
    def __init__(self, host='127.0.0.1', port=5000):
        self.host = host
        self.port = port
        self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.room_capacity = 3
        self.archive_manager = None
        self.room = GameRoom()
        self.user_id = 0

    def start(self):
        self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # 允许地址重用
        self.serversocket.bind((self.host, self.port))
        self.serversocket.listen()
        print(f"Server listening on {self.host}:{self.port}")
        threading.Thread(target=self.accept_connections).start()
        self.room.run()

    def accept_connections(self):
        while True:
            client_socket, client_address = self.serversocket.accept()
            print(f"接收到{client_address}的连接")
            threading.Thread(target=self.handle_client, args=(client_socket, client_address)).start()

    def handle_client(self, client_socket, client_address):
        message_dict = None
        quit_signal = False
        while True:
            data = client_socket.recv(1024)
            message = data.decode()
            message_dict = json.loads(message)
            print("获取到用户的登录信息:", message_dict)
            if message_dict.get("action") == "login":
                login_success = self.handle_login(client_socket, message_dict)
                if login_success:
                    break  # 登录成功后退出循环
            elif message_dict.get("action") == "register":
                self.handle_register(client_socket,message_dict)
            elif message_dict.get("action") == "exit":
                print(f"{client_address}连接断开")
                json_str = {
                    'action': 'disconnect',
                }
                json_str = json.dumps(json_str)
                client_socket.send(json_str.encode())
                client_socket.close()
                quit_signal = True
                break
        if not quit_signal:
            time.sleep(0.1)
            self.assign_room(client_socket, client_address,message_dict)

    def handle_register(self,client_socket, message_dict):
        if self.archive_manager is not None:
            del self.archive_manager
        self.archive_manager = UserArchive('folder/user_folder.json')

        username = message_dict.get("username")
        password = message_dict.get("password")
        nickname = message_dict.get("nickname")
        gender = message_dict.get("gender")
        if not username or not password or not nickname or gender not in ["male", "female"]:
            print("注册信息不完整或性别参数有误")

        elif self.archive_manager.load_user_archive(username, password):

            print("用户名已存在")
            message = {
                "folder_build": "False"
            }
            time.sleep(0.2)
            client_socket.send(json.dumps(message).encode())

        else:
            self.archive_manager.create_user_archive(message_dict.get("username"),
                                                     message_dict.get("password"),
                                                     message_dict.get("nickname"),
                                                     message_dict.get("gender"))
            print("存档建立成功！")
            message = {
                "folder_build": "True"
            }
            client_socket.send(json.dumps(message).encode())
    def handle_login(self, client_socket, message_dict):
        if self.archive_manager is not None:
            del self.archive_manager
        self.archive_manager = UserArchive('folder/user_folder.json')
            # 登录逻辑
        if self.archive_manager.load_user_archive(message_dict.get("username"),message_dict.get("password")):
            if self.archive_manager.load_user_archive(message_dict.get("username"),
                                                      message_dict.get("password"))["locked"] == "False":
                print("密码验证通过！准备匹配进入房间")
                user_agent = self.archive_manager.load_user_archive(message_dict.get("username"),
                                                                    message_dict.get("password"))
                message = {
                    "action_back": "True"
                }
                self.archive_manager.update_user_archive(message_dict.get("username"),locked='True')
                message.update(user_agent)
                time.sleep(0.1)
                client_socket.send(json.dumps(message).encode())
                print("已经发送了",message)
                return True
            elif self.archive_manager.load_user_archive(message_dict.get("username"),
                                                      message_dict.get("password"))["locked"] == "True":
                user_agent = self.archive_manager.load_user_archive(message_dict.get("username"),
                                                                   message_dict.get("password"))
                message = {
                    "action_back": "Locked"
                }
                message.update(user_agent)
                time.sleep(0.1)
                client_socket.send(json.dumps(message).encode())
                print("已经发送了", message)
                print("此账号已经被登录了")
                return False
        else:
            message = {
                "action_back": "False"
            }
            client_socket.send(json.dumps(message).encode())
            print("登录失败，请重新登录")
            return False

    def assign_room(self,client_socket,client_address,message_dict):
        print("调试1")
        if not self.room.is_running:
            print("调试3")
            self.room.is_running = True
        self.room.add_client_signal = True
        self.room.add_client(client_socket, str(self.user_id),message_dict.get("username"),message_dict.get("password"))

        print("调试2")
        print("当前用户id是:", str(self.user_id))
        self.user_id += 1
    def stop(self):
        self.room.is_running = False



