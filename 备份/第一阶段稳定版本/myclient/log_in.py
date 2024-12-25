import threading
import json
import time
import tkinter as tk

class Client_Prepare_Old:
    def __init__(self):
        self.is_prepare = False
        self.state_change = False
        self.json_message = None

    def show_main_manu(self):
        while True:
            print("\n--- Main Menu ---")
            print("1. change mode")
            print("2. Exit Game")
            choice = input("Choose an option: ")
            if choice:  # 检测是否有按键
                if choice == '1':  # Enter 键
                    self.state_change = True
                    self.is_prepare = not self.is_prepare
                    self.json_message = self.prepare_json()
                    print(f"State changed to {'Prepared' if self.is_prepare else 'Not Prepared'}")
                    return self.json_message

                elif choice == '2':  # ESC 键
                    self.json_message = self.exit_game()
                    print("Exiting game...")
                    return self.json_message
                else:
                    print("Invalid option. Please try again.")
    def prepare_json(self):
        prepare_data = {
            'action': 'prepare',
            'is_changed': self.state_change,
            'state': self.is_prepare
        }
        return prepare_data

    def exit_game(self):
        exit_data = {
            'action': 'exit'
        }
        return exit_data
class Client_Bet_Old:
    def __init__(self,id,user_ids_list,client_socket):
        self.bet_choice = -1
        self.json_message = None
        self.running = True
        self.rest_option = 0
        self.option = ["2", "5", "10", "20", "50", "100", "弃牌", "看牌"]
        self.user_ids_list = user_ids_list #["1","3","4"]
        self.id = id
        self.client_socket = client_socket

        self.my_turn_event = threading.Event()
        self.choice_made_event = threading.Event()
        self.choice_made = False  # 新增标志位，用于指示是否已经做出选择
        self.time_out = False
        self.choice = 0
        self.json_message = None

    def set_turn(self,choice):
        self.timer = threading.Timer(5.0, self.timeout_operation)
        self.choice = choice
        self.timer.start()
        self.my_turn_event.set()
        self.choice_made_event.clear()
        self.choice_made = False

    def timeout_operation(self):
        if not self.choice_made:
            print("时间到，自动选择默认选项：弃牌")
            self.choice = len(self.option) - 2  # 更新为正确的选项索引
            self.handle_choice(str(self.choice))  # 假设"弃牌"是倒数第二个选项
            self.time_out = True
            self.choice_made_event.set()
            self.my_turn_event.clear()

    def update_option(self, rest_option):
        # 确保rest_option在有效范围内
        if 0 <= rest_option < len(self.option) - 2:  # -2是因为最后两个选项是"弃牌"和"看牌"
            self.rest_option = rest_option
        else:
            print("Invalid rest_option value.")
        return

    def show_main_menu(self):
        self.input_thread = threading.Thread(target=self._input_thread)
        self.input_thread.start()

    def _input_thread(self):
        while self.running:
            if self.my_turn_event.is_set():
                print("\n--- Main Menu ---")
                # 从rest_option开始打印选项，直到"弃牌"和"看牌"
                for i in range(self.rest_option, len(self.option) - 2):
                    print(f"{i + 1}. 押注{self.option[i]}刀")
                print(f"{len(self.option) - 1}. 弃牌")
                print(f"{len(self.option)}. 看牌")
                self.choice_thread = threading.Thread(target=self._choice_thread)
                self.choice_thread.start()
                self.choice_made_event.wait()
                if self.choice_made_event.is_set():
                    if not self.time_out:
                        self.choice_thread.join()
                        self.choice_made = True
                        self.handle_choice(self.choice)
                    else:
                        pass
                self.my_turn_event.clear()

    def _choice_thread(self):
        self.choice = input("请选择一个选项 ")
        self.choice_made_event.set()


    def handle_choice(self, choice):
        if not self.running:
            return
        try:
            choice_index = int(choice)
            if choice_index:
                if 0 <= choice_index < len(self.option) - 2:  # -2是因为最后两个选项是"弃牌"和"看牌"
                    print(f"选择了: {self.option[choice_index]}刀")
                    self.update_option(choice_index)  # 更新rest_option以反映新的开始位置
                elif choice_index == len(self.option) - 2:
                    print("选择了: 弃牌")
                elif choice_index == len(self.option) - 1:
                    for i in range(len(self.user_ids_list)):
                        print(f"玩家{i}")
                    print("请选择玩家")
                    self.timer.cancel()
                    self.id_choice = input("选择一个看牌的对象id: ")
                    print(f"你选择了玩家{self.id_choice},他的id是{self.user_ids_list[int(self.id_choice)]}")
                else:
                    print("Invalid option. Please try again.")

            if choice_index != len(self.option) - 1:
                self.json_message = {
                    "option": self.choice,
                    "target": -1
                }
            if choice_index == len(self.option) - 1:
                self.json_message = {
                    "option": self.choice,
                    "target": self.user_ids_list[int(self.id_choice)]
                }
            self.client_socket.send(json.dumps(self.json_message).encode())

            self.choice_thread.join()
            self.time_out = False
            self.timer.cancel()

        except ValueError:
            print("Invalid input. Please enter a number.")

    def close(self):
        self.running = False
        if hasattr(self, 'input_thread') and self.input_thread.is_alive():
            self.input_thread.join()
        print("Client Prepare closed.")

