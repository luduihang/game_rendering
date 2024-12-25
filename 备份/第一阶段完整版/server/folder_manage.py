import json
import os

class UserArchive:
    def __init__(self, data_file):
        self.data_file = data_file
        if not os.path.exists(data_file):
            self.users_data = {}
            self.save_archive()
        else:
            self.load_archive()

    def load_archive(self):
        with open(self.data_file, 'r') as file:
            self.users_data = json.load(file)

    def save_archive(self):
        with open(self.data_file, 'w') as file:
            json.dump(self.users_data, file, indent=4)

    def load_user_archive(self, username, password):
        user_data = self.users_data.get(username)
        if user_data and user_data['password'] == password:
            return user_data
        return None

    def create_user_archive(self, username, password,nickname, gender=''):
        if username in self.users_data:
            raise FileExistsError(f"User archive for {username} already exists.")
        user_data = {
            "username": username,
            "password": password,
            "nickname": nickname,
            "money": 500,
            "gender": gender
        }
        self.users_data[username] = user_data
        self.save_archive()
        return user_data
#参数：username: 字符串，表示要更新档案的用户名。
#     **kwargs: 可变关键字参数，表示要更新到用户档案中的键值对。用法：archive_manager.update_user_archive('ldh', coins=1000, gender='male')
#     更新用户名对应的参数。
    def update_user_archive(self, username, **kwargs):
        if username not in self.users_data:
            raise FileNotFoundError(f"No user archive found for {username}.")
        self.users_data[username].update(kwargs)
        self.save_archive()
        return self.users_data[username]




# # Usage example:
# archive_manager = UserArchive('folder/user_folder.json')
#
# # Load user archive
# user_data = archive_manager.load_user_archive('ldh', 'ldh')
# if user_data:
#     print("User archive loaded:", user_data)
# else:
#     print("User not found or incorrect password.")
#
# # Create new user archive
# try:
#     new_user_data = archive_manager.create_user_archive('new_user', 'new_password','kipely', gender='female')
#     print("New user archive created:", new_user_data)
# except FileExistsError as e:
#     print(e)
#
# # Update user archive
# try:
#     updated_user_data = archive_manager.update_user_archive('ldh', gender='male')
#     print("User archive updated:", updated_user_data)
# except FileNotFoundError as e:
#     print(e)
