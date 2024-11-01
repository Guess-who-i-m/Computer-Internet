#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <arpa/inet.h>
#include <netinet/ip.h>
#include <netinet/if_ether.h>
#include <netinet/ether.h>
#include <sys/socket.h>
#include <unistd.h>
#include <linux/if_packet.h>
#include <net/if.h>
#include <sys/ioctl.h>
#include <time.h>
//#include <linux/if_arp.h>
#include <net/if_arp.h>

#define BUFFER_SIZE 65536
#define MAX_ROUTES 10

// 路由器条目
struct route_entry {
    char dest_ip[INET_ADDRSTRLEN];
    char next_hop[INET_ADDRSTRLEN];
    char iface[IFNAMSIZ];
};

// 路由表
struct route_entry routing_table[MAX_ROUTES] = {
    {"192.168.48.130", "192.168.48.130", "ens33"},
    {"10.0.0.2", "10.0.0.1", "ens38"}
};

// 寻找目的ip对应的路由表
const struct route_entry* lookup_next_hop(const char *dest_ip) {
    for (int i = 0; i < MAX_ROUTES; i++) {
        if (strcmp(routing_table[i].dest_ip, dest_ip) == 0) {
            return &routing_table[i];
        }
    }
    return NULL;
}



// 发送 ARP 广播请求
// 发送ARP请求
int send_arp_request(int sockfd, const char *src_ip_str, unsigned char *src_mac, const char *dest_ip_str, unsigned char *dest_mac, const char* iface)
{
    unsigned char buffer[42]; // ARP请求的长度为42字节
    struct in_addr src_ip, dest_ip;

    // 将字符串形式的IP地址转换为in_addr结构体
    if (inet_pton(AF_INET, src_ip_str, &src_ip) <= 0) {
        perror("Invalid source IP address");
        return -1;
    }

    if (inet_pton(AF_INET, dest_ip_str, &dest_ip) <= 0) {
        perror("Invalid destination IP address");
        return -1;
    }

    // 构造以太网头
    struct ether_header *eh = (struct ether_header *)buffer;
    memcpy(eh->ether_shost, src_mac, ETH_ALEN);
    memset(eh->ether_dhost, 0xFF, ETH_ALEN); // 广播地址
    eh->ether_type = htons(ETH_P_ARP);

    // 构造 ARP 请求
    struct ether_arp *arp_req = (struct ether_arp *)(buffer + sizeof(struct ether_header));
    arp_req->arp_hrd = htons(ARPHRD_ETHER);
    arp_req->arp_pro = htons(ETH_P_IP);
    arp_req->arp_hln = ETH_ALEN;
    arp_req->arp_pln = 4;
    arp_req->arp_op = htons(ARPOP_REQUEST);
    memcpy(arp_req->arp_sha, src_mac, ETH_ALEN);
    memcpy(arp_req->arp_spa, &src_ip.s_addr, 4);
    memset(arp_req->arp_tha, 0x00, ETH_ALEN);
    memcpy(arp_req->arp_tpa, &dest_ip.s_addr, 4);


    int if_index = if_nametoindex(iface);
    if (if_index == 0) {
        perror("Failed to get interface index");
        return -1;
    }

    // 设置 socket 地址结构
    struct sockaddr_ll socket_address;
    memset(&socket_address, 0, sizeof(socket_address));
    socket_address.sll_ifindex = if_index;
    socket_address.sll_halen = ETH_ALEN;
    memset(socket_address.sll_addr, 0xFF, ETH_ALEN); // 广播地址

    printf("ARP Request:\n");
    for (int i = 0; i < sizeof(buffer); i++) {
        printf("%02x ", buffer[i]);
        if ((i + 1) % 16 == 0) printf("\n");
    }

    // 发送 ARP 请求
    if (sendto(sockfd, buffer, sizeof(buffer), 0, (struct sockaddr *)&socket_address, sizeof(socket_address)) < 0)
    {
        perror("sendto ARP request");
        return -1;
    }

    printf("Sent ARP request for %s\n", dest_ip_str);
    return 0;
}


