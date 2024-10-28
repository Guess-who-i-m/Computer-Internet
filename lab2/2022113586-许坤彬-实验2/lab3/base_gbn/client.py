import socket
import random

SERVER_IP = '127.0.0.1'
SERVER_PORT = 12345
BUFFER_SIZE = 1024
ACK_LOSS_RATE = 0.2  # 模拟 ACK 丢失率
SEQ_SIZE = 4

# 利用随机数来模拟ACK丢失的情况
def loss_in_loss_ratio(loss_ratio):
    return random.random() < loss_ratio

# 客户端程序
def client_program():
    # 首先创建两个socket，并绑定在对应的IP和端口号上
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_addr = (SERVER_IP, SERVER_PORT)

    # 向服务端发送开始信号
    sock.sendto(b'start', server_addr)  # 向服务器请求开始数据传输

    # 期待的序列号
    expected_seq_num = 0

    while True:
        try:
            
            # 从绑定端口接收数据，并对数据进行解码从而获取信息
            data, _ = sock.recvfrom(BUFFER_SIZE)
            message = data.decode()

            # 依据':'分割序列号和数据信息
            seq_num, content = message.split(':', 1)
            seq_num = int(seq_num)

            # 依据序列号的位数，进行取余比对，如果比对一致，那么直接输出信息，接收到了这个包
            if seq_num == expected_seq_num % (2 ** SEQ_SIZE):
                print(f"Received packet: {message}")
                # 期待的包序列号+1
                expected_seq_num += 1
            else:
                print(f"Out of order packet: {message}, expected: {expected_seq_num}")

            # 模拟 ACK 丢失
            if not loss_in_loss_ratio(ACK_LOSS_RATE):
                # 发送确认的ACK信息，ACK序列号指的是1——ACK的包都已接收
                ack_message = str(expected_seq_num - 1).encode()
                sock.sendto(ack_message, server_addr)
                print(f"Sent ACK: {expected_seq_num - 1}")
            else:
                # 如果模拟ACK丢失，啥也不发送
                print(f"ACK {expected_seq_num - 1} lost")

        except KeyboardInterrupt:
            sock.sendto(b'quit', server_addr)
            break

    sock.close()

if __name__ == "__main__":
    client_program()
