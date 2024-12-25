import socket
import threading
import queue
import json
import time


from folder_manage import UserArchive
from card_deck import Cards, Cards_Value

option = ["2","5","10","20","50","100","弃牌","看牌"]

def simple_state_json(user_id,message):
    json_message = {
        "id": user_id,
        "message": message
    }
    json_data =json.dumps(json_message)
    byte_data = json_data.encode('utf-8')
    return byte_data

class GameRoom:
    def __init__(self, room_id):
        self.room_id = room_id
        self.lock = threading.Lock()
        self.lock_plus = threading.Lock()
        self.lock_broadcast = threading.Lock()

        self.is_running = True
        self.max_clients = 3
        self.winner = -1
        self.round = 0
        self.rest_option = 0

        self.clients = {}  # 使用字典存储客户端和对应的用户ID 未来会将用户ID与客户端socket关联
        self.user_ids_list = []  # 列表存储用户ID，顺序与客户端加入的顺序相同
        self.client_data = {}  # 存储每个客户端发送的数据
        self.client_received = {}  # 存储每个客户端的数据接收标志位
        self.client_received_event = {}  # 初始化为空字典

        self.old_user_num = 0
        self.room_message = {}
        self.card_table = {"game_process": "preparing"}
        self.archive_manager = UserArchive('folder/user_folder.json')

        self.deck = Cards()

    def add_client(self, client_socket, user_id, username, password):
        with self.lock:
            if len(self.clients) < self.max_clients:
                user_inform = self.archive_manager.load_user_archive(username, password)
                print("用户的所有信息是:", user_inform)
                print("用户的金额是:", user_inform['money'])
                self.clients[user_id] = {"socket": client_socket, "username": username, "password": password,"money": user_inform['money']}
                self.card_table[user_id] = {"nickname": user_inform["nickname"],"gender":user_inform["gender"],"preparing": False,"money":user_inform["money"],"bet_money":0}

                self.client_received_event[user_id] = threading.Event()
                self.client_data[user_id] = None
                self.client_received[user_id] = False
                self.user_ids_list.append(user_id)  # 将新加入用户的ID添加到user_ids列表中

                time.sleep(0.2)
                with self.lock_broadcast:
                    self.broadcast({"action": "new_client", "id": user_id})
                # time.sleep(0.1)
                # self.broadcast(self.card_table)

                client_thread = threading.Thread(target=self.handle_client, args=(user_id,))
                client_thread.start()

                client_socket.send(simple_state_json(user_id, message="New client connected"))

                return True

            else:
                print(f"Room {self.room_id} is full. Cannot add more clients.")
                return False
    def remove_client(self, user_id):
        with self.lock:
            if user_id in self.clients:
                print(f"client {self.clients[user_id]} leave room {self.room_id}")
                del self.clients[user_id]
                del self.client_data[user_id]
                del self.client_received[user_id]
                del self.card_table[user_id]
                # time.sleep(0.1)
                self.user_ids_list.remove(user_id)  # 从user_ids列表中移除离开的用户ID
                # self.broadcast(self.card_table)

                if not self.clients:
                    self.is_running = False

    def broadcast(self, message, exclude=None):
        for user_id, client_info in self.clients.items():
            if user_id != exclude:
                try:
                    json_str = json.dumps(message)
                    client_info["socket"].send(json_str.encode())
                    print("send message:",message)
                except Exception as e:
                    print(f"Error sending to client {user_id}: {e}")
            # time.sleep(0.05)
    def handle_client(self, user_id):
        client_info = self.clients[user_id]
        client_socket = client_info["socket"]

        # try:
        while self.is_running:
            try:
                message = client_socket.recv(1024).decode()
                if not message:  # 如果没有数据接收到，客户端可能已经断开连接
                    print(f"Client {user_id} disconnected unexpectedly.")
                    # self.remove_client(user_id)
                    break
                try:
                    message_dict = json.loads(message)
                    if message_dict.get("action") == 'exit':
                        print(f"Client {user_id} requested to disconnect.")
                        self.remove_client(user_id)
                        print("断开客户端方式1")
                        json_str = {
                            'action': 'disconnect',
                        }
                        json_str = json.dumps(json_str)
                        client_socket.send(json_str.encode())
                        break
                    with self.lock_plus:
                        self.client_data[user_id] = message_dict
                        self.client_received[user_id] = True
                        self.client_received_event[user_id].set()

                    print(f"get message {message_dict} from client {user_id}")

                except json.JSONDecodeError:
                    print("json_JSONDecodeError")
            except socket.error as e:
                print(f"Socket error for client {user_id}: {e}")
                self.remove_client(user_id)
                print("断开客户端方式2")
                break
        # finally:
        #     self.remove_client(user_id)
        #     print("断开客户端方式3")
    def count_preparing_clients(self):
        count = 0
        for user_id in self.clients:
            if self.card_table[user_id].get("preparing") is True :
                count += 1
                print("好运来")
        return count

    def wait_for_ready(self):
        while self.is_running:
            if self.old_user_num != len(self.user_ids_list):
                with self.lock_broadcast:
                    self.broadcast(self.card_table)

            self.old_user_num = len(self.user_ids_list)
            for user_id in self.user_ids_list:
                if self.client_received[user_id]:
                    self.client_received[user_id] = False
                    print("放过我把")
                    with self.lock_plus:
                        if self.client_data.get(user_id) and "is_changed" in self.client_data[user_id] and "state" in self.client_data[user_id]:
                            client_ready_flag = self.client_data[user_id]["state"]
                            self.card_table[user_id]["preparing"] = client_ready_flag
                            print(f"收到用户 {user_id} 准备消息: {client_ready_flag}")
                            self.client_data[user_id] = None
                            self.client_received[user_id] = False
                        json_message = {
                            "game_process": "preparing",
                            "ready_clients": self.count_preparing_clients()
                        }
                        json_message.update(self.card_table)
                        with self.lock_broadcast:
                            self.broadcast(json_message)
            #这里必须要延时，不然客户端接受开始信息过于密集json解析会失败
            time.sleep(0.1)
            if len(self.clients) == self.max_clients:
                if all(self.card_table[user_id]["preparing"] for user_id in self.user_ids_list if user_id in self.clients):
                    print("all clients ready")
                    self.card_table["game_process"] = "starting"
                    time.sleep(0.5)
                    with self.lock_broadcast:
                        self.broadcast(self.card_table)
                    # time.sleep(0.1)
                    break
    def draw_cards(self):
        while self.is_running:
            self.deck.shuffle_deck()
            self.card_table["property"] = "table"
            self.card_table["all_bets"] = 0
            for user_id in self.clients:
                drawn_cards = self.deck.draw_cards(3)
                self.card_table[user_id]["bet_money"] += 1
                self.card_table[user_id]["money"] = self.card_table[user_id]["money"] - 1
                self.card_table[user_id]["cards"] = drawn_cards
                self.card_table["all_bets"] += 1
                self.card_table[user_id]["failure"] = False
                self.cards_value = Cards_Value(drawn_cards)
                self.card_table[user_id]["cards_value"] = self.cards_value.value
            time.sleep(0.5)
            with self.lock_broadcast:
                self.broadcast(self.card_table)
            self.deck.reset_deck()

    def place_bet(self):
        while self.is_running:
            user_lists_copy = self.user_ids_list
            for user_id in user_lists_copy:
                self.client_received_event[user_id].clear()
            while self.winner < 0:
                turn = self.round % len(user_lists_copy)
                user_id = user_lists_copy[turn]
                self.round += 1
                if user_lists_copy[turn] == -1:
                    continue
                active_users = [user_id for user_id in self.user_ids_list if user_id != -1]
                if len(active_users) == 1:
                    self.winner = active_users[0]
                    print("最终的胜利者id是:",self.winner)
                    self.card_table["game_process"] = "ending"
                    self.card_table["final_winner"] = self.winner
                    break

                self.card_table["whose_turn"] = user_lists_copy[turn]
                self.card_table["rest_option"] = self.rest_option
                self.card_table["game_process"] = "requesting"
                self.card_table["user_ids_list"] = user_lists_copy
                self.broadcast(self.card_table)
                time.sleep(0.5)
                # if self.client_received_event[user_id].is_set():
                #     print("怎么回事！！！")
                self.client_received_event[user_id].wait()
                if 0 <= self.client_data[user_id]["option"] <= 7:
                    client_option = self.client_data[user_id]["option"]
                    self.card_table["option"] = self.client_data[user_id]["option"]
                    self.card_table["target"] = self.client_data[user_id]["target"]
                    self.card_table["game_process"] = "inform"
                    self.broadcast(self.card_table)
                    time.sleep(1)
                    if 0 <= client_option <= 5:
                        print(f"用户{user_id}选择了押注{option[client_option]}")
                        if self.rest_option <= client_option:
                            self.rest_option = client_option
                            print(f"选项更新为{option[client_option]}之后选项")
                        self.card_table[user_id]["money"] = self.card_table[user_id]["money"] - int(option[client_option])
                        self.card_table[user_id]["bet_money"] += int(option[client_option])

                    elif client_option == 6:
                        print(f"用户{user_id}选择了弃牌")
                        self.card_table[user_id]["failure"] = True
                        user_lists_copy[turn] = -1

                    elif client_option == 7:
                        target_id = self.card_table["target"]
                        print(f"用户{user_id}选择了看牌{target_id}")
                        self.card_table[user_id]["money"] = self.card_table[user_id]["money"] - int(option[self.rest_option])
                        self.card_table[user_id]["bet_money"] += int(option[self.rest_option])
                        if self.card_table[user_id]["cards_value"] > self.card_table[target_id]["cards_value"]:
                            self.card_table[target_id]["failure"] = True
                            user_lists_copy[user_lists_copy.index(target_id)] = -1
                            print("挑战成功，被挑战者失败")
                            self.card_table["battle_win"] = True
                        else:
                            self.card_table[user_id]["failure"] = False
                            user_lists_copy[turn] = -1
                            print("挑战失败")
                            self.card_table["battle_win"] = False
                        self.card_table["game_process"] = "battle"
                        self.broadcast(self.card_table)
                        time.sleep(1)
                else:
                    print("option fail, something wrong!!!")
                self.client_received_event[user_id].clear()  # 重置事件状态，以便下次使用



    def run(self):
        try:
            print("已经建立房间，当前房间id:", self.room_id)
            while self.is_running:
                # time.sleep(10)
                time.sleep(0.5)
                self.wait_for_ready()
                time.sleep(0.5)
                self.draw_cards()
                time.sleep(2)
                self.place_bet()
                while self.is_running:
                    time.sleep(1)
        finally:
            self.is_running = False
            for client_socket in list(self.clients.keys()):
                self.remove_client(client_socket)
                print("断开客户端方式4")
            print(f"Room {self.room_id} closed due to no clients or manual stop.")

