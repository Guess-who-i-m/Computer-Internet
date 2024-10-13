import socket

CLIENT_IP = '127.0.0.1'
CLIENT_PORT = 12346
BUFFER_SIZE = 1024
FILE_PATH = 'received_file.txt'  # 接收后保存的文件

def udp_client():
    # 创建客户端套接字
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.bind((CLIENT_IP, CLIENT_PORT))
    print("客户端启动，等待文件接收...")

    expected_packet = 0

    try:
        with open(FILE_PATH, 'wb') as file:
            while True:
                data, server_address = client_socket.recvfrom(BUFFER_SIZE + 10)  # 增加缓冲区以处理数据包头
                
                # 当内容为结束符号时
                if data.decode('utf-8') == "EOF":
                    print("文件接收完毕，收到结束标记。")
                    break  # 停止接收

                # 使用'-'分隔符将序列号和文件块分开
                sequence_number_str, file_chunk = data.decode('utf-8').split('-', 1)

                try:
                    sequence_number = int(sequence_number_str)  # 将序列号转换为整数
                except ValueError:
                    print(f"解析序列号失败，收到无效数据：{sequence_number_str}")
                    continue

                if sequence_number == expected_packet:
                    # 写入接收到的文件块
                    file.write(file_chunk.encode('utf-8'))  # 将文件块写入文件
                    print(f"收到数据包：{expected_packet}")

                    # 发送 ACK 确认
                    ack = f"ACK{expected_packet}".encode('utf-8')
                    client_socket.sendto(ack, server_address)
                    expected_packet = 1 - expected_packet  # 切换期望的数据包序号
                else:
                    print(f"接收到错误包，期望包号：{expected_packet}")
    
    except KeyboardInterrupt:
        print("\n客户端已被中断，正在关闭...")
    finally:
        client_socket.close()
        print("客户端已关闭。")

if __name__ == "__main__":
    udp_client()
