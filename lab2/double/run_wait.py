import wait as wait
import threading

SERVER_IP = '127.0.0.1'
SERVER_SEND_PORT = 12345
SERVER_RECV_PORT = 12347

CLIENT_IP = "127.0.0.1"
CLIENT_SEND_PORT = 12346
CLIENT_RECV_PORT = 12348

# 模拟要传输的数据
data_packet1 = ["数据包1:哈", "数据包2：尔", "数据包3：滨", "数据包4：工", "数据包5：业",  "数据包6：大", "数据包7：学"]
data_packet2 = ["数据包1:规", "数据包2：格", "数据包3：严", "数据包4：格", "数据包5：功",  "数据包6：夫", "数据包7：到", "数据包8：家"]


Thread_Server_send = threading.Thread(target=wait.udp_server, args=(SERVER_IP, SERVER_SEND_PORT, CLIENT_IP, CLIENT_RECV_PORT, data_packet1, ))
Thread_Server_recv = threading.Thread(target=wait.udp_client, args=(SERVER_IP, SERVER_RECV_PORT, ))

Thread_Client_send = threading.Thread(target=wait.udp_server, args=(CLIENT_IP, CLIENT_SEND_PORT, SERVER_IP, SERVER_RECV_PORT, data_packet2, ))
Thread_Client_recv = threading.Thread(target=wait.udp_client, args=(CLIENT_IP, CLIENT_RECV_PORT, ))

Thread_Server_send.start()
Thread_Client_recv.start()

Thread_Client_send.start()
Thread_Server_recv.start()