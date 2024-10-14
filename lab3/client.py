import socket
import random

SERVER_IP = '127.0.0.1'
SERVER_PORT = 12345
BUFFER_SIZE = 1024
ACK_LOSS_RATE = 0.2  # 模拟 ACK 丢失率
SEQ_SIZE = 4

def loss_in_loss_ratio(loss_ratio):
    return random.random() < loss_ratio

def client_program():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_addr = (SERVER_IP, SERVER_PORT)

    sock.sendto(b'start', server_addr)  # 向服务器请求开始数据传输

    expected_seq_num = 0

    while True:
        try:
            data, _ = sock.recvfrom(BUFFER_SIZE)
            message = data.decode()

            seq_num, content = message.split(':', 1)
            seq_num = int(seq_num)

            if seq_num == expected_seq_num % (2 ** SEQ_SIZE):
                print(f"Received packet: {message}")
                expected_seq_num += 1
            else:
                print(f"Out of order packet: {message}, expected: {expected_seq_num}")

            # 模拟 ACK 丢失
            if not loss_in_loss_ratio(ACK_LOSS_RATE):
                ack_message = str(expected_seq_num - 1).encode()
                sock.sendto(ack_message, server_addr)
                print(f"Sent ACK: {expected_seq_num - 1}")
            else:
                print(f"ACK {expected_seq_num - 1} lost")

        except KeyboardInterrupt:
            sock.sendto(b'quit', server_addr)
            break

    sock.close()

if __name__ == "__main__":
    client_program()
