import socket
import threading
import select
import time
import os
from urllib.parse import urlparse  # 用于解析URL


# 可以用来测试缓存的网站
# http://www.arnc2024.cn/hello.html
# http://example.com/

# 禁止访问的网站列表
invalid_website = ["http://jwes.hit.edu.cn/"]

# 钓鱼网站配置
fishing_src = "http://today.hit.edu.cn"
fishing_dest = "http://example.com/"
fishing_dest_host = "example.com"

# 限制访问的用户IP
restrict_host = ["127.0.0.1"]

# 是否开启钓鱼、禁止和限制访问功能
func_web_block = False
func_user_block = False
func_fish = True

# 设置代理服务器监听的端口
PROXY_PORT = 10240
BUFFER_SIZE = 4096

# 缓存字典，键值对格式(URL:缓存响应和响应时间)
CACHE_EXPIRY = 60      # 设置缓存的过期时间，单位为秒
CACHE_NUM = 50

cache_index = 0  # 当前应将缓存放在哪个位置  

# HTTP 重要头部数据 用来存储解析后的HTTP请求头信息
class HttpHeader:
    def __init__(self):
        self.method = ''  # GET、POST 或 CONNECT
        self.url = ''     # 请求的 URL
        self.host = ''    # 目标主机
        self.port = 80    # 目标端口

# 缓存的 HTTP 头部（不包含 Cookie） 用来比较是否命中缓存
class CacheHttpHead:
    def __init__(self):
        self.method = ''
        self.url = ''
        self.host = ''
        self.port = 80
        
# 代理服务器缓存结构 
class CacheEntry:
    def __init__(self):
        self.httpHead = CacheHttpHead()
        self.buffer = b''      # 存储返回内容
        self.date = ''         # 缓存内容的最后修改时间
   
cache = [CacheEntry() for _ in range(CACHE_NUM)]  # 缓存列表

        
def receive_full_response(remote_socket):
    response = b''
    while True:
        part = remote_socket.recv(BUFFER_SIZE)
        response += part
        if not part:
            break
    return response

def parse_http_response(response):
    # 解析 HTTP 响应，获取状态行、头部和正文
    header_end = response.find(b'\r\n\r\n')
    if header_end == -1:
        return None, None, None
    header_bytes = response[:header_end]
    body = response[header_end+4:]
    header_text = header_bytes.decode('utf-8', errors='ignore')
    lines = header_text.split('\r\n')
    status_line = lines[0]
    headers = {}
    for line in lines[1:]:
        if ': ' in line:
            key, value = line.split(': ', 1)
            headers[key.lower()] = value
    return status_line, headers, body


def http_equal(http1, http2):
    # 判断两个 HTTP 报文是否相同
    return (http1.method == http2.method and http1.host == http2.host
            and http1.url == http2.url and http1.port == http2.port)
    
def is_in_cache(cache, http_header):
    # 检查缓存中是否存在对应的条目
    for index, entry in enumerate(cache):
        # print(entry.httpHead.url)
        if http_equal(entry.httpHead, http_header):
            return index
    return -1


def modify_request_for_fishing(request, http_header):
    # 修改请求，进行钓鱼网站重定向 返回新的请求url
    lines = request.decode('utf-8').split('\r\n')
    # 修改请求行和 Host 头部
    new_lines = []
    for line in lines:
        if line.startswith(http_header.method):
            # 修改请求行
            parts = line.split(' ')
            if len(parts) >= 3:
                parts[1] = http_header.url  # 更新 URL
                new_line = ' '.join(parts)
                new_lines.append(new_line)
            else:
                new_lines.append(line)
        elif line.startswith('Host:'):
            # 修改 Host 头部
            new_lines.append(f"Host: {http_header.host}")
        else:
            new_lines.append(line)
    return '\r\n'.join(new_lines).encode('utf-8')


