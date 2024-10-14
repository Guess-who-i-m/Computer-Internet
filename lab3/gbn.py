import socket
import time
import threading
import random


BUFFER_SIZE = 1024

SEQ_SIZE = 4  # 序列号比特数 L = 4，修改时需要同时修改服务端和客户端的SEQ_SIZE
WINDOW_SIZE = 8  # 发送窗口大小 W，满足 W + 1 <= 2^L
TIMEOUT = 3  # 超时时间为 3 秒
PACKET_LOSS_RATE = 0.1  # 模拟包丢失率
ACK_LOSS_RATE = 0.1  # 模拟 ACK 丢失率



########## server端部分

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
                print(f"服务端：Sent packet: {data}")
            else:
                print(f"服务端：Packet loss, Seq: {i % (2 ** SEQ_SIZE)}")

# 服务端运行函数
def server_program(server_ip, server_port, client_ip, client_port, data_list):
    # 创建套接字，并且绑定在对应的IP和端口
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((server_ip, server_port))
    
    base = 0                # 滑动窗口的第一个序号，也就是序列号最小的已发送但没收到ACK的数据包
    next_seq_num = 0        # 下一个可用的序列号，也就是第一个还没发送的数据报
    # client_addr = None      # 客户端地址，使用recv方法来获取

    timer = Timer(TIMEOUT)  # 实例化计时器的对象，设定超时时间为3s

    # 发生超时，重新传输所有已发送但是没有收到ACK的数据包，也就是从基序号base到next_seq_num前
    def timeout_callback():
        print("服务端：Timeout! Resending window...")
        send_window_data(sock, (client_ip, client_port), data_list, base, next_seq_num)
        timer.start(timeout_callback)   # 重传结束后再次启动计时器

    print(f"Server is listening on {server_ip}:{server_port}")

    while True:
        # message, client_addr = sock.recvfrom(BUFFER_SIZE)
        # message = message.decode()
        message = 'start'
        # 首先接收客户端的开始信息
        if message == 'start':
            # 开始传输数据，设定计时器开始计时
            # print("服务端：Start sending data...")
            # timer.start(timeout_callback)
            # 当基序号在列表范围内时，重复尝试发送
            while base < len(data_list):
                # 如果下一可用序列在滑动窗口范围内，且每超出待发送队列范围，那么直接发送
                if next_seq_num < base + WINDOW_SIZE and next_seq_num < len(data_list):
                    # 当滑动窗口还没有结束，且base = next_seq_num时，还要继续启动计时器
                    if base == next_seq_num:
                        timer.start(timeout_callback)
                    send_window_data(sock, (client_ip, client_port), data_list, base, next_seq_num + 1)
                    # send_window_data(sock, client_addr, data_list, base, next_seq_num + 1)
                    next_seq_num += 1

                # 接收ack，并获取ack序列号
                ack_message, _ = sock.recvfrom(BUFFER_SIZE)
                ack_num = int(ack_message.decode())
                print(f"服务端：Received ACK: {ack_num}")
                
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


########### client端部分

# 利用随机数来模拟ACK丢失的情况
def loss_in_loss_ratio(loss_ratio):
    return random.random() < loss_ratio

# 客户端程序
def client_program( client_ip, client_port):
    # 首先创建两个socket，并绑定在对应的IP和端口号上
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((client_ip, client_port))
    # server_addr = (server_ip, server_port)

    # 向服务端发送开始信号
    # sock.sendto(b'start', server_addr)  # 向服务器请求开始数据传输

    # 期待的序列号
    expected_seq_num = 0

    while True:
        try:
            
            # 从绑定端口接收数据，并对数据进行解码从而获取信息
            data, server_addr = sock.recvfrom(BUFFER_SIZE)
            message = data.decode()

            # 依据':'分割序列号和数据信息
            seq_num, content = message.split(':', 1)
            seq_num = int(seq_num)

            # 依据序列号的位数，进行取余比对，如果比对一致，那么直接输出信息，接收到了这个包
            if seq_num == expected_seq_num % (2 ** SEQ_SIZE):
                print(f"客户端：Received packet: {message}")
                # 期待的包序列号+1
                expected_seq_num += 1
            else:
                print(f"客户端：Out of order packet: {message}, expected: {expected_seq_num}")

            # 模拟 ACK 丢失
            if not loss_in_loss_ratio(ACK_LOSS_RATE):
                # 发送确认的ACK信息，ACK序列号指的是1——ACK的包都已接收
                ack_message = str(expected_seq_num - 1).encode()
                sock.sendto(ack_message, server_addr)
                print(f"客户端：Sent ACK: {expected_seq_num - 1}")
            else:
                # 如果模拟ACK丢失，啥也不发送
                print(f"客户端：ACK {expected_seq_num - 1} lost")

        except KeyboardInterrupt:
            sock.sendto(b'quit', server_addr)
            break

    sock.close()


