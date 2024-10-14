import gbn as gbn
import threading

SERVER_IP = '127.0.0.1'
SERVER_PORT1 = 12345
SERVER_PORT2 = 12347

CLIENT_IP = '127.0.0.1'
CLIENT_PORT1 = 12346
CLIENT_PORT2 = 12348

# 模拟要发送的数据
data1_list = [f"Data1 {i}" for i in range(50)]  # 模拟要传输的数据

data2_list = [f"Data2 {i}" for i in range(50)]  # 模拟要传输的数据

Thread_Server_Send = threading.Thread(target=gbn.server_program, args=(SERVER_IP, SERVER_PORT1, CLIENT_IP, CLIENT_PORT2, data1_list,))
Thread_Server_Recv = threading.Thread(target=gbn.client_program, args=(SERVER_IP, SERVER_PORT2,  ))

Thread_Client_Send = threading.Thread(target=gbn.server_program, args=(CLIENT_IP, CLIENT_PORT1, SERVER_IP, SERVER_PORT2, data2_list))
Thread_Client_Recv = threading.Thread(target=gbn.client_program, args=(CLIENT_IP, CLIENT_PORT2, ))

Thread_Server_Send.start()
Thread_Server_Recv.start()

Thread_Client_Send.start()
Thread_Client_Recv.start()



# import gbn_d
# import threading

# SERVER_IP = '127.0.0.1'
# SERVER_PORT1 = 12345
# SERVER_PORT2 = 12347

# CLIENT_IP = '127.0.0.1'
# CLIENT_PORT1 = 12346
# CLIENT_PORT2 = 12348

# # 模拟要发送的数据
# data1_list = [f"Data1 {i}" for i in range(50)]  # 模拟要传输的数据

# data2_list = [f"Data2 {i}" for i in range(50)]  # 模拟要传输的数据

# Thread_Server_Send = threading.Thread(target=gbn_d.gbn_sender, args=(SERVER_IP, SERVER_PORT1, CLIENT_IP, CLIENT_PORT2, data1_list, "服务端发送"))
# Thread_Server_Recv = threading.Thread(target=gbn_d.gbn_receiver, args=(SERVER_IP, SERVER_PORT2,"服务端接收",  ))

# Thread_Client_Send = threading.Thread(target=gbn_d.gbn_sender, args=(CLIENT_IP, CLIENT_PORT1, SERVER_IP, SERVER_PORT2, data2_list, "客户端发送"))
# Thread_Client_Recv = threading.Thread(target=gbn_d.gbn_receiver, args=(CLIENT_IP, CLIENT_PORT2, "客户端接收", ))

# Thread_Server_Send.start()
# Thread_Server_Recv.start()

# Thread_Client_Send.start()
# Thread_Client_Recv.start()