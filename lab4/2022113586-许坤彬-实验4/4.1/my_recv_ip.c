#include <stdio.h>
#include <stdlib.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <string.h>
#include <time.h>
int main()
{
  int sockfd;
  struct sockaddr_in src_addr, my_addr;
  char* buffer = NULL;
  socklen_t addr_len;
  int port = 54321; // 修改后的接收端口号
  int len = 1024;
  // 创建 UDP 套接字
  if ((sockfd = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)) < 0)
  {
    perror("socket");
    return 1;
  }
  // 本地地址
  my_addr.sin_family = AF_INET;
  my_addr.sin_port = htons(port);
  my_addr.sin_addr.s_addr = INADDR_ANY;

  // 绑定套接字到本地地址
  if (bind(sockfd, (struct sockaddr *)&my_addr, sizeof(my_addr)) < 0)
  {
    perror("bind");
    return 1;
  }

  // 接收数据报
  while(1)
  {
    addr_len = sizeof(src_addr);
    buffer = (char*)malloc(len*sizeof(char));
    memset(buffer, 0, sizeof(buffer));
    if (recvfrom(sockfd, buffer, len, 0, (struct sockaddr *)&src_addr, &addr_len) < 0)
    {
      perror("recvfrom");
      return 1;
    }

    time_t now;
    time(&now);
    struct tm *local = localtime(&now);
    local->tm_hour += 8;
    mktime(local);  //标准化时间，处理溢出情况（例如可能加8小时后超过24小时）
    printf("Time: %02d:%02d:%02d ,Datagram received: %s\n", local->tm_hour, local->tm_min, local->tm_sec, buffer);

    free(buffer);
    buffer = NULL;
  }

  return 0;
}