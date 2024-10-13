import socket

SERVER_IP='127.0.0.1'
SERVER_PORT= 12345
CLIENT_IP = '127.0.0.1'
CLIENT_PORT = 12346
BUFFER_SIZE = 1024
TIMEOUT = 2

def udp_client():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.bind((CLIENT_IP, CLIENT_PORT))
    print("客户端启动，等待数据接收...")
    
    # 数据包的内容
    data_packets = ["数据包1:小", "数据包2：狗", "数据包3：汪", "数据包4：汪", "数据包5：队"]
    # data_packets = ["数据包1:小", "数据包2：狗", "数据包3：汪", "数据包4：汪"]

    expected_packet = 0
    send_state = 0
    
    try:
        while True:
            try:
                # 客户端接收部分
                data, server_address = client_socket.recvfrom(BUFFER_SIZE)
                data = data.decode('utf-8')
                
                if data.startswith("ACK"):
                    send_state = 1
                    ack = data
                
                    if ack == f"ACK{expected_packet}":
                        print(f"收到来自服务器的确认：{ack}")
                        
                        
                else:
                    
                    sequence_number, packet_content = data.split('-')
                    send_state = 0

                    if int(sequence_number) == expected_packet:
                        print(f"收到正确的包：{packet_content}")
                        
                        
                        
                    else:
                        print(f"接收到错误包，期望包号：{expected_packet}")
                        # continue
                        
                # 客户端发送部分
                if send_state == 1 or len(data_packets) == 0:
                    ack_send = f"ACK{expected_packet}".encode('utf-8')
                    client_socket.sendto(ack_send, server_address)
                    if expected_packet == 1:
                        expected_packet = 0
                    elif expected_packet == 0:
                        expected_packet = 1
                
                if send_state == 0 and len(data_packets) > 0:
                    packet = f"{expected_packet}-{data_packets[0]}".encode('utf-8')
                    client_socket.sendto(packet, (SERVER_IP, SERVER_PORT))
                    print(f"发送数据包：{data_packets[0]}")
                    data_packets.pop(0)
                    client_socket.settimeout(TIMEOUT)
            except socket.timeout:
                if len(data_packets) > 0:
                    print(f"超时")
                else:
                    print("等待状态")
    except KeyboardInterrupt:
        print("\n客户端已被中断，正在关闭...")
    finally:
        client_socket.close()
        print("客户端已关闭。")

if __name__ == "__main__":
    udp_client()