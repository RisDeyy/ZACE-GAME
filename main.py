import os
import sys
import subprocess
import argparse

def start_server():
    print("Starting server...")
    server_process = subprocess.Popen([sys.executable, "server.py"])
    return server_process

def start_client():
    print("Starting client...")
    client_process = subprocess.Popen([sys.executable, "client.py"])
    return client_process

def main():
    parser = argparse.ArgumentParser(description="Zace Game Launcher")
    parser.add_argument('--mode', choices=['server', 'client', 'both'], default='both', 
                        help='Start as server, client, or both')
    parser.add_argument('--clients', type=int, default=1, 
                        help='Number of clients to start (only relevant when mode is both)')
    
    args = parser.parse_args()
    
    processes = []
    
    if args.mode == 'server' or args.mode == 'both':
        server_process = start_server()
        processes.append(server_process)
    
    if args.mode == 'client' or args.mode == 'both':
        for _ in range(args.clients):
            client_process = start_client()
            processes.append(client_process)
    
    try:
        for process in processes:
            process.wait()
    except KeyboardInterrupt:
        print("Shutting down...")
        for process in processes:
            process.terminate()
    
    print("All processes terminated")

if __name__ == "__main__":
    main()

# python main.py --mode server
# python main.py --mode client
# ----------------------------
# python main.py --mode both 