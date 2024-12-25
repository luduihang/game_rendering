import socket
import threading
import json
import time
import copy

from folder_manage import UserArchive
from card_deck import Cards, Cards_Value

option = ["10","20","50","100","弃牌","看牌"]

class GameRoom:
    def __init__(self):
        self.lock = threading.Lock()
        self.lock_plus = threading.Lock()
        self.lock_broadcast = threading.Lock()
        self.list_lock = threading.Lock()

        self.is_running = True
        self.max_clients = 3
        self.winner = -1
        self.round = 0
        self.how_much_game = 0

        self.rest_option = 0

        self.old_user_num = 0
        self.clients = {}  # 使用字典存储客户端和对应的用户ID 未来会将用户ID与客户端socket关联
        self.user_ids_list = []  # 列表存储用户ID，顺序与客户端加入的顺序相同
        self.client_data = {}  # 存储每个客户端发送的数据
        self.client_received = {}  # 存储每个客户端的数据接收标志位
        self.client_received_event = {}  # 初始化为空字典
        self.remove_once = {}

        self.card_table = {"game_process": "preparing"}

        self.archive_manager = UserArchive('folder/user_folder.json')
        self.deck = Cards()


        self.user_lists_copy = []
        self.card_table_copy ={}


        self.remove_client_event = threading.Event()
        self.remove_client_lock = threading.Lock()
        self.remove_client_signal = False

        self.add_client_event = threading.Event()
        self.add_client_lock = threading.Lock()
        self.add_client_signal = False

        self.timer_user_id = None
        self.choose_in_time = False

    def add_client(self, client_socket, user_id, username, password):
        self.add_client_event.wait()
        self.archive_manager = UserArchive('folder/user_folder.json')
        with self.add_client_lock:
            if len(self.clients) < self.max_clients:
                user_inform = self.archive_manager.load_user_archive(username, password)
                if user_inform is not None:
                    print("用户的金额是:", user_inform['money'])
                else:
                    print("没有找到用户信息或用户信息加载失败")
                self.clients[user_id] = {"socket": client_socket, "username": username, "password": password,
                                         "money": user_inform['money']}
                self.card_table[user_id] = {"nickname": user_inform['nickname'], "gender": user_inform["gender"], "preparing": False,
                                            "money": user_inform["money"], "bet_money": 0}

                self.client_received_event[user_id] = threading.Event()
                self.client_data[user_id] = None
                self.client_received[user_id] = False
                self.user_ids_list.append(user_id)  # 将新加入用户的ID添加到user_ids列表中
                self.remove_once[user_id] = True

                with self.lock_broadcast:
                    self.broadcast({"action": "new_client", "id": user_id})
                    time.sleep(0.2)
                    self.broadcast(self.card_table)
                client_thread = threading.Thread(target=self.handle_client, args=(user_id,))
                client_thread.start()
        self.add_client_signal = False

    def remove_client(self, user_id):
        self.remove_client_event.wait()
        print('999')
        with self.remove_client_lock:
            if user_id in self.clients:
                if self.remove_once[user_id]:
                    with self.list_lock:
                        self.user_ids_list.remove(user_id)  # 从user_ids列表中移除离开的用户ID
                        self.remove_once[user_id] = False
                    self.archive_manager.update_user_archive(self.clients[user_id]["username"], locked='False')
                    print(f"client {self.clients[user_id]} leave room")


                    del self.clients[user_id]
                    del self.client_data[user_id]
                    del self.client_received[user_id]
                    del self.card_table[user_id]


                    with self.lock_broadcast:
                        self.broadcast(self.card_table)
                if not self.clients:
                    # self.is_running = False
                    pass
            self.remove_client_event.clear()
            self.remove_client_signal = False

    def broadcast(self, message, exclude=None):
        for user_id, client_info in self.clients.items():
            if user_id != exclude:
                try:
                    json_str = json.dumps(message)
                    client_info["socket"].send(json_str.encode())
                    print("send message:",message)
                except Exception as e:
                    print(f"发生错误，发送给客户端{user_id}: {e}")

    def handle_client(self, user_id):
        client_info = self.clients[user_id]
        client_socket = client_info["socket"]
        while self.is_running:
            try:
                data = client_socket.recv(1024)
                if not data:
                    print(f"Client {user_id} disconnected.")
                    self.remove_client(user_id)
                    break

                # 将接收到的数据解码为字符串
                message = data.decode()
                message_dict = json.loads(message)
                print(f"get message {message_dict} from client {user_id}")

                if message_dict.get("action") == 'exit':
                    print(f"Client {user_id} requested to disconnect.")
                    json_str = json.dumps({'action': 'disconnect'})
                    client_socket.send(json_str.encode())
                    self.remove_client_signal = True
                    self.remove_client(user_id)
                    print("触发断开客户端连接")
                    break

                self.client_data[user_id] = message_dict
                self.client_received[user_id] = True
                self.client_received_event[user_id].set()
                self.choose_in_time = True
                print("接收到来自客户端的数据", message_dict)

            except Exception as e:
                print(f"An error occurred with client {user_id}: {e}")
                self.remove_client(user_id)
                break

    def count_preparing_clients(self):
        count = 0
        for user_id in self.clients:
            if self.card_table[user_id].get("preparing") is True :
                count += 1
        return count

    def back_to_ready(self):
        self.archive_manager = UserArchive('folder/user_folder.json')
        self.winner = -1
        self.rest_option = 0
        for user_id in self.user_ids_list:
            self.client_data[user_id] = None
            self.client_received[user_id] = False
            self.client_received_event[user_id].clear()
        self.card_table = {"game_process": "preparing"}
        for user_id in self.user_ids_list:
            username = self.clients[user_id]["username"]
            password = self.clients[user_id]["password"]
            user_inform = self.archive_manager.load_user_archive(username, password)
            self.card_table[user_id] = {"nickname": user_inform['nickname'], "gender": user_inform["gender"],
                                        "preparing": False,
                                        "money": user_inform["money"], "bet_money": 0}
        with self.lock_broadcast:
            self.broadcast(self.card_table)
            print("好讨厌")
    def wait_for_ready(self):
        while self.is_running:
            time.sleep(0.1)
            with self.remove_client_lock and self.add_client_lock:
                if len(self.user_ids_list) != 0 :
                    for user_id in self.user_ids_list:
                        time.sleep(0.1)
                        if self.client_received[user_id]:
                            if "action" in self.client_data[user_id]:
                                client_ready_flag = self.client_data[user_id]["state"]
                                self.card_table[user_id]["preparing"] = client_ready_flag
                                print(f"收到用户 {user_id} 准备消息: {client_ready_flag}")
                                self.client_data[user_id] = None
                                self.client_received[user_id] = False
                            with self.lock_broadcast:
                                self.broadcast(self.card_table)
                    if len(self.clients) == 0:
                        continue
                    time.sleep(0.1)
                    # print('222')
                    if len(self.clients) == self.max_clients:
                        if all(self.card_table[user_id]["preparing"] for user_id in self.user_ids_list if
                               user_id in self.clients):
                            print("all clients ready")
                            self.card_table["game_process"] = "starting"
                            time.sleep(0.5)
                            with self.lock_broadcast:
                                self.broadcast(self.card_table)
                            print('333')
                            break
                else:
                    time.sleep(1)
            if self.remove_client_signal == True:
                self.remove_client_event.set()
                time.sleep(0.1)
            if self.add_client_signal == True:
                self.add_client_event.set()
                time.sleep(0.1)

        print("为什么呀")
    def draw_cards(self):
        self.card_table_copy = copy.deepcopy(self.card_table)
        time.sleep(0.5)
        self.deck.shuffle_deck()
        self.card_table["all_bets"] = 0
        for user_id in self.clients:
            drawn_cards = self.deck.draw_cards_plus(3)
            self.card_table[user_id]["bet_money"] += 5
            self.card_table[user_id]["money"] = self.card_table[user_id]["money"] - 5
            self.card_table[user_id]["cards"] = drawn_cards
            self.card_table["all_bets"] += 5
            self.card_table[user_id]["failure"] = False
            self.cards_value = Cards_Value(drawn_cards)
            self.cards_value.Get_Value()
            self.card_table[user_id]["cards_value"] = self.cards_value.value
            self.card_table[user_id]["cards_type"] = self.cards_value.type
        time.sleep(0.1)
        with self.lock_broadcast:
            self.broadcast(self.card_table)
        self.deck.reset_deck()

    def place_bet(self):
        self.round = self.how_much_game % self.max_clients
        self.user_lists_copy = copy.deepcopy(self.user_ids_list)
        for user_id in self.user_lists_copy:
            if user_id != -1:
                self.client_received_event[user_id].clear()
        while self.winner < 0:
            turn = self.round % len(self.user_lists_copy)
            user_id = self.user_lists_copy[turn]
            self.round += 1
            if self.user_lists_copy[turn] == -1:
                continue
            active_users = [user_id for user_id in self.user_lists_copy if user_id != -1]
            if len(active_users) == 1:
                self.winner = int(active_users[0])
                print("最终的胜利者id是:",self.winner)
                self.card_table["game_process"] = "ending"
                self.card_table["final_winner"] = self.winner
                self.card_table[active_users[0]]['money'] = self.card_table[active_users[0]]['money'] + self.card_table["all_bets"]
                for user_id in self.user_ids_list:
                    self.archive_manager.update_user_archive(self.clients[user_id]["username"],money = self.card_table[user_id]["money"])
                with self.lock_broadcast:
                    time.sleep(0.5)
                    self.broadcast(self.card_table)
                    self.winner = -1
                break

            self.card_table["whose_turn"] = self.user_lists_copy[turn]
            self.card_table["rest_option"] = self.rest_option
            self.card_table["game_process"] = "requesting"
            # self.card_table["user_ids_list"] = self.user_lists_copy
            with self.lock_broadcast:
                time.sleep(0.5)
                self.broadcast(self.card_table)
            self.timer = threading.Timer(10.0, self.timeout_operation)
            self.timer_user_id = user_id
            self.timer.start()
            self.client_received_event[user_id].wait()
            if self.choose_in_time:
                self.timer.cancel()
                print("及时选择，中断定时器")
                self.choose_in_time = False
            if 0 <= self.client_data[user_id]["option"] <= 5:
                client_option = self.client_data[user_id]["option"]
                self.card_table["option"] = self.client_data[user_id]["option"]
                self.card_table["target"] = self.client_data[user_id]["target"]
                self.card_table["game_process"] = "inform"
                if 0 <= client_option <= 3:
                    print(f"用户{user_id}选择了押注{option[client_option]}")
                    if self.rest_option <= client_option:
                        self.rest_option = client_option
                        print(f"选项更新为{option[client_option]}之后选项")
                    self.card_table[user_id]["money"] = self.card_table[user_id]["money"] - int(option[client_option])
                    self.card_table[user_id]["bet_money"] += int(option[client_option])
                    self.card_table["all_bets"] += int(option[client_option])
                    with self.lock_broadcast:
                        time.sleep(0.5)
                        self.broadcast(self.card_table)
                elif client_option == 4:
                    print(f"用户{user_id}选择了弃牌")
                    self.card_table[user_id]["failure"] = True
                    self.user_lists_copy[turn] = -1
                    with self.lock_broadcast:
                        time.sleep(0.5)
                        self.broadcast(self.card_table)
                elif client_option == 5:
                    target_id = self.card_table["target"]
                    print(f"用户{user_id}选择了看牌{target_id}")
                    self.card_table[user_id]["money"] = self.card_table[user_id]["money"] - int(option[self.rest_option])
                    self.card_table[user_id]["bet_money"] += int(option[self.rest_option])
                    self.card_table["all_bets"] += int(option[self.rest_option])
                    if self.card_table[str(user_id)]["cards_value"] > self.card_table[str(target_id)]["cards_value"]:
                        self.card_table[str(target_id)]["failure"] = True
                        self.user_lists_copy[self.user_lists_copy.index(str(target_id))] = -1
                        print("挑战成功，被挑战者失败")
                        self.card_table["battle_win"] = True
                    else:
                        self.card_table[str(user_id)]["failure"] = True
                        self.user_lists_copy[turn] = -1
                        print("挑战失败")
                        self.card_table["battle_win"] = False
                    self.card_table["game_process"] = "battle"
                    with self.lock_broadcast:
                        self.broadcast(self.card_table)
                        time.sleep(2)
            self.client_received_event[user_id].clear()  # 重置事件状态，以便下次使用
            time.sleep(1.3)

    def timeout_operation(self):
        if self.timer_user_id:
            self.client_data[self.timer_user_id] = {
                "option": 4,
                "target": -1,
            }
            self.client_received[self.timer_user_id] = True
            self.client_received_event[self.timer_user_id].set()

    def run(self):
        try:
            while self.is_running:
                self.wait_for_ready()
                self.draw_cards()
                self.place_bet()
                time.sleep(5)
                print("回到准备阶段+++++++++++++++++++++++++++++++++++")
                self.back_to_ready()
                self.how_much_game += 1
                self.is_running= True
        finally:
            self.is_running = False
            for key, value in self.clients.items():
                print("断开客户端方式2")
                self.remove_client(self.clients[key]['socket'])