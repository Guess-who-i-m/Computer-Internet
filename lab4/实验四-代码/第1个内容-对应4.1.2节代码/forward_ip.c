#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <arpa/inet.h>
#include <sys/socket.h>
int main()
{
  int sockfd;
  struct sockaddr_in src_addr, dest_addr, my_addr;
  char buffer[1024];
  socklen_t addr_len;
  int src_port = 12345;  // 原始端口号
  int dest_port = 54321; // 目标端口号（接收程序的端口号）
  // 创建 UDP 套接字
  if ((sockfd = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)) < 0)
  {
    perror("socket");
    return 1;
  }
  // 本地地址
  my_addr.sin_family = AF_INET;
  my_addr.sin_port = htons(src_port);
  my_addr.sin_addr.s_addr = INADDR_ANY;
  // 绑定套接字到本地地址
  if (bind(sockfd, (struct sockaddr *)&my_addr, sizeof(my_addr)) < 0)
  {
    perror("bind");
    return 1;
  }
  // 接收数据报
  addr_len = sizeof(src_addr);
  if (recvfrom(sockfd, buffer, sizeof(buffer), 0, (struct sockaddr *)&src_addr,
               &addr_len) < 0)
  {
    perror("recvfrom");
    return 1;
  }
  printf("Datagram received: %s\n", buffer);
  // 修改目标地址为接收程序主机的 IP 地址
  dest_addr.sin_family = AF_INET;
  dest_addr.sin_port = htons(dest_port);
  dest_addr.sin_addr.s_addr = inet_addr("192.168.79.131"); // 替换为接收程序主机的实际 IP 地址
  // 发送数据报
  if (sendto(sockfd, buffer, strlen(buffer), 0, (struct sockaddr *)&dest_addr,
             sizeof(dest_addr)) < 0)
  {
    perror("sendto");
    return 1;
  }
  printf("Datagram forwarded.\n");
  return 0;
}