class LogIn:
    def __init__(self):
        self.username = None
        self.password = None
        self.nickname = None
        self.gender = None
        self.money = None
        self.json_message = None

    def show_main_menu(self):
        while True:
            print("\n--- Main Menu ---")
            print("1. Login")
            print("2. Register")
            print("3. Exit Game")
            choice = input("Choose an option: ")

            if choice == '1':
                self.json_message = self.login_menu()
                return self.json_message
            elif choice == '2':
                self.json_message = self.register_menu()
                return self.json_message
            elif choice == '3':
                self.json_message = self.exit_game()
                return self.json_message
            else:
                print("Invalid option. Please try again.")

    def login_menu(self):
        print("\n--- Login Menu ---")
        self.username = input("Enter username: ")
        self.password = input("Enter password: ")

        # 这里可以添加验证逻辑，例如检查字段是否为空

        login_data = {
            'action': 'login',
            'username': self.username,
            'password': self.password
        }
        return login_data

    def register_menu(self):
        print("\n--- Register Menu ---")
        self.username = input("Enter username: ")
        self.password = input("Enter password: ")
        self.nickname = input("Enter nickname: ")
        self.gender = input("Enter gender (male/female): ")

        # 这里可以添加验证逻辑，例如检查字段是否为空

        register_data = {
            'action': 'register',
            'username': self.username,
            'password': self.password,
            'nickname': self.nickname,
            'gender': self.gender
        }
        return register_data

    def exit_game(self):
        print("Exiting game...")
        exit_data = {
            'action': 'exit'
        }
        return exit_data

class Client_Prepare:
    def __init__(self,client_socket):
        self.is_prepare = False
        self.state_change = False
        self.json_message = None
        self.choice_callback = None
        self.json_changed = False
        self.client_socket = client_socket

        self.running = True  # 新增一个运行标志

    def show_main_menu(self, callback):
        self.choice_callback = callback
        threading.Thread(target=self._input_thread).start()

    def _input_thread(self):
        while self.running:  # 检查运行标志
            print("\n--- Main Menu ---")
            print("1. change mode")
            print("2. Exit Game")
            choice = input("Choose an option: ")
            if choice:
                self.choice_callback(choice)

    def handle_choice(self, choice):
        if not self.running:  # 如果不在运行状态，直接返回
            return

        if choice == '1':
            self.state_change = True
            self.is_prepare = not self.is_prepare
            self.json_message = self.prepare_json()
            self.json_changed = True
            print(f"State changed to {'Prepared' if self.is_prepare else 'Not Prepared'}")
            self.send_data_to_server()
            # Here you can return or process the json_message as needed
        elif choice == '2':
            self.json_message = self.exit_game()
            self.json_changed = True
            print("Exiting game...")
            self.send_data_to_server()
            self.close()
            # Here you can return or process the json_message as needed
        else:
            print("Invalid option. Please try again.")

    def send_data_to_server(self):
        message = self.json_message
        if self.json_changed:
            self.client_socket.send(json.dumps(message).encode())
        self.json_changed = False

    def prepare_json(self):
        prepare_data = {
            'action': 'prepare',
            'is_changed': self.state_change,
            'state': self.is_prepare
        }
        return prepare_data

    def exit_game(self):
        exit_data = {
            'action': 'exit'
        }
        return exit_data

    def close(self):
        self.running = False  # 设置运行标志为False
        if hasattr(self, 'input_thread') and self.input_thread.is_alive():
            self.input_thread.join()  # 等待输入线程结束
        # 如果有其他线程，也需要在这里加入join来等待它们结束
        print("Client Prepare closed.")

