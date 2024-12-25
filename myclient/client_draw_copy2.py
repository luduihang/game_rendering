import socket
import algorithm
import json
import threading
import time
from key_handle import *

class Client:
    def __init__(self, host, port):
        self.mouse_handle = None
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
        self.close_once = False
        self.quit_signal = False


        # self.thread_lock = threading.Lock()
        self.user_info = {}
        self.room_info = {}

        self.time_to_choose = 10
        self.time_to_choose_copy = 10
        self.rt = RepeatedTimer(1, self.update_left_time)

    def connect(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((self.host, self.port))
        print(f"成功连接 {self.host}:{self.port}")

        self.receive_thread = threading.Thread(target=self.receive_data)
        self.receive_thread.start()
        self.signal_handler = threading.Thread(target=self.signal_handler)
        self.signal_handler.start()

    def receive_data(self):
        while self.running:
            json_str = self.client_socket.recv(2048).decode()
            json_data = json.loads(json_str)
            self.data_received.set()  # 设置数据接收标志位
            self.received_data = json_data
            print("Received data:", self.received_data)

            if 'action' in json_data:
                if json_data['action'] == 'disconnect':  # 检查是否接收到空字符串
                    print("Received disconnect string from myserver, closing connection.")
                    self.mouse_handle.update_state('quit')
                    break
            # 解析 JSON 字符串

        print("消息接受线程结束")

    def signal_handler(self):
        while self.running:
            if self.mouse_handle is not None:
                self.data_received.wait()
                if self.mouse_handle.state["quit"]:
                    self.mouse_handle.mouse_quit_signal = True
                    self.close()
                    print('关闭函数2号')
                    break
                if self.data_received.is_set() and self.received_data is not None:
                    if self.mouse_handle.state['quit']:
                        pass
                    elif self.mouse_handle.state['log_in']:
                        if 'id' in self.received_data and self.id is None:
                            self.id = self.received_data['id']
                            print("获取己方id:", self.id)
                        if self.received_data.get("action_back"):
                            if self.received_data.get("action_back") == "True":
                                print("登录成功")
                                self.Success_Log = True
                                if self.received_data.get("username") and self.received_data.get(
                                        "password") and self.received_data.get(
                                        "nickname") and self.received_data.get("gender") and self.received_data.get(
                                    "money") is not None:
                                    self.user_info.update(self.received_data)
                                    print(f"成功获取数据库信息：{self.user_info}")
                            elif self.received_data.get("action_back") == "False":
                                print("登录失败，请重新登录")
                                self.Success_Log = False
                                self.mouse_handle.login_fail_wrong = True
                            elif self.received_data.get("action_back") == "Locked":
                                print("此账号已经被登录")
                                self.Success_Log = False
                                self.mouse_handle.login_fail_lock = True

                        if self.Success_Log and self.id is not None:
                            self.mouse_handle.draw_pic.get_id(str(self.id))
                            self.mouse_handle.update_state('preparing')
                            self.mouse_handle.first_to_prepare = True
                    elif self.mouse_handle.state['register']:
                        if 'folder_build' in self.received_data:
                            if  self.received_data.get("folder_build"):
                                if self.received_data.get("folder_build") == "True":
                                    self.mouse_handle.folder_set = True
                                    print("存档建立成功")
                                elif self.received_data.get("folder_build") == "False":
                                    self.mouse_handle.folder_exist = True
                                    print("存档已经存在")
                    elif self.mouse_handle.state['preparing']:
                        if 'game_process' in self.received_data:
                            if self.received_data.get("game_process") == "preparing":
                                self.mouse_handle.key_json = self.received_data
                                self.mouse_handle.draw_pic.new_json_signal = True
                                # self.mouse_handle.draw_pic.update_json(self.received_data)
                            if self.received_data.get("game_process") == "starting":
                                self.mouse_handle.key_json = self.received_data
                                self.mouse_handle.draw_pic.new_json_signal = True
                                self.mouse_handle.update_state('gaming')
                                print("准备开始游戏")
                    elif self.mouse_handle.state['gaming']:
                        if 'game_process' in self.received_data:
                            if self.received_data.get("game_process") == "starting":
                                self.mouse_handle.key_json = self.received_data
                                self.mouse_handle.draw_pic.new_json_signal = True
                                # self.mouse_handle.draw_pic.update_json(self.received_data)
                                print("已经更新卡牌")
                            elif self.received_data.get("game_process") == "requesting":
                                if self.received_data["whose_turn"] == self.mouse_handle.draw_pic.id:
                                    if not self.rt.is_running:
                                        self.rt = RepeatedTimer(1, self.update_left_time)
                                        self.mouse_handle.draw_pic.time_left = str(self.time_to_choose_copy)
                                        self.rt.start()
                                        self.mouse_handle.draw_pic.update_time_left = True
                                self.mouse_handle.key_json = self.received_data
                                self.mouse_handle.draw_pic.new_json_signal = True
                                # self.mouse_handle.draw_pic.update_json(self.received_data)
                                print("已经更新轮次")
                            elif self.received_data.get("game_process") == "inform":
                                if self.rt.is_running:
                                    self.rt.stop()
                                    self.mouse_handle.draw_pic.update_time_left = False
                                    self.time_to_choose = self.time_to_choose_copy
                                self.mouse_handle.key_json = self.received_data
                                self.mouse_handle.draw_pic.new_json_signal = True
                                # self.mouse_handle.draw_pic.update_json(self.received_data)
                                print("已经更新用户操作数据")
                            elif self.received_data.get("game_process") == "battle":
                                if self.rt.is_running:
                                    self.rt.stop()
                                    self.mouse_handle.draw_pic.update_time_left = False
                                    self.time_to_choose = self.time_to_choose_copy
                                self.mouse_handle.key_json = self.received_data
                                self.mouse_handle.draw_pic.new_json_signal = True
                                # self.mouse_handle.draw_pic.update_json(self.received_data)
                                print("已经更新用户对抗")
                            elif self.received_data.get("game_process") == "ending":
                                winner = self.received_data["final_winner"]
                                self.mouse_handle.key_json = self.received_data
                                self.mouse_handle.draw_pic.new_json_signal = True
                                # self.mouse_handle.draw_pic.update_json(self.received_data)
                                print("游戏结束，胜利者是:",winner)
                                time.sleep(0.1)
                            elif self.received_data.get("game_process") == "preparing":
                                # self.mouse_handle.update_state('preparing')
                                self.mouse_handle.buffer = self.received_data
                                self.mouse_handle.draw_pic.new_json['game_process'] = 'ending'
                                self.mouse_handle.press_return_button = True
                                self.mouse_handle.draw_pic.wait_for_return = True

                                # self.mouse_handle.draw_pic.update_json(self.received_data)
                                print("结束这一局，回到准备阶段")
                self.data_received.clear()

    def update_left_time(self):
        self.time_to_choose -= 1
        self.mouse_handle.draw_pic.time_left = str(self.time_to_choose)
        if self.time_to_choose == 0:
            self.rt.stop()

    def send_id_message(self,message):
        if self.id is None:
            print("此时没有id,已经发送断开连接消息")
            self.client_socket.send(json.dumps(message).encode())
        else:
            json_id = {
                "id": self.id
            }
            json_id.update(message)
            self.client_socket.send(json.dumps(json_id).encode())
    def send_disconnect_message(self):
        if self.client_socket:
            try:
                json_message = {
                    "action": 'exit'
                }
                self.send_id_message(json_message)
                print("已经发送请求断开连接数据包")
            except Exception as e:
                print(f"Error sending disconnect message: {e}")
    def close(self):
        self.mouse_handle.mouse_quit_event.wait()
        with self.mouse_handle.mouse_quit_lock:
            if not self.close_once:
                self.running = False
                self.send_disconnect_message()
                self.mouse_handle.running = False
                print("123456")
                time.sleep(0.3)
                self.client_socket.close()
                self.close_once = True
        self.mouse_handle.mouse_quit_signal = False
        self.mouse_handle.mouse_quit_event.clear()
        # if self.signal_handler:
        #     self.signal_handler.join(timeout=1)

    def run(self):
        try:
            self.connect()
            self.mouse_handle = MouseClickHandler(self.client_socket)
            self.mouse_handle.input_box['password']['text'] = 'lc'
            self.mouse_handle.input_box['username']['text'] = 'lc'
            self.mouse_handle.input_box['password']['cursor_position'] = 2
            self.mouse_handle.input_box['username']['cursor_position'] = 2
            self.mouse_handle.run(self.data_received)
            print('------')

        finally:
            if self.mouse_handle.running:
                self.close()
                print('------')
        #     if self.mouse_handle.running:
        #         self.mouse_handle.running = False
        #         self.close()
        #         print("关闭函数3号")
        #     self.receive_thread.join()
        #     self.signal_handler.join()
        #     print('------')

if __name__ == "__main__":
    host = '127.0.0.1'  # 标准回环地址
    port = 5000  # 服务器正在监听的端口
    client = Client(host, port)
    client.run()