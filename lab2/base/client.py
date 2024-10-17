import socket

CLIENT_IP = '127.0.0.1'
CLIENT_PORT = 12346
BUFFER_SIZE = 1024

def udp_client():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.bind((CLIENT_IP, CLIENT_PORT))
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

if __name__ == "__main__":
    udp_client()