class Client_Bet:
    def __init__(self, id ,client_socket):
        self.bet_choice = -1
        self.json_message = None
        self.running = True
        self.rest_option = 0
        self.option = ["2", "5", "10", "20", "50", "100", "弃牌", "看牌"]
        self.user_ids_list = []
        self.id = id
        self.client_socket = client_socket

        self.my_turn_event = threading.Event()
        self.choice_made_event = threading.Event()
        self.choice_made = False
        self.time_out = False
        self.choice = 0
        self.json_message = None
        self.id_choice = -1

    def show_main_menu(self):
        print("\n--- Main Menu ---")
        # 从rest_option开始打印选项，直到"弃牌"和"看牌"
        for i in range(self.rest_option, len(self.option) - 2):
            print(f"{i}. 押注{self.option[i]}刀")
        print(f"{len(self.option) - 2}. 弃牌")
        print(f"{len(self.option) - 1}. 看牌")

        self.root = tk.Tk()
        self.root.title("Main Menu")

        def on_submit():
            choice = self.entry.get()
            try:
                choice_int = int(choice)
                if self.rest_option <= choice_int <= 7:
                    self.choice = choice_int
                    self.root.destroy()
                else:
                    print("Invalid choice. Please enter a number between 0 and 7.")
            except ValueError:
                print("Invalid input. Please enter a number.")

        self.entry = tk.Entry(self.root)
        self.entry.pack()

        submit_button = tk.Button(self.root, text="Submit", command=on_submit)
        submit_button.pack()

        self.root.mainloop()

    def set_turn(self, rest_option, user_ids_list):
        self.user_ids_list = user_ids_list
        self.timer = threading.Timer(10.0, self.timeout_operation)
        self.rest_option = rest_option
        self.timer.start()
        self.my_turn_event.set()
        self.choice_made_event.clear()
        self.choice_made = False

    def timeout_operation(self):
        if not self.choice_made:
            print("Time's up, automatically choosing the default option: 弃牌")
            self.choice = len(self.option) - 2
            self.handle_choice(self.choice)
            self.choice_made_event.set()
            self.my_turn_event.clear()
            self.entry.pack()

    def handle_choice(self, choice):
        if not self.running:
            return
        try:
            choice_index = int(choice)
            if choice_index:
                if 0 <= choice_index < len(self.option) - 2:  # -2是因为最后两个选项是"弃牌"和"看牌"
                    print(f"选择了: {self.option[choice_index]}刀")
                elif choice_index == len(self.option) - 2:
                    print("选择了: 弃牌")
                elif choice_index == len(self.option) - 1:
                    self.timer.cancel()
                    i = 0
                    free_list = []
                    for idx in self.user_ids_list:
                        if idx != -1 and idx != self.id:
                            print(f"玩家{i}")
                            free_list.append(i)
                        i += 1

                    print("请选择玩家")

                    # 在选择完玩家后执行逻辑
                    self.root = tk.Tk()
                    self.root.title("Select Player")

                    def on_submit_player():
                        try:
                            choice_index = int(self.entry.get())
                            if choice_index in free_list:
                                print(f"你选择了玩家{choice_index}")
                                self.id_choice = choice_index  # 存储选择的索引而不是玩家ID
                                self.root.destroy()
                            else:
                                print("Invalid player choice. Please enter a valid player index.")
                        except ValueError:
                            print("Invalid input. Please enter a number.")

                    self.entry = tk.Entry(self.root)
                    self.entry.pack()

                    submit_button = tk.Button(self.root, text="Submit", command=on_submit_player)
                    submit_button.pack()

                    self.root.mainloop()
                else:
                    print("当前没有可选择的玩家。")
            if choice_index != len(self.option) - 1:
                self.json_message = {
                    "option": self.choice,
                    "target": -1
                }
            if choice_index == len(self.option) - 1:
                self.json_message = {
                    "option": self.choice,
                    "target": self.user_ids_list[self.id_choice]
                }

            print(self.json_message)
            self.client_socket.send(json.dumps(self.json_message).encode())
            self.time_out = False
            self.timer.cancel()

        except ValueError:
            print("Invalid input. Please enter a number.")


    def Get_Send_Choice(self):
        self.show_main_menu()
        self.handle_choice(self.choice)


# client_bet = Client_Bet(1)
# client_bet.set_turn(0,[0,1,2])
# client_bet.Get_Send_Choice()


# 使用 LogIn 类
# def main():
#     prepare_manager = Client_Prepare()
#     while True:
#         json_message = prepare_manager.show_main_manu()
#         if prepare_manager.state_change == True:
#             print(f"ready to send message {json_message}")
#             prepare_manager.state_change = False
#         if prepare_manager.json_message["action"] == "exit":
#             print(f"ready to send exit signal {json_message}")
#             break
#         # 这里可以添加发送 JSON 到服务器的逻辑
#
#
# if __name__ == "__main__":
#     main()
