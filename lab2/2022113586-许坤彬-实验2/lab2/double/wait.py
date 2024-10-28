import socket
import time
import random

BUFFER_SIZE = 1024
TIMEOUT = 2  # 超时时间（秒）

# 模拟丢包函数
def simulate_packet_loss():
    return random.random() < 0.2  # 20%的概率丢包

def udp_server(sever_ip, sever_port, client_ip, client_port, data_packets):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((sever_ip, sever_port))
    print(f"服务器启动，等待客户端连接...")

    # 数据包的内容
    # data_packets = ["数据包1:小", "数据包2：狗", "数据包3：汪", "数据包4：汪", "数据包5：队"]
    # current_packet = 0  # 当前发送的包序号
    state = 0           # 初始序列号为0

    while len(data_packets) > 0 :
        # 发送数据包格式：状态-数据
        packet = f"{state}-{data_packets[0]}".encode('utf-8')
        
        # 模拟丢包
        if simulate_packet_loss():
            print(f"模拟丢失：{data_packets[0]}")
            continue

        server_socket.sendto(packet, (client_ip, client_port))
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
            
            
def udp_client(client_ip, client_port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.bind((client_ip, client_port))
    print("客户端启动，等待数据接收...")

    expected_packet = 0

    try:
        while True:
            data, server_address = client_socket.recvfrom(BUFFER_SIZE)
            data = data.decode('utf-8')
            sequence_number, packet_content = data.split('-')

            if int(sequence_number) == expected_packet:
                print(f"收到正确的包：{packet_content}")
                ack = f"ACK{expected_packet}".encode('utf-8')
                client_socket.sendto(ack, server_address)
                if expected_packet == 1:
                    expected_packet = 0
                elif expected_packet == 0:
                    expected_packet = 1
            else:
                print(f"接收到错误包，期望包号：{expected_packet}")
    
    except KeyboardInterrupt:
        print("\n客户端已被中断，正在关闭...")
    finally:
        client_socket.close()
        print("客户端已关闭。")