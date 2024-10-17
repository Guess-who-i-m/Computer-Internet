import socket
import threading
import random
import time

BUFFER_SIZE = 1024

SEQ_SIZE = 4  # 序列号位数
WINDOW_SIZE = 8  # 窗口大小，W < 2^SEQ_SIZE
TIMEOUT = 3  # 超时时间，单位秒
PACKET_LOSS_RATE = 0.1  # 模拟数据包丢失率
ACK_LOSS_RATE = 0.1  # 模拟ACK丢失率

########## 服务器端部分 ##########

# 计时器类，用于每个数据包独立的超时处理
class Timer:
    def __init__(self, timeout, callback):
        self.timeout = timeout  # 超时时间
        self.callback = callback  # 超时回调函数
        self.timer_thread = None  # 定时器线程
        self.lock = threading.Lock()
        self.active = False

    def start(self):
        with self.lock:
            self.timer_thread = threading.Timer(self.timeout, self.callback)
            self.active = True
            self.timer_thread.start()

    def stop(self):
        with self.lock:
            if self.active:
                self.timer_thread.cancel()
                self.active = False

# 模拟数据包丢失
def loss_in_loss_ratio(loss_ratio):
    return random.random() < loss_ratio

# 发送单个数据包
def send_packet(sock, addr, seq_num, data):
    packet = f"{seq_num}:{data}"
    if not loss_in_loss_ratio(PACKET_LOSS_RATE):
        sock.sendto(packet.encode(), addr)
        print(f"服务器：发送数据包：{packet}")
    else:
        print(f"服务器：数据包丢失，序列号：{seq_num}")

# 服务器程序，使用选择性重传协议
def server_program(server_ip, server_port, client_ip, client_port, data_list):
    # 创建socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((server_ip, server_port))

    base = 0  # 窗口起始序号
    next_seq_num = 0  # 下一个发送的序列号
    window = {}  # 存储已发送但未确认的数据包 {序号: 数据}
    timers = {}  # 存储每个数据包的定时器 {序号: Timer对象}

    client_addr = (client_ip, client_port)

    print(f"服务器正在监听 {server_ip}:{server_port}")

    # 超时回调函数，重传特定序列号的数据包
    def timeout_callback(seq):
        print(f"服务器：超时，重传数据包，序列号：{seq%(2**SEQ_SIZE)}")
        send_packet(sock, client_addr, seq%(2**SEQ_SIZE), data_list[seq])
        # 重新启动该数据包的定时器
        timers[seq].start()

    # 等待客户端发送“start”信号
    while True:
        message, addr = sock.recvfrom(BUFFER_SIZE)
        message = message.decode()
        if message == 'start':
            print("服务器：开始发送数据...")
            break

    # 发送数据包
    while base < len(data_list):
        # 发送窗口内的数据包
        while next_seq_num < base + WINDOW_SIZE and next_seq_num < len(data_list):
            seq_num = next_seq_num % (2 ** SEQ_SIZE)
            send_packet(sock, client_addr, seq_num, data_list[next_seq_num])
            # 启动该数据包的定时器
            timer = Timer(TIMEOUT, lambda s=next_seq_num: timeout_callback(s))
            timer.start()
            timers[next_seq_num] = timer
            window[next_seq_num] = seq_num
            next_seq_num += 1

        try:
            sock.settimeout(TIMEOUT)
            ack_message, _ = sock.recvfrom(BUFFER_SIZE)
            ack_num = int(ack_message.decode())
            print(f"服务器：收到ACK：{ack_num}")

            # 查找对应的发送序号
            ack_received = False
            for key, seq in list(window.items()):
                if seq == ack_num:
                    print(f"服务器：ACK确认，序列号：{seq}")
                    
                    timers[key].stop()  # 停止该数据包的定时器
                    del timers[key]  # 移除定时器
                    del window[key]  # 从窗口移除该数据包
                    
                    if key == base:
                        # 如果确认的是窗口的最小序号，移动窗口基准
                        while base not in window and base < next_seq_num:
                            base += 1
                    ack_received = True
                    break
            if not ack_received:
                print("服务器：收到不在缓存范围内的ACK")
                # # 当ACK发生过丢失，即接收方返回expected_seq - 1
                # if base < ack_num:
                #     base = ack_num + 1
                #     for key, seq in list(window.items()):
                #         if seq < base:
                #             timers[key].stop()  # 停止该数据包的定时器
                #             del timers[key]  # 移除定时器
                #             del window[key]  # 从窗口移除该数据包
                        
                
                print(f"服务器：收到重复或无效的ACK：{ack_num}")
                
        except socket.timeout:
            # 可能有数据包超时，已由各自的定时器处理
            continue

    # 所有数据包发送并确认后，发送“quit”信号
    sock.sendto(b'quit', client_addr)
    print("服务器：所有数据包已发送并确认，退出。")

    sock.close()



