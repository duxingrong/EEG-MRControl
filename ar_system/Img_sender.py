# -*- coding: utf-8 -*-
"""
UDP Image-Sending Module
"""

import cv2
import socket
import numpy as np
import time




# Each packet has a maximum size of 8,192 bytes == 8KB
SAFE_CHUNK_SIZE=8192

# 协议设计如下：
# b'\x01' - 开始包: [类型0x01 (1字节)] + [总包数 (2字节)]
# b'\x02' - 结束包: [类型0x02 (1字节)]
# b'\x00' - 数据包: [类型0x00 (1字节)] + [包序号 (2字节)] + [数据内容]

def send_image(image_rgb, host, port):
    """
    Compress, segment, and transmit the image

    Args:
        image_rgb (np.array): 从cv2.imread()或Realsense获取的原始RGB图像 (NumPy array)。
        host (str): 目标主机的IP地址 (例如 '192.168.1.100' 或 HoloLens的IP)。
        port (int): 目标主机的端口号。
    """

    # Creating the socket inside the function guarantees a fresh intance on every call
    # eliminating interference from any previously unclosed sockets
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock: # UDP
        try:
            # 1. Compress Image
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 10]
            _, img_encoded = cv2.imencode('.jpg', image_rgb, encode_param)
            
            # 从一个装着字节的NumPy容器对象中，提取出纯粹的字节序列
            img_bytes = img_encoded.tobytes()
            
            # 2. Data segment
            size = len(img_bytes)
            max_data_size = SAFE_CHUNK_SIZE - 3 # 减去1字节标志+两个字节的包序号
            num_packets = (size + max_data_size - 1) // max_data_size

                        
            if num_packets > 65535: # 2^16-1 = 65535 
                print("错误：图像太大，分割后的包数超过65535！")
                return

            # 发送一个“开始”信号，包含总包数
            # 格式: b'\x01' (开始标志) + [包总数 (2字节)]
            start_packet = b'\x01' + num_packets.to_bytes(2, 'big') # 大端字节序列
            sock.sendto(start_packet, (host, port))
            
            # 循环发送每一个数据块
            for i in range(num_packets):
                start = i * max_data_size
                end = start + max_data_size
                
                # [0x00 数据标志(1字节)] + [包序号 (2字节)] + [数据内容]
                packet = b'\x00' +  i.to_bytes(2, 'big') + img_bytes[start:end]
                
                # 发送数据
                sock.sendto(packet, (host, port))
                # 短暂延时，防止接收端缓冲区溢出，这里很重要！！！
                time.sleep(0.0001) 

            # 发送一个“结束”信号
            # 格式: b'\x02' (结束标志)
            end_packet = b'\x02'
            sock.sendto(end_packet, (host, port))

            # print(f"图像已发送，大小: {size} 字节, 分为 {num_packets} 个包。")

        except Exception as e:
            print(f"发送图像时发生错误: {e}")
        finally:
            # 关闭socket
            sock.close()


if __name__ == '__main__':
    HOLOLENS_IP = "127.0.0.1"  
    UDP_PORT = 9999

    # Use sample images instead of live camera feeds
    try:
        test_image = cv2.imread('test.jpg') 
        if test_image is None:
            print("未找到 'test.jpg'，将创建一个黑色图像用于测试。")
            test_image = np.zeros((480, 640, 3), dtype=np.uint8)

        print(f"开始向 {HOLOLENS_IP}:{UDP_PORT} 发送图像...")
        
        # Simulate a video stream and transmit continuosuly
        while True:
            send_image(test_image, HOLOLENS_IP, UDP_PORT)
            # Control the transmission frame rate , 30fps
            time.sleep(1/30) 

    except KeyboardInterrupt:
        print("\n程序已停止。")