// 接收ARP回复
int receive_arp_response(int sockfd, const char *target_ip_str, unsigned char *target_mac)
{
    unsigned char buffer[BUFFER_SIZE];
    struct in_addr target_ip;

    // 将字符串形式的IP地址转换为in_addr结构体
    if (inet_pton(AF_INET, target_ip_str, &target_ip) <= 0) {
        perror("Invalid target IP address");
        return -1;
    }

    while (1)
    {
        int length = recvfrom(sockfd, buffer, BUFFER_SIZE, 0, NULL, NULL);
        if (length < 0)
        {
            perror("recvfrom ARP reply");
            return -1;
        }

        // printf("Received packet of length %d\n", length);

        struct ether_header *eh = (struct ether_header *)buffer;
        if (ntohs(eh->ether_type) == ETH_P_ARP)
        {
            struct ether_arp *arp_resp = (struct ether_arp *)(buffer + sizeof(struct ether_header));
            struct in_addr sender_ip;
            memcpy(&sender_ip.s_addr, arp_resp->arp_spa, 4);

            if (ntohs(arp_resp->arp_op) == ARPOP_REPLY && sender_ip.s_addr == target_ip.s_addr) {
                memcpy(target_mac, arp_resp->arp_sha, ETH_ALEN);
                printf("Received ARP reply from %s with MAC: ", inet_ntoa(sender_ip));
                for (int i = 0; i < ETH_ALEN; i++) {
                    printf("%02x ", target_mac[i]);
                }
                printf("\n");
                return 0; // 收到目标IP的ARP回复
            }
        }

        
    }
    return -1;
}


// 从arp协议获得mac地址
int get_mac_from_arp(int sockfd, const char *iface, const char* src_ip,unsigned char *src_mac, const char *dest_ip, unsigned char *dest_mac) {
    struct arpreq req;
    struct sockaddr_in *sin = (struct sockaddr_in *)&req.arp_pa;
    memset(&req, 0, sizeof(struct arpreq));
    sin->sin_family = AF_INET;
    sin->sin_addr.s_addr = inet_addr(dest_ip);
    strncpy(req.arp_dev, iface, IFNAMSIZ - 1);
    printf("ARP:\n");

    if (ioctl(sockfd, SIOCGARP, &req) == 0) {
        
        memcpy(dest_mac, req.arp_ha.sa_data, ETH_ALEN);
        printf("%s", dest_mac);
    }
    else
    {
        printf("Not found in ARP cahce, send broadcast request.\n");

            // int send_arp_request(int sockfd, const char *src_ip_str, unsigned char *src_mac, const char *dest_ip_str, unsigned char *dest_mac, int if_index)
        if(send_arp_request(sockfd, src_ip, src_mac, dest_ip, dest_mac, iface) < 0 )
        {
            printf("Arp broadcast request sent failed.\n");
            
        }

        if(receive_arp_response(sockfd,  dest_ip, dest_mac)<0)
        {
            printf("Arp broadcast request received failed.\n");
            
        }
    }

    
    return 0;
}



unsigned short checksum(void *b, int len)
{
  unsigned short *buf = b;
  unsigned int sum = 0;
  unsigned short result;
  for (sum = 0; len > 1; len -= 2)
    sum += *buf++;
  if (len == 1)
    sum += *(unsigned char *)buf;
  sum = (sum >> 16) + (sum & 0xFFFF);
  sum += (sum >> 16);
  result = ~sum;
  return result;
}



