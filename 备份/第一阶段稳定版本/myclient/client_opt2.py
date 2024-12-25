import socket
import json
import threading
import time

from log_in import LogIn,Client_Prepare,Client_Bet

class Client:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.client_socket = None
        self.received_data = None  # 存储接收到的数据
        self.data_received = threading.Event()  # 数据接收标志位
        self.receive_thread = None  # 接收数据的线程
        self.running = True  # 客户端运行状态标志位
        self.id = None
        self.player_ids = None

        self.Success_Log = False

        self.user_info = {}
        self.room_info = {}

        self.login_manager = LogIn()

    def connect(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((self.host, self.port))
        print(f"成功连接 {self.host}:{self.port}")
        self.receive_thread = threading.Thread(target=self.receive_data)
        self.receive_thread.start()
    def receive_data(self):
        while self.running:
            try:
                json_str = self.client_socket.recv(1024).decode()
                # if not json_str:  # 检查是否接收到空字符串
                #     print("Received empty string from myserver, closing connection.")
                #     break
                # 解析 JSON 字符串
                json_data = json.loads(json_str)
                self.received_data = json_data
                self.data_received.set()  # 设置数据接收标志位
                print("Received data:", self.received_data)
            except json.JSONDecodeError:
                print("Error decoding JSON from myserver.")
                print("Error decoding JSON from myserver.")
                self.running = False
            except Exception as e:
                print(f"An error occurred: {e}")
                self.running = False

    def user_login(self):
        # 创建并启动接收数据的线程
        while self.running:
            # 此部分为登录Login阶段。
            json_response = self.login_manager.show_main_menu()
            if json_response["action"] == 'exit':
                self.running = False
                break
            self.client_socket.send(json.dumps(json_response).encode())
            self.data_received.wait()
            if self.data_received.is_set():
                if self.received_data.get("folder_build"):
                    if self.received_data.get("folder_build") == "True":
                        print("存档建立成功")
                        self.Success_Log = False
                        self.data_received.clear()
                if self.received_data.get("action_back"):
                    if self.received_data.get("action_back") == "True":
                        print("登录成功")
                        self.Success_Log = True
                        if self.received_data.get("username") and self.received_data.get("password") and self.received_data.get(
                                "nickname") and self.received_data.get("gender") and self.received_data.get("money") is not None:
                            self.user_info.update(self.received_data)
                            print(f"成功获取数据库信息：{self.user_info}")
                        self.data_received.clear()
                    elif self.received_data.get("action_back") == "False":
                        print("登录失败，请重新登录")
                        self.Success_Log = False
                        self.data_received.clear()
                if self.Success_Log:
                    self.received_data.clear()
                    break
                self.data_received.clear()
    def get_id(self):
        self.data_received.clear()
        while self.running:
            self.data_received.wait()
            if self.data_received.is_set():
                if self.received_data["action"] == "new_client":  # 直接检查键是否存在
                    self.id = self.received_data['id']
                    print("获取己方id:",self.id)
                    self.data_received.clear()
                    break
                self.data_received.clear()
    def prepare_login(self):
        if self.running:
            self.data_received.clear()
            self.client_prepare = Client_Prepare(self.client_socket)
            self.client_prepare.show_main_menu(self.client_prepare.handle_choice)
        while self.running:
            self.data_received.wait()
            if self.data_received.is_set():
                if "game_process" in self.received_data:
                    if self.received_data['game_process'] == "preparing":
                        self.room_info.update(self.received_data)
                        print("数据刷新，当前房间情况:",self.room_info)
                    if self.received_data['game_process'] == "starting":
                        print("准备开始游戏")
                        self.client_prepare.close()
                        break
                self.data_received.clear()
    def game_initialization(self):
        time.sleep(0.1)
        self.data_received.clear()
        while self.running:
            self.data_received.wait()
            if self.data_received.is_set():
                self.user_info["card_deck"] = self.received_data[str(self.id)]["cards"]
                print("我的手牌是:", self.user_info["card_deck"])
                if self.player_ids is None:
                    self.player_ids = [key for key in self.received_data.keys() if key.isdigit()]
                    print("获取玩家的id列表:",self.player_ids)
            if self.user_info["card_deck"] and self.player_ids is not None:
                break
            self.data_received.clear()
    def game_cycle(self):
        self.data_received.clear()
        self.option_choice = Client_Bet(self.id,self.client_socket)
        while self.running:
            self.data_received.wait()
            if self.data_received.is_set():
                if self.received_data["game_process"] == "requesting":
                    if self.received_data["whose_turn"] == self.id:
                        print("刷新页面")
                        print("客户端准备做出选择")
                        rest_option = self.received_data["rest_option"]
                        user_ids_list = self.received_data["user_ids_list"]
                        self.option_choice.set_turn(int(rest_option),user_ids_list)
                        self.option_choice.Get_Send_Choice()
                if self.received_data["game_process"] == "inform":
                    print("刷新页面")
                    player_index = self.player_ids.index(str(self.received_data["whose_turn"]))
                    if self.received_data["option"] == 7:
                        player_target = self.player_ids.index(str(self.received_data["target"]))
                        print(f"玩家{player_index}看牌{player_target}")
                    if self.received_data["option"] == 6:
                        print(f"玩家{player_index}弃牌")
                    if 0 <= self.received_data["option"] <= 5:
                        money_input = self.option_choice.option[self.received_data["option"]]
                        print(f"玩家{player_index}押注{money_input}")
                if self.received_data["game_process"] == "battle":
                    print("刷新页面")
                    player_index = self.player_ids.index(str(self.received_data["whose_turn"]))
                    player_target = self.player_ids.index(str(self.received_data["target"]))
                    if self.received_data["battle_win"] :
                        battle_winner = player_index
                    else:
                        battle_winner = player_target
                    print(f"玩家{player_index}挑战{player_target}，{battle_winner}胜利！")
                self.data_received.clear()

    def send_disconnect_message(self):
        if self.client_socket:
            try:
                json_message = {
                    "action": 'exit'
                }
                self.send_id_message(json_message)

            except Exception as e:
                print(f"Error sending disconnect message: {e}")
    def send_id_message(self,message):
        if self.id is None:
            print("invalid id,please check connection")
            return False
        else:
            json_id = {
                "id": self.id
            }
            json_id.update(message)
            self.client_socket.send(json.dumps(json_id).encode())
    def close(self):
        self.send_disconnect_message()
        self.running = False
        if self.client_socket:
            self.client_socket.close()
            print("Connection closed.")
        if self.receive_thread:
            self.receive_thread.join(timeout=2)
            if self.receive_thread.is_alive():
                print("Receive thread did not terminate in time. Forcing shutdown.")
            print("Receive thread has been closed.")



    def run(self):
        try:
            self.connect()
            self.user_login()
            self.get_id()
            self.prepare_login()
            self.game_initialization()
            self.game_cycle()
            while self.running:
                time.sleep(0.1)
        finally:
            self.close()
# 使用客户端
if __name__ == "__main__":
    host = '127.0.0.1'  # 标准回环地址
    port = 5000  # 服务器正在监听的端口
    client = Client(host, port)
    client.run()
