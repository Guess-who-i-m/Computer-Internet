#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <unistd.h> // 为了使用 close 函数

int main()
{
    
    int sockfd;
    struct sockaddr_in dest_addr;
    char *message = NULL;
    char answer = '\0';
    int port = 12345; // 目标端口号
    int len  = 1024;

    

    // 创建 UDP 套接字
    if ((sockfd = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)) < 0)
    {
        perror("socket");
        return 1;
    }

    // 目标地址
    dest_addr.sin_family = AF_INET;
    dest_addr.sin_port = htons(port);
    dest_addr.sin_addr.s_addr = inet_addr("192.168.48.132");//目标 IP 地址"); 

    //询问是否发送并且接收信息
    do
    {
        printf("Continue to send?(Y or N)\n");
        answer = getchar();
        getchar(); // 读取并丢弃换行符

        if(answer == 'Y'){

            message = (char *)malloc(len * sizeof(char));
            if (message == NULL) {
                perror("malloc");
                return 1;
            }

            printf("Please input the information:\n");
            fgets(message, len, stdin);
            message[strcspn(message, "\n")] = 0;
            message[strcspn(message, "\n")] = 0;
            // getchar(); // 读取并丢弃换行符 

            if (sendto(sockfd, message, strlen(message), 0, (struct sockaddr *)&dest_addr, sizeof(dest_addr)) < 0)
            {
                perror("sendto");
                return 1;
            }

            free(message);
            message = NULL;

            printf("Datagram sent.\n");
        }

    }while(answer == 'Y');

    close(sockfd);
    return 0;
}