int main()
{
    // 创建socket
    int sockfd;
    struct sockaddr saddr;
    unsigned char *buffer = (unsigned char *)malloc(BUFFER_SIZE);
    sockfd = socket(AF_PACKET, SOCK_RAW, htons(ETH_P_ALL));
    // sockfd = socket(AF_PACKET, SOCK_RAW, htons(ETH_P_ARP));
    
    if (sockfd < 0)
    {
        perror("Socket creation failed");
        return 1;
    }

    // 循环的等待接收
    while (1)
    {
        // 接收到报文
        int saddr_len = sizeof(saddr);
        int data_size = recvfrom(sockfd, buffer, BUFFER_SIZE, 0, &saddr, (socklen_t *)&saddr_len);
        if (data_size < 0)
        {
            perror("Recvfrom error");
            return 1;
        }

        // 解析报文
        struct ethhdr *eth_header = (struct ethhdr *)buffer;
        struct iphdr *ip_header = (struct iphdr *)(buffer + sizeof(struct ethhdr));
        char src_ip[INET_ADDRSTRLEN];
        char dest_ip[INET_ADDRSTRLEN];
        inet_ntop(AF_INET, &(ip_header->saddr), src_ip, INET_ADDRSTRLEN);
        inet_ntop(AF_INET, &(ip_header->daddr), dest_ip, INET_ADDRSTRLEN);


        

        // 在路由表中寻找下一跳的信息
        const struct route_entry *route = lookup_next_hop(dest_ip);
        if (route == NULL) 
        {
            // printf("No route to host %s\n", dest_ip);
            continue; // 或丢弃该数据包
        }

        struct ifreq ifr;
        strncpy(ifr.ifr_name, route->iface, IFNAMSIZ - 1); // 使用路由表中的接口名
        if (ioctl(sockfd, SIOCGIFHWADDR, &ifr) < 0) {
            perror("ioctl");
            return -1;
        }
        unsigned char src_mac[ETH_ALEN];
        memcpy(src_mac, ifr.ifr_hwaddr.sa_data, ETH_ALEN);

        // 使用 ARP 获取下一跳 MAC 地址
        unsigned char next_hop_mac[ETH_ALEN];
        if (get_mac_from_arp(sockfd, route->iface, src_ip, src_mac, route->next_hop, next_hop_mac) < 0) 
        {
            // printf("ARP request failed for next hop %s\n", route->next_hop);
            continue; // 或丢弃该数据包
        }


        // 获取当前系统时间
        time_t rawtime;
        struct tm *timeinfo;
        char time_str[100];
        time(&rawtime);
        timeinfo = localtime(&rawtime);
        // 格式化时间字符串
        strftime(time_str, sizeof(time_str), "%Y-%m-%d %H:%M:%S", timeinfo);
            
        // 打印信息
        printf("[%s] Captured packet from %s to %s\n", time_str, src_ip, dest_ip);

        // 修改 TTL
        ip_header->ttl -= 1;
        ip_header->check = 0;
        ip_header->check = checksum((unsigned short *)ip_header, ip_header->ihl * 4);

        // 获取网卡接口索引
        struct ifreq ifr_mac;
        memset(&ifr, 0, sizeof(ifr));
        snprintf(ifr.ifr_name, sizeof(ifr.ifr_name), route->iface);
        if (ioctl(sockfd, SIOCGIFINDEX, &ifr) < 0)
        {
            perror("ioctl");
            return 1;
        }
        // 获取网卡接口 MAC 地址
        memset(&ifr_mac, 0, sizeof(ifr_mac));
        snprintf(ifr_mac.ifr_name, sizeof(ifr_mac.ifr_name), route->iface);
        if (ioctl(sockfd, SIOCGIFHWADDR, &ifr_mac) < 0)
        {
            perror("ioctl");
            return 1;
        }

        // 发送数据包到目的主机
        // 设置 MAC 地址和接口
        struct sockaddr_ll dest = {0};
        dest.sll_ifindex = ifr.ifr_ifindex;
        dest.sll_halen = ETH_ALEN;
        memcpy(dest.sll_addr, next_hop_mac, ETH_ALEN);


        // 构造新的以太网帧头
        memcpy(eth_header->h_dest, next_hop_mac, ETH_ALEN);                   // 目标 MAC 地址
        memcpy(eth_header->h_source, ifr_mac.ifr_hwaddr.sa_data, ETH_ALEN);  // 源 MAC   地址
        eth_header->h_proto = htons(ETH_P_IP);                               // 以太网类型为 IP
        printf("Interface name: %s, index: %d\n", ifr.ifr_name, ifr.ifr_ifindex);

        printf("Sending packet to %s with MAC: ", dest_ip);
        for (int i = 0; i < ETH_ALEN; i++) {
            printf("%02x ", next_hop_mac[i]);
        }
        printf("\n");

        if (sendto(sockfd, buffer, data_size, 0, (struct sockaddr *)&dest, sizeof(dest)) < 0)
        {
            perror("Sendto error");
            return 1;
        }
        printf("Datagram forwarded.\n");
    }
    close(sockfd);
    free(buffer);
    return 0;
}

