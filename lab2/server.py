import socket
import time
import random

SERVER_IP = '127.0.0.1'
SERVER_PORT = 12345

CLIENT_IP = "127.0.0.1"
CLIENT_PORT = 12346

BUFFER_SIZE = 1024
TIMEOUT = 2  # 超时时间（秒）

# 模拟丢包函数
def simulate_packet_loss():
    return random.random() < 0.2  # 20%的概率丢包

def udp_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((SERVER_IP, SERVER_PORT))
    print(f"服务器启动，等待客户端连接...")

    # 数据包的内容
    data_packets = ["数据包1:小", "数据包2：狗", "数据包3：汪", "数据包4：汪", "数据包5：队"]
    # current_packet = 0  # 当前发送的包序号
    state = 0           # 初始序列号为0

    while len(data_packets) > 0 :
        # 发送数据包格式：状态-
        packet = f"{state}-{data_packets[0]}".encode('utf-8')
        
        # 模拟丢包
        if simulate_packet_loss():
            print(f"模拟丢失：{data_packets[0]}")
            continue

        server_socket.sendto(packet, (CLIENT_IP, CLIENT_PORT))
        print(f"发送数据包：{data_packets[0]}")

        # 设置超时接收
        server_socket.settimeout(TIMEOUT)
        try:
            ack, client_address = server_socket.recvfrom(BUFFER_SIZE)
            ack = ack.decode('utf-8')
            
            if ack == f"ACK{state}":
                print(f"收到 ACK：{ack}")
                data_packets.pop(0) # 弹出待发送队列的列首
                if state == 0 :
                    state = 1       # 收到ACK反转状态
                elif state == 1:
                    state = 0
            else:
                print(f"收到错误的 ACK：{ack}，重发当前数据包。")
        
        except socket.timeout:
            print(f"超时未收到 ACK{state}，重发数据包。")

if __name__ == "__main__":
    udp_server()