class Server:
    def __init__(self, host='127.0.0.1', port=5000):
        self.host = host
        self.port = port
        self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lock = threading.Lock()  # 创建一个锁对象
        self.lock_plus = threading.Lock()

        self.rooms = {}  # 用于存储所有活跃的游戏房间，字典的键是房间的唯一标识符 room_id，而值是 GameRoom 类的实例
        self.room_id_counter = 0  # 用于记录房间的id的数量
        self.user_id_counter = 0  # 全局用户ID计数器
        self.room_threads = []  # 用于跟踪房间处理线程
        self.room_capacity = 3

        self.archive_manager = UserArchive('folder/user_folder.json')
    def start(self):
        self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # 允许地址重用
        self.serversocket.bind((self.host, self.port))
        self.serversocket.listen()
        print(f"Server listening on {self.host}:{self.port}")
        threading.Thread(target=self.accept_connections).start()

    def accept_connections(self):
        while True:
            with self.lock:
                client_socket, client_address = self.serversocket.accept()
            print(f"接收到{client_address}的连接")
            threading.Thread(target=self.handle_client, args=(client_socket, client_address)).start()

    def handle_client(self, client_socket, client_address):
        try:
            message_dict = None
            quit_signal = False
            while True:
                data = client_socket.recv(1024)
                if not data:
                    pass
                    # break
                message = data.decode()
                message_dict = json.loads(message)
                if message_dict.get("action") == "login":
                    login_success = self.handle_login(client_socket, message_dict)
                    if login_success:
                        break  # 登录成功后退出循环
                elif message_dict.get("action") == "register":
                    self.handle_register(client_socket,message_dict)
                elif message_dict.get("action") == "exit":
                    print(f"{client_address}连接断开")
                    time.sleep(0.1)
                    json_str = {
                        'action': 'disconnect',
                    }
                    json_str = json.dumps(json_str)
                    client_socket.send(json_str.encode())
                    time.sleep(0.1)
                    client_socket.close()
                    quit_signal = True
                    break
            print(quit_signal)
            if not quit_signal:
                time.sleep(0.1)
                self.assign_room(client_socket, client_address, message_dict)

        except Exception as e:
            print(f"处理客户端{client_address}时发生错误: {e}")
            print("客户端断开连接")
            client_socket.close()


    def handle_register(self,client_socket, message_dict):
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
            time.sleep(0.2)
            client_socket.send(json.dumps(message).encode())

    def handle_login(self, client_socket, message_dict):
        # 登录逻辑
        if self.archive_manager.load_user_archive(message_dict.get("username"),
                                                  message_dict.get("password")):
            print("密码验证通过！准备匹配进入房间")
            user_agent = self.archive_manager.load_user_archive(message_dict.get("username"),
                                                                message_dict.get("password"))
            message = {
                "action_back": "True"
            }
            message.update(user_agent)
            time.sleep(0.1)
            client_socket.send(json.dumps(message).encode())
            return True
        else:
            message = {
                "action_back": "False"
            }
            client_socket.send(json.dumps(message).encode())
            print("登录失败，请重新登录")
            return False

    def assign_room(self, client_socket, client_address, message_dict):
        room = None
        with self.lock_plus:
            for room_id, r in self.rooms.items():
                if len(r.clients) < self.room_capacity:
                    room = r
                    new_room_signal = False
                    break

            # 如果所有房间都满了，创建一个新的房间
            if room is None:
                self.room_id_counter += 1
                new_room_id = self.room_id_counter
                room = GameRoom(new_room_id)
                self.rooms[new_room_id] = room
                new_room_signal = True

        time.sleep(0.1)
        user_id = self.add_user_to_room(room, client_socket, client_address, message_dict.get("username"),
                                        message_dict.get("password"))
        print("当前用户id是:",user_id)
        if user_id is not None:
            if "username" in message_dict and "password" in message_dict:
                if new_room_signal:
                    print('概率错误打卡点')
                    room_thread = threading.Thread(target=self.handle_room, args=(room,))
                    self.room_threads.append(room_thread)  # 添加到线程列表
                    room_thread.start()
        else:
            print("fail to get user_id")

    #此函数用于为服务器为所有新连接的用户分配一个唯一的id号
    def add_user_to_room(self, room, clientsocket, clientaddr, username,password):

        user_id = self.user_id_counter  # 获取当前用户ID
        self.user_id_counter += 1  # 递增用户ID计数器
        if room.add_client(clientsocket, user_id, username, password):
            print(f"User {clientaddr} added to room {room.room_id} with user ID {user_id}")
            return user_id  # 返回用户ID，以便调用者知道分配了哪个ID
        else:
            print(f"Room {room.room_id} is full. Cannot add user {clientaddr}")
            return None  # 如果房间已满，返回None

    def handle_room(self, room):
        # with self.lock:
        print("开始运行房间")
        room.run()
        #在 GameRoom 类的 run 方法中，如果房间中没有用户（即 self.clients 列表为空），则 run 方法会退出其循环，这通常意味着房间不再需要。
        #在这种情况下，run 方法的执行将结束，随后 handle_room 方法中的代码会执行，这将触发删除房间操作。
        with self.lock:
            if room.room_id in self.rooms:
                del self.rooms[room.room_id]

    def stop(self):
        with self.lock:
            self.serversocket.close()
            # 设置所有房间停止运行
            for room in self.rooms.values():
                room.is_running = False

            # 等待所有房间处理线程完成
            for room_thread in self.room_threads:
                room_thread.join()


if __name__ == "__main__":
    server = Server()
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()  # 确保在退出前调用 stop 方法