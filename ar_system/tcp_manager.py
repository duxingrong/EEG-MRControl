# -*- coding: utf-8 -*-
"""
TCP client for bidirectional data transfer
双向传输的数据格式一定都是信封，即{type:, payload:}
"""

import socket
import threading
import time
import json


class TCPClient:
    def __init__(self, host, port=9998):
        """
        Initialize TCP Client
        Args:
            host (str): HoloLens 2 (server) IP address
            port (int): Socket Port
        """
        self.host = host
        self.port = port
        self.client_socket = None
        self.is_running = False
        self.connection_thread = None
        # Create a dictionary to store the callback functions
        self.callbacks = {}

    # Register the callback functions
    def register_callback(self, msg_type, callback_func):
        """
        Register a function for the specified message type
        Args:
            msg_type (str): message type
            callback_func (function): The function to be invoked upon receiving a message of this type
        """
        self.callbacks[msg_type] = callback_func
        print(f"已为消息类型 '{msg_type}' 注册回调函数: {callback_func.__name__}")


    def start(self):
        """Start the client and attempt to connect to the server"""
        if self.is_running:
            print("客户端已在运行中。")
            return
            
        self.is_running = True
        self.connection_thread = threading.Thread(target=self._connection_loop)
        self.connection_thread.daemon = True
        self.connection_thread.start()

    def _connection_loop(self):
        """
        A continuous loop that keeps attempting to connect 
        and maintain the connection with the server
        """
        while self.is_running:
            try:
                print(f"正在尝试连接到HoloLens服务器 {self.host}:{self.port}...")
                
                self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client_socket.connect((self.host, self.port))
                print(f"成功连接到HoloLens服务器！")
                
                self._receive_loop()

            except (socket.error, ConnectionRefusedError) as e:
                print(f"连接失败: {e}。将在5秒后重试...")
                self.client_socket = None # Ensure the socket is properly cleaned up after any failure
            except Exception as e:
                print(f"连接循环中发生未知错误: {e}")
                self.client_socket = None

            if self.is_running:
                time.sleep(5) # Wait before retrying

        print("连接循环已停止。")

    def _receive_loop(self):
        """Handle incoming data from the server"""
        while self.is_running and self.client_socket:
            try:
                # Receive 4-byte length prefix firstly 
                length_prefix = self.client_socket.recv(4)
                if not length_prefix:
                    print("服务器已关闭连接。")
                    break
                
                message_length = int.from_bytes(length_prefix, 'big')
                
                # Receive the complete message based on the length prefix
                data = b''
                while len(data) < message_length:
                    packet = self.client_socket.recv(message_length - len(data))
                    if not packet:
                        raise ConnectionError("收到的消息不完整，连接可能已丢失。")
                    data += packet
                
                message_str = data.decode('utf-8')
                envelope = json.loads(message_str)
                msg_type = envelope.get("type")
                payload = envelope.get("payload")
                
                # Invoke the registered callback function
                if msg_type in self.callbacks:
                    self.callbacks[msg_type](payload)
                else:
                    print(f"警告: 收到未注册回调的消息类型 '{msg_type}'")

            except (ConnectionResetError, ConnectionAbortedError, ConnectionError) as e:
                print(f"连接已断开: {e}")
                break
            except Exception as e:
                print(f"接收数据时发生错误: {e}")
                break
        
        # Clean up after the loop ends
        if self.client_socket:
            self.client_socket.close()
            self.client_socket = None
        print("接收循环结束。将尝试重新连接。")

    def send(self, msg_type, payload):
        """
        Send data to the connected Hololens server (str, dict, list)。
        """
        if not self.is_client_connected():
            print("无法发送数据，未连接到服务器。")
            return False

        try:
            # 无论payload是什么，都先将其转换为字符串（如果是字典/列表，则转换为JSON字符串）
            if isinstance(payload, (dict, list)):
                payload_str = json.dumps(payload)
            else:
                payload_str = str(payload)

            envelope = {
                "type": msg_type,
                "payload": payload_str
            }
            message = json.dumps(envelope)
            
            encoded_message = message.encode('utf-8')
            length_prefix = len(encoded_message).to_bytes(4, 'big')

            self.client_socket.sendall(length_prefix + encoded_message)
            return True
        except Exception as e:
            print(f"发送数据时出错: {e}")
            # Assume the connection has been lost
            if self.client_socket:
                self.client_socket.close()
                self.client_socket = None
            return False

    def is_client_connected(self):
        """Check whether any client is currently connected"""
        return self.client_socket is not None and self.is_running
    
    def stop(self):
        """Stop the client and close the connection."""
        print("正在停止TCP客户端...")
        self.is_running = False
        if self.client_socket:
            try:
                self.client_socket.shutdown(socket.SHUT_RDWR)
                self.client_socket.close()
            except OSError as e:
                print(f"关闭套接字时出错: {e}")
        if self.connection_thread:
            self.connection_thread.join() # Wait for the thread to finish
        self.client_socket = None
        print("TCP客户端已停止。")