# 处理客户端请求的线程处理函数
def handle_client(client_socket, addr):
    
    global cache_index
    
    # 用户过滤
    if func_user_block and (addr[0] in restrict_host):
        print(addr[0] + '已经被禁止访问')
        client_socket.close()   # 关闭socket
        return
    
    
    
    
    # 接收客户端请求
    # recv(bufsize, [flag])：接受TCP套接字的数据，数据会以字符串的形式返回
    # bufsize：是一个整数，表示要接收的最大字节数，接收实际数据量小于等于这个值
    # flag(可选)：一般忽略
    request = client_socket.recv(BUFFER_SIZE)     # decode用于解码
    
    if not request.strip():  # 使用strip()去掉首尾空白字符
        print("收到空请求，关闭连接。")
        client_socket.close()
        return
    
    # 提取请求中的方法和目标主机
    first_line = request.decode().split('\n')[0]     # 提取请求中的第一行
    parts = first_line.split()
    
    if len(parts) < 3:
        print(parts)
        print(f"格式错误的请求行: '{first_line}'")
        client_socket.close()
        return
    
    header = HttpHeader()   # 实例化HTTP头对象
    
    header.method = parts[0]
    header.url    = parts[1]
    
    # 网站过滤
    if func_web_block and any(site in header.url for site in invalid_website):
        print("网站已经被屏蔽")
        client_socket.close()
        return
    
    # 钓鱼网站
    if func_fish and fishing_src in header.url:
        print(f"从源网站{fishing_src}转到目的网站{fishing_dest}")
        header.host = fishing_dest_host
        header.url = fishing_dest
        # 重新将这些信息整合回到请求中
        request = modify_request_for_fishing(request, header)
    
    
    # connect请求的格式为 arnc2024.cn:2024
    if header.method == "CONNECT":
        # 提取目标主机和端口
        header.host = header.url.split(':')[0]
        header.port = int(header.url.split(':')[1])

        # 尝试连接目标服务器
        try:
            # 创建用于向目标IP发送请求的socket：使用IPv4和TCP相关参数
            remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # connect()：客户端程序用来连接服务端
            remote_socket.connect((header.host, header.port))
    
            # 向客户端发送 200 Connection Established 响应
            client_socket.send(b"HTTP/1.1 200 Connection Established\r\n\r\n")

            # 确立HTTP连接之后开始转发数据
            forward_data(client_socket, remote_socket)
        except Exception as e:
            print(f"请求转发失败：{e}")
            client_socket.close()
            
    # get/post请求格式是http://www.arnc2024.cn/
    elif header.method == "GET" or header.method == "POST" :
        
        # 由于格式和connect不一样，所以需要使用 urlparse 来解析 URL，提取目标主机和端口
        parsed_url = urlparse(header.url)
        header.host = parsed_url.hostname
        header.port = parsed_url.port if parsed_url.port else 80  # 如果URL中没有端口，默认使用80端口，一般情况下后端服务器的服务进程默认开放在80
        
        cache_entry = None 
        
        # for index, entry in enumerate(cache):
        #     print(entry.httpHead.url)
        
        # 检查缓存
        index = is_in_cache(cache, header)
        
        # print(index)
        if index > -1:
            print(f"命中缓存{index}")
            # 检查缓存
            cache_entry = cache[index]  # 初始化 cache_entry
            # 缓存命中，添加 If-Modified-Since 头部
            print(cache_entry.date)
            request = add_if_modified_since(request, cache_entry.date)
            print("修改的request:" + request.decode('iso-8859-1', errors='ignore'))
            print("已修改request，增加了if-modified-since")
            # print(request)

        # if cache_entry is None:  # 如果缓存没有命中  
        
              
                    
        # 尝试连接目标服务器
        try:
            # 创建用于向目标IP发送请求的socket：使用IPv4和TCP相关参数
            remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # print("socket连接")
            
            # connect()：客户端程序用来连接服务端
            remote_socket.connect((header.host, header.port))
            # print("connect")

            # 在Get/Post请求中，直接将原本的请求转发就可以
            remote_socket.send(request)
            # print("转发请求")
            
            # 获取响应
            response = remote_socket.recv(BUFFER_SIZE)
            # response = receive_full_response(remote_socket)
            
            # content_length = get_content_length(response)
            
            #if content_length and content_length != len(response):
                
                # print(f"Warning: Content-Length ({content_length}) does not match actual response length ({len(response)})")
            
            
            
            # print("获得响应")
            # print(response.decode())
            
            status_line, headers, body = parse_http_response(response)
            
            if not status_line:
                # 无法解析响应，直接转发
                client_socket.sendall(response)
                return
            
            # 当index>-1，缓存命中
            if index > -1 : 
                if "304" in status_line:
                    # 没有在服务器被修改，所以可以直接返回
                    print(status_line)
                    client_socket.send(cache_entry.buffer)
                    print(f"缓存没有被修改，所以可以直接返回内容：{header.url}")
                else:
                    # 更新缓存
                    print("缓存被修改了")
                    print(status_line)
                    cache_entry.buffer = response
                    # 修改最新的last-modified
                    cache_entry.date = headers.get('last-modified', '')
                    client_socket.send(response)
            else:
                print("缓存没命中，增加信息")
                # 缓存没命中，选择index指向的cache进行更新
                print("写入的"+ str(cache_index))
                cache_entry = cache[cache_index % CACHE_NUM]  
                
                # 修改各项记录
                cache_entry.httpHead.method = header.method
                cache_entry.httpHead.url = header.url
                cache_entry.httpHead.host = header.host
                cache_entry.httpHead.port = header.port
                cache_entry.buffer = response      
                print(headers)
                # print(response)
                
                # 获取 Last-Modified 时间
                cache_entry.date = headers.get('last-modified', '')
                print(cache_entry.date)
                # cache_entry.date = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
                
                # 更新索引
                cache_index += 1
                
                client_socket.send(response)
            
        except Exception as e:
            # print(cache)
            print(f"请求转发失败1：{e}")
            client_socket.close()
    
        finally:
            client_socket.close()
            remote_socket.close()



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

    # print(f"[*] 代理服务器正在运行，监听端口 {PROXY_PORT}")


    # 不断接受客户端请求并创建新线程处理
    while True:
        # 调用accept函数接收客户端请求
        # 返回的两个参数为(conn, address)
        #   conn为新的套接字对象，用来接受收和发送数据
        #   address是连接的客户端的地址
        client_socket, addr = proxy_socket.accept()
        
        
        # print(f"[*] 接受到来自 {addr} 的连接")


        # 为每个客户端请求创建一个新线程
        # threading.Thread声明了一个线程对象
        # threading.Thread(group=None, target=None, name=None, args=(), kwargs={}, *, daemon=None)
        #   group：应该设为None，即不用设置，使用默认值就好，因为这个参数是为了以后实现ThreadGroup类而保留的。
        #   target：在run方法中调用的可调用对象，即需要开启线程的可调用对象，比如函数或方法。
        #   name：线程名称，默认为“Thread-N”形式的名称，N为较小的十进制数。
        #   args：在参数target中传入的可调用对象的参数元组，默认为空元组()。
        #   kwargs：在参数target中传入的可调用对象的关键字参数字典，默认为空字典{}。
        #   daemon：默认为None，即继承当前调用者线程（即开启线程的线程，一般就是主线程）的守护模式属性，如果不为None，则无论该线程是否为守护模式，都会被设置为“守护模式”。
        client_handler = threading.Thread(target=handle_client, args=(client_socket,addr), daemon=True)
        # 开启线程活动
        client_handler.start()

# 缓存相关

# 添加If-Modified-Since头
def add_if_modified_since(request, last_modified):
    header_end = request.find(b"\r\n\r\n")  # 找到头部结束的位置
    if header_end != -1:
        headers = request[:header_end].decode('iso-8859-1').split('\r\n')
        body = request[header_end:]
        
        # 移除现有的 If-Modified-Since 头部（如果存在）
        headers = [line for line in headers if not line.lower().startswith('if-modified-since:')]
        
        # 添加新的 If-Modified-Since 头部
        headers.append(f"If-Modified-Since: {last_modified}")
        
        # 重新组合头部
        modified_header = '\r\n'.join(headers).encode('iso-8859-1')
        
        # 返回新的请求（头部 + 空行 + 原请求的主体）
        return modified_header + body
    return request  # 如果没有找到头部结束位置，返回原始请求


def get_last_modified(response):
    # 从响应头中提取Last-Modified字段
    headers = response.decode('utf-8').split("\r\n")
    for header in headers:
        if "Last-Modified" in header:
            return header.split(": ", 1)[1]
    return None

# 在main函数的情况下，开启代理
if __name__ == "__main__":
    start_proxy()
