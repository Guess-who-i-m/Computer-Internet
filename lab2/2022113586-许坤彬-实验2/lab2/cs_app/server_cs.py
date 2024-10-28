import socket
import os
import random

SERVER_IP = '127.0.0.1'
SERVER_PORT = 12345
CLIENT_IP = '127.0.0.1'
CLIENT_PORT = 12346
BUFFER_SIZE = 1024
TIMEOUT = 2  # 超时时间（秒）
FILE_PATH = 'server_file.txt'  # 要发送的文件

# 模拟丢包函数
def simulate_packet_loss():
    return random.random() < 0.2  # 20%的概率丢包

def udp_server():
    # 创建socket套接字，并且绑定在本地端口上
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((SERVER_IP, SERVER_PORT))
    print(f"服务器启动，等待客户端连接...")

    try:
        # 首先打开需要传递的文件
        with open(FILE_PATH, 'rb') as file:
            # 获取文件大小
            file_size = os.path.getsize(FILE_PATH)
            # 计算文件需要多少数据包
            num_packets = (file_size // BUFFER_SIZE) + 1  
            state = 0  # 初始序列号为0
            
            # 根据文件读取结果确定什么时候结束循环
            for i in range(num_packets):
                # 读取文件的一块数据并且分别进行封装
                file_chunk = file.read(BUFFER_SIZE)
                packet = f"{state}-".encode('utf-8') + file_chunk

                # # 模拟丢包
                # if simulate_packet_loss():
                #     print(f"模拟丢失：数据包{state}")
                #     continue

                # 向客户端发送对应的数据包
                server_socket.sendto(packet, (CLIENT_IP, CLIENT_PORT))
                print(f"发送数据包{state}")

                # 设置超时接收
                server_socket.settimeout(TIMEOUT)
                try:
                    ack, client_address = server_socket.recvfrom(BUFFER_SIZE)
                    ack = ack.decode('utf-8')

                    if ack == f"ACK{state}":
                        print(f"收到 ACK：{ack}")
                        state = 1 - state  # 切换状态
                    else:
                        print(f"收到错误的 ACK：{ack}，重发当前数据包。")

                except socket.timeout:
                    print(f"超时未收到 ACK{state}，重发数据包。")


            # 文件传输完成后，单独发送结束标记
            end_packet = "EOF".encode('utf-8')
            server_socket.sendto(end_packet, (CLIENT_IP, CLIENT_PORT))
            print("文件传输结束标记已发送。")

    except FileNotFoundError:
        print("要发送的文件不存在。")
    finally:
        server_socket.close()

if __name__ == "__main__":
    udp_server()
