import socket
import threading
import select
from urllib.parse import urlparse  # 用于解析URL

# 设置代理服务器监听的端口
PROXY_PORT = 10240
BUFFER_SIZE = 4096


# 处理客户端请求的线程处理函数
def handle_client(client_socket):
    # 接收客户端请求
    # recv(bufsize, [flag])：接受TCP套接字的数据，数据会以字符串的形式返回
    # bufsize：是一个整数，表示要接收的最大字节数，接收实际数据量小于等于这个值
    # flag(可选)：一般忽略
    request = client_socket.recv(4096).decode()     # decode用于解码
    
    if not request:
        print("收到空请求，关闭连接。")
        client_socket.close()
        return
    
    # 提取请求中的方法和目标主机
    first_line = request.split('\n')[0]     # 提取请求中的第一行
    # method, url, _ = first_line.split()     # 提取请求中的方法和目标主机
    parts = first_line.split()

    if len(parts) < 3:
        print(f"格式错误的请求行: '{first_line}'")
        client_socket.close()
        return
    
    method, url, _ = parts  # 解包请求中的方法、URL和协议版本

    # connect请求的格式为 arnc2024.cn:2024
    if method == "CONNECT":
        # 提取目标主机和端口
        target_host = url.split(':')[0]
        target_port = int(url.split(':')[1])

        # 尝试连接目标服务器
        try:
            # 创建用于向目标IP发送请求的socket：使用IPv4和TCP相关参数
            remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # connect()：客户端程序用来连接服务端
            remote_socket.connect((target_host, target_port))

            # 向客户端发送 200 Connection Established 响应
            client_socket.send(b"HTTP/1.1 200 Connection Established\r\n\r\n")

            # 确立HTTP连接之后开始转发数据
            forward_data(client_socket, remote_socket)
        except Exception as e:
            print(f"请求转发失败：{e}")
            client_socket.close()
            
    # connect请求格式是http://www.arnc204.cn/
    elif method == "GET" or method == "POST" :
        
        # # 提取目标主机和端口
        # target_host = url.split(':')[0]
        # target_port = int(url.split(':')[1])
        
        # 由于格式和connect不一样，所以需要使用 urlparse 来解析 URL，提取目标主机和端口
        parsed_url = urlparse(url)
        target_host = parsed_url.hostname
        target_port = parsed_url.port if parsed_url.port else 80  # 如果URL中没有端口，默认使用80端口，一般情况下后端服务器的服务进程默认开放在80
        
        # 尝试连接目标服务器
        try:
            # 创建用于向目标IP发送请求的socket：使用IPv4和TCP相关参数
            remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # connect()：客户端程序用来连接服务端
            remote_socket.connect((target_host, target_port))

            # # 向客户端发送 200 Connection Established 响应
            #client_socket.send(b"HTTP/1.1 200 Connection Established\r\n\r\n")

            # 在Get/Post请求中，直接将原本的请求转发就可以
            remote_socket.send(request.encode())

            # 确立HTTP连接之后开始转发数据
            forward_data(client_socket, remote_socket)
        except Exception as e:
            print(f"请求转发失败1：{e}")
            client_socket.close()
        
        pass


# 转发数据
def forward_data(client_socket, remote_socket):
    sockets = [client_socket, remote_socket]
    while True:
        read_sockets, _, error_sockets = select.select(sockets, [], sockets)
        
        if error_sockets:
            break

        for sock in read_sockets:
            data = sock.recv(4096)
            if not data:
                break
            if sock == client_socket:
                remote_socket.send(data)
            else:
                client_socket.send(data)

    # 关闭套接字
    client_socket.close()
    remote_socket.close()
    


# 代理服务器函数，连接目标服务器并转发响应
def proxy_server(webserver, port, client_socket, client_request):
    # 创建连接到目标服务器的 socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.connect((webserver.decode(), port))

    # 将客户端的请求发送到目标服务器
    server_socket.send(client_request)

    # 接收目标服务器的响应并转发给客户端
    while True:
        response = server_socket.recv(BUFFER_SIZE)
        if len(response) > 0:
            client_socket.send(response)
        else:
            break

    # 关闭目标服务器的连接
    server_socket.close()

# 启动代理服务器，作为服务端不断监听本地的请求
def start_proxy():
    
    # 创建监听套接字
    # socket(family, type,[protocol])
    # family参数：
    #   AF_UNIX：使用单一的Unix系统进程间通信
    #   AF_INET；Ipv4地址族，服务器之间网络通信
    #   AF_INET6：IPv6 
    # type参数：
    #   SOCK_STREAM：流式socket，使用TCP时选择此参数
    #   SOCK_DGRAM：数据报式socket，使用UDP的时候选择此参数
    #   SOCK_RAW：原始套接字，允许底层协议如IP、ICMP进行直接访问
    # protocol：    可选项，指明接受的协议类型，通常为0或者不填
    #   IPPROTO_RAW：相当于protocol=255，此时socket只能用来发送IP包，而不能接收任何的数据。发送的数据需要自己填充IP包头，并且自己计算校验和
    #   IPPROTO_IP：相当于protocol=0，此时用于接收任何的IP数据包。其中的校验和和协议分析由程序自己完成。
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # 服务端函数
    
    # bind()：将创建的套接字和指定的IP地址和端口进行绑定，使用(IP, 端口)的元组来指定
    proxy_socket.bind(('0.0.0.0', PROXY_PORT))
    
    # listen()：在使用TCP的服务端开启监听模式
    proxy_socket.listen(5)

    print(f"[*] 代理服务器正在运行，监听端口 {PROXY_PORT}")


    # 不断接受客户端请求并创建新线程处理
    while True:
        # 调用accept函数接收客户端请求
        # 返回的两个参数为(conn, address)
        #   conn为新的套接字对象，用来接受收和发送数据
        #   address是连接的客户端的地址
        client_socket, addr = proxy_socket.accept()
        print(f"[*] 接受到来自 {addr} 的连接")

        # 为每个客户端请求创建一个新线程
        # threading.Thread声明了一个线程对象
        # threading.Thread(group=None, target=None, name=None, args=(), kwargs={}, *, daemon=None)
        #   group：应该设为None，即不用设置，使用默认值就好，因为这个参数是为了以后实现ThreadGroup类而保留的。
        #   target：在run方法中调用的可调用对象，即需要开启线程的可调用对象，比如函数或方法。
        #   name：线程名称，默认为“Thread-N”形式的名称，N为较小的十进制数。
        #   args：在参数target中传入的可调用对象的参数元组，默认为空元组()。
        #   kwargs：在参数target中传入的可调用对象的关键字参数字典，默认为空字典{}。
        #   daemon：默认为None，即继承当前调用者线程（即开启线程的线程，一般就是主线程）的守护模式属性，如果不为None，则无论该线程是否为守护模式，都会被设置为“守护模式”。
        client_handler = threading.Thread(target=handle_client, args=(client_socket,))
        # 开启线程活动
        client_handler.start()


# 在main函数的情况下，开启代理
if __name__ == "__main__":
    start_proxy()
