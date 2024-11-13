#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <arpa/inet.h>
#include <netinet/ip.h>
#include <netinet/if_ether.h>
#include <sys/socket.h>
#include <unistd.h>
#include <linux/if.h>
#include <linux/if_packet.h>
#include <sys/ioctl.h>
#include <time.h>

#define BUFFER_SIZE 65536

struct route_entry
{
  uint32_t dest;
  uint32_t gateway;
  uint32_t netmask;
  char interface[IFNAMSIZ];
};
struct route_entry route_table[2];

int route_table_size = sizeof(route_table) / sizeof(route_table[0]);

void convert_to_ip_string(uint32_t ip_addr, char *ip_str)
{
  struct in_addr addr;
  addr.s_addr = ip_addr; // htonl(ip_addr); // 转换为网络字节序 inet_ntop(AF_INET, &addr, ip_str, INET_ADDRSTRLEN);
  inet_ntop(AF_INET, &addr, ip_str, INET_ADDRSTRLEN);
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

struct route_entry *lookup_route(uint32_t dest_ip)
{

  char ip_str[32];

  for (int i = 0; i < route_table_size; i++)
  {
    if ((dest_ip & route_table[i].netmask) == (route_table[i].dest & route_table[i].netmask))
    {

      convert_to_ip_string(dest_ip, ip_str);
      convert_to_ip_string(route_table[i].dest, ip_str);
      return &route_table[i];
    }
  }
  return NULL;
}

void initialize_route_table()
{
  route_table[0].dest = inet_addr("192.168.1.121");       // 子网1的目的地址
  route_table[0].gateway = inet_addr("192.168.1.120");    // 子网1的网关
  route_table[0].netmask = inet_addr("255.255.255.0");
  strcpy(route_table[0].interface, "ens33");
  route_table[1].dest = inet_addr("192.168.2.121");       // 子网2的目的地址
  route_table[1].gateway = inet_addr("192.168.2.120");    // 子网2的网关
  route_table[1].netmask = inet_addr("255.255.255.0");
  strcpy(route_table[1].interface, "ens37");
}

int main()
{
  int sockfd;
  struct sockaddr saddr;
  unsigned char *buffer = (unsigned char *)malloc(BUFFER_SIZE);
  uint16_t src_port, dest_port;

  initialize_route_table();

  sockfd = socket(AF_PACKET, SOCK_RAW, htons(ETH_P_IP));
  if (sockfd < 0)
  {
    perror("Socket creation failed");
    return 1;
  }
  while (1)
  {
    int saddr_len = sizeof(saddr);
    int data_size = recvfrom(sockfd, buffer, BUFFER_SIZE, 0, &saddr, (socklen_t *)&saddr_len);

    strcpy(buffer, "ddd");

    if (data_size < 0)
    {
      perror("Recvfrom error");
      return 1;
    }
    if (data_size == 0)      continue;
    struct ethhdr *eth_header = (struct ethhdr *)buffer;

    struct iphdr *ip_header = (struct iphdr *)(buffer + sizeof(struct ethhdr));
    struct route_entry *route = lookup_route(ip_header->daddr);

    if (route == NULL)
    {
      // fprintf(stderr, "No route to host\n");
      continue;
    }
    char ip_s[32],ip_d[32];
    convert_to_ip_string(ip_header->saddr, ip_s);
    convert_to_ip_string(ip_header->daddr, ip_d);

    // 提取发送端的源 MAC 地址
    unsigned char *src_mac = eth_header->h_source;
    unsigned char *dest_mac = eth_header->h_dest;
    if(strcmp(ip_s,"192.168.1.1")!=0 && strcmp(ip_s,"192.168.2.1")!=0)
    {
        // 打印信息
        printf("Captured packet from %s to %s\n", ip_s, ip_d);
        printf("Source MAC (from sender): %02x:%02x:%02x:%02x:%02x:%02x\n",
               src_mac[0], src_mac[1], src_mac[2], src_mac[3], src_mac[4], src_mac[5]);

        // 修改 TTL
        ip_header->ttl -= 1;
        ip_header->check = 0;
        ip_header->check = checksum((unsigned short *)ip_header, ip_header->ihl * 4);

        printf("ttl: %d\n", ip_header->ttl);
        
        src_port = ntohs(*(uint16_t *)(buffer + sizeof(struct ethhdr) + ip_header->ihl * 4));
        dest_port = ntohs(*(uint16_t *)(buffer + sizeof(struct ethhdr) + ip_header->ihl * 4 + 2));

        printf("Source Port: %u\n", src_port);
        printf("Destination Port: %u\n", dest_port);

    }


    

    // 发送数据包到目的主机
    struct ifreq ifr, ifr_mac;
    struct sockaddr_ll dest;
    // 获取网卡接口索引
    memset(&ifr, 0, sizeof(ifr));
    snprintf(ifr.ifr_name, sizeof(ifr.ifr_name), route->interface);
    if (ioctl(sockfd, SIOCGIFINDEX, &ifr) < 0)
    {
      perror("ioctl");
      return 1;
    }
    // 获取网卡接口 MAC 地址
    memset(&ifr_mac, 0, sizeof(ifr_mac));
    snprintf(ifr_mac.ifr_name, sizeof(ifr_mac.ifr_name), route->interface);
    if (ioctl(sockfd, SIOCGIFHWADDR, &ifr_mac) < 0)
    {
      perror("ioctl");
      return 1;
    }
    // 设置目标 MAC 地址（假设目标地址已知,此处做了简化处理，实际上，如果查找路由表后，存在“下
    // 一跳”，应该利用 ARP 协议获得 route->gateway 的 MAC 地址，如果是“直接交付”的话，也应使用 ARP 协议获得
    // 目的主机的 MAC 地址。）
    unsigned char target_mac[ETH_ALEN]; // 在外部声明

    if (!strcmp(ip_d, "192.168.1.121")) {
        // 这里可以设置 target_mac 的值
        memcpy(target_mac, (unsigned char[]){0x00, 0x50, 0x56, 0x31, 0xf4, 0x92}, ETH_ALEN);
    } else if (!strcmp(ip_d, "192.168.2.121")) {
        // 这里也可以设置 target_mac 的值
       memcpy(target_mac, (unsigned char[]){0x00, 0x50, 0x56, 0x22, 0x72, 0x32}, ETH_ALEN); // 更改 MAC 地址
    } else {
        // 其他情况
    }

    // 替换为实际的目标 MAC 地址
    memset(&dest, 0, sizeof(dest));
    dest.sll_ifindex = ifr.ifr_ifindex;
    dest.sll_halen = ETH_ALEN;
    memcpy(dest.sll_addr, target_mac, ETH_ALEN);
    // 构造新的以太网帧头
    memcpy(eth_header->h_dest, target_mac, ETH_ALEN);                   // 目标 MAC 地址
    memcpy(eth_header->h_source, ifr_mac.ifr_hwaddr.sa_data, ETH_ALEN); // 源 MAC 地址
    eth_header->h_proto = htons(ETH_P_IP);                              // 以太网类型为 IP
    //printf("Interface name: %s, index: %d\n", ifr.ifr_name, ifr.ifr_ifindex);

    if(strcmp(ip_s,"192.168.1.1")!=0 && strcmp(ip_s,"192.168.2.1")!=0)
    {

        printf("Destination MAC: %02x:%02x:%02x:%02x:%02x:%02x\n",
               dest_mac[0], dest_mac[1], dest_mac[2], dest_mac[3], dest_mac[4], dest_mac[5]);
    }

    if (sendto(sockfd, buffer, data_size, 0, (struct sockaddr *)&dest, sizeof(dest)) < 0)
    {
      perror("Sendto error");
      return 1;
    }
  }
  close(sockfd);
  free(buffer);
  return 0;
}