########### 客户端部分 ###########

# 模拟ACK丢失
def loss_in_loss_ratio(loss_ratio):
    return random.random() < loss_ratio

# 客户端程序，使用选择性重传协议
def client_program(client_ip, client_port, server_ip, server_port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((client_ip, client_port))
    server_addr = (server_ip, server_port)

    expected_seq_num = 0  # 下一个期望的序列号
    received_packets = {}  # 缓存不按序到达的数据包 {序号: 数据}

    # 发送“start”信号给服务器
    sock.sendto(b'start', server_addr)
    print("客户端：发送‘start’信号给服务器。")

    while True:
        try:
            data, addr = sock.recvfrom(BUFFER_SIZE)
            message = data.decode()

            if message == 'quit':
                print("客户端：收到‘quit’信号，退出。")
                break

            # 解析收到的数据包
            try:
                seq_num_str, content = message.split(':', 1)
                seq_num = int(seq_num_str)
            except ValueError:
                print("客户端：收到格式错误的数据包，忽略。")
                continue

            abs_seq_num = seq_num

            # 检查数据包是否在接收窗口内
            window_start = expected_seq_num
            window_end = (expected_seq_num + WINDOW_SIZE) % (2**SEQ_SIZE)
            judge = 0
            
            if window_end > window_start:
                if window_start <= abs_seq_num < window_end:
                    judge = 1
                else:
                    judge = 0
            else:
                if (window_start<= abs_seq_num < 2**SEQ_SIZE) or (0 <= abs_seq_num < window_end ):
                    judge = 2
                else:
                    judge = 0

            if judge != 0:
                if abs_seq_num == expected_seq_num:
                    print(f"客户端：收到期望的数据包，序列号：{seq_num}，内容：{content}")
                    expected_seq_num = (expected_seq_num + 1) % (2 ** SEQ_SIZE)

                    # 检查是否有缓存的数据包可以处理
                    while expected_seq_num in received_packets:
                        buffered_content = received_packets.pop(expected_seq_num)
                        print(f"客户端：处理缓存的数据包，序列号：{expected_seq_num}，内容：{buffered_content}")
                        expected_seq_num = (expected_seq_num + 1) % (2 ** SEQ_SIZE)
                elif abs_seq_num != expected_seq_num:
                    if abs_seq_num not in received_packets:
                        print(f"客户端：收到乱序数据包，序列号：{seq_num}，内容：{content}")
                        received_packets[abs_seq_num] = content
                    else:
                        print(f"客户端：已缓存数据包，序列号：{seq_num}，无需重复缓存。")
                # 发送ACK
                if not loss_in_loss_ratio(ACK_LOSS_RATE):
                    ack_message = str(seq_num).encode()
                    sock.sendto(ack_message, server_addr)
                    print(f"客户端：发送ACK，序列号：{seq_num}")
                else:
                    print(f"客户端：ACK丢失，序列号：{seq_num}")
                judge = 0
            else:
                print(f"客户端：收到不在窗口内的数据包，序列号：{seq_num}，已丢弃。")
                # 可选：重发上一个确认的ACK
                
                last_ack = seq_num 
                if not loss_in_loss_ratio(ACK_LOSS_RATE):
                    ack_message = str(last_ack).encode()
                    sock.sendto(ack_message, server_addr)
                    print(f"客户端：重新发送ACK，序列号：{last_ack}")
                else:
                    print(f"客户端：重新发送ACK丢失，序列号：{last_ack}")
                judge = 0

        except KeyboardInterrupt:
            # 用户中断时发送“quit”信号
            sock.sendto(b'quit', server_addr)
            print("客户端：用户中断，发送‘quit’信号并退出。")
            break

    sock.close()