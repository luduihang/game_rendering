#!/bin/bash
import key_handle
import socket
import pygame
# 定义服务器和客户端的路径
SERVER_PATH="/home/kipleytaylor/Documents/MyCode/PythonProject/game_rendering/myserver"
CLIENT_PATH="/home/kipleytaylor/Documents/MyCode/PythonProject/game_rendering/myclient"

# 切换到服务器路径并运行服务器脚本
cd "$SERVER_PATH"
python server_simple.py &

# 获取服务器进程的PID
SERVER_PID=$!

# 切换到客户端路径并运行客户端脚本
cd "$CLIENT_PATH"
python client_draw.py
python client_draw_copy.py
python client_draw_copy2.py

# 等待客户端脚本运行完毕后，杀死服务器进程
wait
