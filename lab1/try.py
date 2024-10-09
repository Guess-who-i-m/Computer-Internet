import socket
import threading
import time
import os

MAXSIZE = 65507  # 发送数据报文的最大长度
DATELENGTH = 50  # 时间字节数
CACHE_NUM = 50   # 定义最大缓存数量

from concurrent.futures import ThreadPoolExecutor
# 用于处理异步写入任务
executor = ThreadPoolExecutor(max_workers=5)  # 创建一个线程池，最多5个线程并发写入

# HTTP 重要头部数据 用来存储解析后的HTTP请求头信息
class HttpHeader:
    def __init__(self):
        self.method = ''  # GET、POST 或 CONNECT
        self.url = ''     # 请求的 URL
        self.host = ''    # 目标主机
        self.port = 80    # 目标端口
        self.cookie = ''  # Cookie

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
cache_index = 0  # 当前应将缓存放在哪个位置

# 禁止访问的网站列表
invalid_website = ["http://www.hit.edu.cn"]
invalid_website_num = len(invalid_website)

# 钓鱼网站配置
fishing_src = "http://today.hit.edu.cn"
fishing_dest = "http://jwes.hit.edu.cn"
fishing_dest_host = "jwes.hit.edu.cn"

# 限制访问的用户IP
restrict_host = ["127.0.0.1"]

# 选做功能开关
button = True  # True表示开启选做功能

def init_socket(proxy_port):
    # 初始化套接字 AF_INET是IPv4
    proxy_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_server.bind(('0.0.0.0', proxy_port))
    proxy_server.listen(5)  
    print(f"代理服务器正在运行，监听端口 {proxy_port}")
    return proxy_server

def parse_http_header(data):
    # 解析 HTTP 头部
    header = HttpHeader()
    lines = data.decode('iso-8859-1').split('\r\n')
    request_line = lines[0]
    parts = request_line.split()
    if len(parts) >= 3:
        header.method = parts[0]
        header.url = parts[1]
        if header.method.upper() == 'CONNECT':
            # CONNECT 方法，URL 格式为 host:port
            host_port = header.url
            if ':' in host_port:
                header.host, port = host_port.split(':', 1)
                header.port = int(port)
            else:
                header.host = host_port
                header.port = 443  # 默认 HTTPS 端口
        else:
            # 其他方法GET、POST，从 Host 头部获取主机名和端口
            for line in lines[1:]:
                if line.startswith('Host:'):
                    host_line = line[5:].strip()
                    if ':' in host_line:
                        header.host, port = host_line.split(':', 1)
                        header.port = int(port)
                    else:
                        header.host = host_line
                        header.port = 80  # 默认 HTTP 端口
                elif line.startswith('Cookie:'):
                    header.cookie = line[8:]
    else:
        return None

    return header

def connect_to_server(host, port):
    # 连接到目标服务器
    try:
        server_ip = socket.gethostbyname(host)
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.connect((server_ip, port))
        return server_socket
    except Exception as e:
        print(f"连接到服务器 {host}:{port} 时出错：{e}")
        return None

def http_equal(http1, http2):
    # 判断两个 HTTP 报文是否相同
    return (http1.method == http2.method and http1.host == http2.host
            and http1.url == http2.url and http1.port == http2.port)

def is_in_cache(cache, http_header):
    # 检查缓存中是否存在对应的条目
    for index, entry in enumerate(cache):
        if http_equal(entry.httpHead, http_header):
            return index
    return -1

def change_http(buffer, date):
    # 修改 HTTP 请求，插入 If-Modified-Since 头部
    # ISO-8859-1 是一种 字符编码标准
    lines = buffer.decode('iso-8859-1').split('\r\n')
    # 插入 If-Modified-Since 头部
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        new_lines.append(line)
        if line.startswith('Host:'):
            # 在 Host 后面插入 If-Modified-Since 头部
            new_lines.append(f"If-Modified-Since: {date}")
        i += 1
        if line == '':
            break  # 头部结束
    # 添加剩余的行
    new_lines.extend(lines[i:])
    return '\r\n'.join(new_lines).encode('iso-8859-1')

def modify_request_for_phishing(request, http_header):
    # 修改请求，进行钓鱼网站重定向 返回新的请求url
    lines = request.decode('iso-8859-1').split('\r\n')
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
    return '\r\n'.join(new_lines).encode('iso-8859-1')

def parse_http_response(response):
    # 解析 HTTP 响应，获取状态行、头部和正文
    header_end = response.find(b'\r\n\r\n')
    if header_end == -1:
        return None, None, None
    header_bytes = response[:header_end]
    body = response[header_end+4:]
    header_text = header_bytes.decode('iso-8859-1', errors='ignore')
    lines = header_text.split('\r\n')
    status_line = lines[0]
    headers = {}
    for line in lines[1:]:
        if ': ' in line:
            key, value = line.split(': ', 1)
            headers[key.lower()] = value
    return status_line, headers, body

def save_cache_to_file_async(cache_entry):
    # 异步写入缓存内容到文件
    def write_to_file():
        filename = f"cache_{cache_entry.httpHead.host}_{cache_entry.httpHead.url.replace('/', '_')}.txt"
        filename = filename.replace(':', '_').replace('?', '_').replace('&', '_')
        with open(filename, 'wb') as f:
            f.write(cache_entry.buffer)
        print(f"缓存内容已异步保存到文件 {filename}")
    
    # 提交异步写入任务
    executor.submit(write_to_file)


