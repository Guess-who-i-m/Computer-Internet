import socket
import time
import threading
import random

SERVER_IP = '127.0.0.1'
SERVER_PORT = 12345
BUFFER_SIZE = 1024

SEQ_SIZE = 4  # 序列号比特数 L = 4，修改时需要同时修改服务端和客户端的SEQ_SIZE
WINDOW_SIZE = 8  # 发送窗口大小 W，满足 W + 1 <= 2^L
TIMEOUT = 3  # 超时时间为 3 秒
PACKET_LOSS_RATE = 0.2  # 模拟包丢失率



# 计时器类，用于控制超时重传
class Timer:
    def __init__(self, timeout):
        self.timeout = timeout          # 超时时间
        self.timer_thread = None        # 超时处理线程

    def start(self, callback):
        # 如果之前有定时器在运行，它会调用 stop() 方法停止当前定时器，防止重复启动。
        if self.timer_thread is not None: 
            self.stop()
            
        # 使用 threading.Timer 创建一个定时器线程，当达到设定的 timeout 时间后，触发重传的函数
        self.timer_thread = threading.Timer(self.timeout, callback)
        self.timer_thread.start()

    def stop(self):
        #  如果有定时器在运行，那么停止它
        if self.timer_thread is not None:
            self.timer_thread.cancel()
            self.timer_thread = None


# 利用随机数模拟随机丢失
def loss_in_loss_ratio(loss_ratio):
    return random.random() < loss_ratio


# 发送滑动窗口中的数据
# sock是发送的套接字，addr是目标client地址
# data_list是全部数据的队列
# base是当前窗口的的基地址
# next_seq_num是还没有被发送的下一个数据的index
# 重新传输所有已发送但是没有收到ACK的数据包，也就是从基序号base到next_seq_num前
def send_window_data(sock, addr, data_list, base, next_seq_num):
    # base
    for i in range(base, next_seq_num):
        # 
        if i < len(data_list):
            data = f"{i % (2 ** SEQ_SIZE)}:{data_list[i]}"
            
            # 模拟丢失
            if not loss_in_loss_ratio(PACKET_LOSS_RATE):
                sock.sendto(data.encode(), addr)
                print(f"Sent packet: {data}")
            else:
                print(f"Packet loss, Seq: {i % (2 ** SEQ_SIZE)}")

# 服务端运行函数
def server_program():
    # 创建套接字，并且绑定在对应的IP和端口
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((SERVER_IP, SERVER_PORT))

    # 模拟要发送的数据
    data_list = [f"Data {i}" for i in range(50)]  # 模拟要传输的数据
    
    
    base = 0                # 滑动窗口的第一个序号，也就是序列号最小的已发送但没收到ACK的数据包
    next_seq_num = 0        # 下一个可用的序列号，也就是第一个还没发送的数据报
    client_addr = None      # 客户端地址，使用recv方法来获取

    timer = Timer(TIMEOUT)  # 实例化计时器的对象，设定超时时间为3s

    # 发生超时，重新传输所有已发送但是没有收到ACK的数据包，也就是从基序号base到next_seq_num前
    def timeout_callback():
        print("Timeout! Resending window...")
        send_window_data(sock, client_addr, data_list, base, next_seq_num)
        timer.start(timeout_callback)   # 重传结束后再次启动计时器

    print(f"Server is listening on {SERVER_IP}:{SERVER_PORT}")

    while True:
        message, client_addr = sock.recvfrom(BUFFER_SIZE)
        message = message.decode()
        # 首先接收客户端的开始信息
        if message == 'start':
            # 开始传输数据，设定计时器开始计时
            print("Start sending data...")
            # timer.start(timeout_callback)
            # 当基序号在列表范围内时，重复尝试发送
            while base < len(data_list):
                # 如果下一可用序列在滑动窗口范围内，且每超出待发送队列范围，那么直接发送
                if next_seq_num < base + WINDOW_SIZE and next_seq_num < len(data_list):
                    # 当滑动窗口还没有结束，且base = next_seq_num时，还要继续启动计时器
                    if base == next_seq_num:
                        timer.start(timeout_callback)
                    send_window_data(sock, client_addr, data_list, base, next_seq_num + 1)
                    # send_window_data(sock, client_addr, data_list, base, next_seq_num + 1)
                    next_seq_num += 1

                # 接收ack，并获取ack序列号
                ack_message, _ = sock.recvfrom(BUFFER_SIZE)
                ack_num = int(ack_message.decode())
                print(f"Received ACK: {ack_num}")
                
                # 如果接收到ack，那么更新base的数字（base之前全被接收）
                if ack_num >= base:
                    # 当乱序到达时，可以确保base回退到概要发送的第一个
                    base = ack_num + 1
                    
                    if base == next_seq_num:
                        timer.stop()            # 当base追赶上了next_seq_num，说明结束，停止计时器
                    else:
                        timer.start(timeout_callback)


        elif message == 'quit':
            print("Client requested to quit.")
            break

    sock.close()

if __name__ == "__main__":
    server_program()
