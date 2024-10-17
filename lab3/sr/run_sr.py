import sr as sr
import threading

SERVER_IP = '127.0.0.1'
SERVER_PORT = 12345

CLIENT_IP = '127.0.0.1'
CLIENT_PORT = 12346

# 模拟要传输的数据
data_list = [f"Data{i}" for i in range(50)]

Thread_Server = threading.Thread(target=sr.server_program, args=(SERVER_IP, SERVER_PORT, CLIENT_IP, CLIENT_PORT, data_list, ))
Thread_Client = threading.Thread(target=sr.client_program, args=(CLIENT_IP, CLIENT_PORT, SERVER_IP, SERVER_PORT, ))

Thread_Server.start()
Thread_Client.start()