def handle_https_tunnel(client_socket, http_header):
    try:
        # 连接目标服务器
        server_socket = connect_to_server(http_header.host, http_header.port)
        if not server_socket:
            print(f"无法连接到服务器 {http_header.host}:{http_header.port}")
            client_socket.close()
            return
        print(f"建立 HTTPS 隧道到 {http_header.host}:{http_header.port}")

        # 向客户端发送 200 Connection Established 响应
        client_socket.sendall(b'HTTP/1.1 200 Connection Established\r\n\r\n')

        # 开始转发数据，建立双向通信
        t1 = threading.Thread(target=forward, args=(client_socket, server_socket))
        t2 = threading.Thread(target=forward, args=(server_socket, client_socket))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
    except Exception as e:
        print(f"处理 HTTPS 隧道时出错：{e}")
    finally:
        pass  # 套接字的关闭在 forward 函数中处理

def forward(source, destination):
    try:
        while True:
            data = source.recv(4096)
            if not data:
                break
            destination.sendall(data)
    except Exception as e:
        pass
    finally:
        source.close()
        destination.close()

def proxy_thread(client_socket, client_address):
    global cache_index
    is_https_tunnel = False  # 标志变量，指示是否为 HTTPS 隧道
    server_socket = None
    try:
        # 接收客户端请求
        request = client_socket.recv(MAXSIZE)
        if not request:
            client_socket.close()
            return

        http_header = parse_http_header(request)
        if not http_header:
            client_socket.close()
            return

        # 限制访问用户
        if button and client_address[0] not in restrict_host:
            print("该用户访问受限")
            client_socket.close()
            return

        # 处理禁止访问网站
        if button and any(site in http_header.url for site in invalid_website):
            print("--------该网站已被屏蔽!----------")
            client_socket.close()
            return

        # 处理钓鱼网站
        if button and fishing_src in http_header.url:
            print(f"已从源网址：{fishing_src} 转到 目的网址 ：{fishing_dest}")
            http_header.host = fishing_dest_host
            http_header.url = fishing_dest
            # 修改请求
            request = modify_request_for_phishing(request, http_header)

        # 处理 HTTPS CONNECT 方法
        if http_header.method.upper() == 'CONNECT':
            is_https_tunnel = True  # 标记为 HTTPS 隧道请求
            handle_https_tunnel(client_socket, http_header)
            return  # HTTPS 隧道已处理

        # 连接目标服务器
        server_socket = connect_to_server(http_header.host, http_header.port)
        if not server_socket:
            print(f"无法连接到服务器 {http_header.host}:{http_header.port}")
            client_socket.close()
            return
        print(f"代理连接主机 {http_header.host}:{http_header.port}")

        # 检查缓存
        index = is_in_cache(cache, http_header)
        if index > -1:
            # 缓存命中，添加 If-Modified-Since 头部
            cache_entry = cache[index]
            modified_request = change_http(request, cache_entry.date)
            server_socket.sendall(modified_request)
            print("已发送带 If-Modified-Since 的请求")
        else:
            # 缓存未命中，直接发送请求
            server_socket.sendall(request)
            print("缓存未命中，向服务器发送请求")

        # 接收服务器响应
        response = b''
        while True:
            data = server_socket.recv(4096)
            if not data:
                break
            response += data

        if not response:
            return

        # 解析响应
        status_line, headers, body = parse_http_response(response)
        if not status_line:
            # 无法解析响应，直接转发
            client_socket.sendall(response)
            return

        if index > -1:
            # 如果是缓存命中后的请求
            if '304' in status_line:
                # 资源未修改，使用缓存
                client_socket.sendall(cache_entry.buffer)
                print("将缓存内容返回给客户端")
            else:
                # 资源已更新，返回新的内容并更新缓存
                client_socket.sendall(response)
                print("资源已更新，返回新的内容并更新缓存")
                cache_entry.buffer = response
                # 获取新的 Last-Modified 时间
                cache_entry.date = headers.get('last-modified', '')
                # 保存缓存内容到文件
                save_cache_to_file_async(cache_entry)
        else:
            # 缓存未命中
            client_socket.sendall(response)
            print("缓存未命中，返回服务器的响应")
            # 添加到缓存
            cache_entry = cache[cache_index % CACHE_NUM]
            cache_entry.httpHead.method = http_header.method
            cache_entry.httpHead.url = http_header.url
            cache_entry.httpHead.host = http_header.host
            cache_entry.httpHead.port = http_header.port
            cache_entry.buffer = response
            # 获取 Last-Modified 时间
            cache_entry.date = headers.get('last-modified', '')
            cache_index += 1
            # 保存缓存内容到文件
            save_cache_to_file_async(cache_entry)

    except Exception as e:
        print(f"处理请求时出错：{e}")
    finally:
        if not is_https_tunnel:
            client_socket.close()
            if server_socket:
                server_socket.close()
        # 如果是 HTTPS 隧道，套接字的关闭在 forward 函数中处理

def main():
    proxy_port = 10240
    proxy_server = init_socket(proxy_port)
    while True:
        try:
            client_socket, client_address = proxy_server.accept()
            print(f"接受来自 {client_address} 的连接")
            threading.Thread(target=proxy_thread, args=(client_socket, client_address)).start()
        except KeyboardInterrupt:
            print("代理服务器已停止")
            proxy_server.close()
            break
        except Exception as e:
            print(f"发生错误：{e}")
            continue

if __name__ == '__main__':
    main()
