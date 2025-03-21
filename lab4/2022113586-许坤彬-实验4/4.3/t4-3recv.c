#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <unistd.h>
#define PORT 12345
#define MESSAGE "Hello, fuck you too!"


int main()
{
  int sockfd;
  struct sockaddr_in server_addr, client_addr;
  socklen_t addr_len = sizeof(client_addr);
  char buffer[1024];
  // 创建 UDP 套接字
  sockfd = socket(AF_INET, SOCK_DGRAM, 0);
  if (sockfd < 0)
  {
    perror("Socket creation failed");
    return 1;
  }
  // 绑定套接字到端口
  memset(&server_addr, 0, sizeof(server_addr));
  server_addr.sin_family = AF_INET;
  server_addr.sin_addr.s_addr = INADDR_ANY;
  server_addr.sin_port = htons(PORT);
  if (bind(sockfd, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0)
  {
    perror("Bind failed");
    return 1;
  }
  // 接收数据包
  int recv_len = recvfrom(sockfd, buffer, sizeof(buffer) - 1, 0, (struct sockaddr *)&client_addr, &addr_len);
  if (recv_len < 0)
  {
    perror("Recvfrom failed");
    return 1;
  }
  buffer[recv_len] = '\0';
  printf("Received message: %s\n", buffer);

  // 获取客户端的IP地址
  char client_ip[INET_ADDRSTRLEN];
  inet_ntop(AF_INET, &client_addr.sin_addr, client_ip, INET_ADDRSTRLEN);
  printf("Client IP: %s, Port: %d\n", client_ip, ntohs(client_addr.sin_port));

  // 发送消息回客户端
  if (sendto(sockfd, MESSAGE, strlen(MESSAGE), 0, (struct sockaddr *)&client_addr, addr_len) < 0)
  {
    perror("Sendto failed");
    close(sockfd);
    return 1;
  }
  printf("Message sent to server: %s\n", MESSAGE);

  close(sockfd);
  return 0;
}