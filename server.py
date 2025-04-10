import socket
import threading
import random
import json
import time

class GameServer:
    def __init__(self, host='127.0.0.1', port=5555):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        
        self.clients = {}
        self.players = {}
        self.bullets = []
        self.maze = self.generate_maze(32, 16)
        self.lock = threading.Lock()
        self.status_messages = []
        
        print(f"Server started on {self.host}:{self.port}")
    
    def generate_maze(self, width, height):
        if width % 2 == 0:
            width += 1
        if height % 2 == 0:
            height += 1
        
        maze = [[1 for _ in range(width)] for _ in range(height)]
        
        directions = [(0, -2), (2, 0), (0, 2), (-2, 0)]
        
        start_x = random.randrange(1, width, 2)
        start_y = random.randrange(1, height, 2)
        maze[start_y][start_x] = 0
        
        stack = [(start_x, start_y)]
        visited = set([(start_x, start_y)])
        
        while stack:
            x, y = stack[-1]
            random.shuffle(directions)
            moved = False
            for dx, dy in directions:
                nx, ny = x + dx, y + dy
                if (0 < nx < width-1 and 0 < ny < height-1 and 
                    (nx, ny) not in visited):
                    maze[y + dy//2][x + dx//2] = 0 
                    maze[ny][nx] = 0
                    stack.append((nx, ny))
                    visited.add((nx, ny))
                    moved = True
                    break
            if not moved:
                stack.pop()
        
        for _ in range(width * height // 20):
            x = random.randrange(1, width-1, 2)
            y = random.randrange(1, height-1, 2)
            dx, dy = random.choice([(0, 1), (1, 0), (0, -1), (-1, 0)])
            nx, ny = x + dx, y + dy
            if 0 < nx < width-1 and 0 < ny < height-1 and maze[ny][nx] == 1:
                maze[ny][nx] = 0
        
        for _ in range(4):
            side = random.randint(0, 3)
            if side == 0:
                x = random.randrange(1, width-1, 2)
                y = 0
                maze[y+1][x] = 0
            elif side == 1:
                x = width - 1
                y = random.randrange(1, height-1, 2)
                maze[y][x-1] = 0
            elif side == 2:
                x = random.randrange(1, width-1, 2)
                y = height - 1
                maze[y-1][x] = 0
            elif side == 3:
                x = 0
                y = random.randrange(1, height-1, 2)
                maze[y][x+1] = 0
        
        return maze
    
    def get_random_empty_position(self):
        while True:
            x = random.randint(1, len(self.maze[0]) - 2)
            y = random.randint(1, len(self.maze) - 2)
            if self.maze[y][x] == 0 and not any(p['x'] == x and p['y'] == y for p in self.players.values()):
                return x, y

    def handle_client(self, client_socket, client_id):
        try:
            # Nhận tên người chơi từ client
            name_data = client_socket.recv(1024).decode()
            player_name = name_data.strip()
            
            # Nếu không có tên hoặc tên không hợp lệ, đặt tên mặc định
            if not player_name or player_name.startswith("{"):
                player_name = f"Player{client_id}"
            
            print(f"Client {client_id} connected as '{player_name}'")
            
            x, y = self.get_random_empty_position()
            with self.lock:
                self.clients[client_id] = client_socket
                self.players[client_id] = {
                    'x': x,
                    'y': y,
                    'direction': random.choice(['up', 'down', 'left', 'right']),
                    'score': 0,
                    'name': player_name
                }
                self.status_messages.append(f"{player_name} started!")
            
            initial_state = {
                'type': 'init',
                'id': client_id,
                'maze': self.maze,
                'players': self.players,
                'bullets': self.bullets
            }
            client_socket.send(json.dumps(initial_state).encode())
            
            while True:
                try:
                    data = client_socket.recv(1024).decode()
                    if not data:
                        break
                    
                    message = json.loads(data)
                    self.process_client_message(client_id, message)
                    self.broadcast_game_state()
                except json.JSONDecodeError:
                    print(f"Invalid JSON from client {client_id}")
                    continue
                
        except Exception as e:
            print(f"Error processing client {client_id}: {e}")
        finally:
            with self.lock:
                if client_id in self.clients:
                    del self.clients[client_id]
                if client_id in self.players:
                    del self.players[client_id]
            client_socket.close()
            print(f"Client {client_id} disconnected")
            self.broadcast_game_state()
    
    def process_client_message(self, client_id, message):
        with self.lock:
            if message['type'] == 'move':
                direction = message['direction']
                player = self.players[client_id]
                new_x, new_y = player['x'], player['y']
                if direction == 'up':
                    player['direction'] = 'up'
                    new_y -= 1
                elif direction == 'down':
                    player['direction'] = 'down'
                    new_y += 1
                elif direction == 'left':
                    player['direction'] = 'left'
                    new_x -= 1
                elif direction == 'right':
                    player['direction'] = 'right'
                    new_x += 1
                
                if (0 <= new_y < len(self.maze) and 
                    0 <= new_x < len(self.maze[0]) and 
                    self.maze[new_y][new_x] == 0 and 
                    not any(p['x'] == new_x and p['y'] == new_y for p in self.players.values())):
                    player['x'] = new_x
                    player['y'] = new_y
            
            elif message['type'] == 'shoot':
                player = self.players[client_id]
                bullet = {
                    'x': player['x'],
                    'y': player['y'],
                    'direction': player['direction'],
                    'owner': client_id,
                    'distance': 0
                }
                can_shoot = True
                for b in self.bullets:
                    if b['owner'] == client_id and b['distance'] < 4:
                        can_shoot = False
                        break
                if can_shoot:
                    self.bullets.append(bullet)
                    player['score'] -= 1
    
    def update_game_state(self):
        with self.lock:
            new_bullets = []
            for bullet in self.bullets:
                if bullet['direction'] == 'up':
                    bullet['y'] -= 1
                elif bullet['direction'] == 'down':
                    bullet['y'] += 1
                elif bullet['direction'] == 'left':
                    bullet['x'] -= 1
                elif bullet['direction'] == 'right':
                    bullet['x'] += 1
                
                bullet['distance'] += 1
                
                if (bullet['y'] < 0 or bullet['y'] >= len(self.maze) or
                    bullet['x'] < 0 or bullet['x'] >= len(self.maze[0]) or
                    self.maze[bullet['y']][bullet['x']] == 1):
                    continue
                
                hit_player = None
                for player_id, player in self.players.items():
                    if player_id != bullet['owner'] and player['x'] == bullet['x'] and player['y'] == bullet['y']:
                        hit_player = player_id
                        break
                
                if hit_player:
                    self.players[bullet['owner']]['score'] += 11
                    self.players[hit_player]['score'] -= 5
                    
                    x, y = self.get_random_empty_position()
                    self.players[hit_player]['x'] = x
                    self.players[hit_player]['y'] = y
                    self.players[hit_player]['direction'] = random.choice(['up', 'down', 'left', 'right'])
                    
                    shooter_name = self.players[bullet['owner']]['name']
                    hit_player_name = self.players[hit_player]['name']
                    self.status_messages.append(f"{shooter_name} just vaporized {hit_player_name}")
                    
                    while True:
                        direction = self.players[hit_player]['direction']
                        check_x, check_y = x, y
                        if direction == 'up':
                            check_y -= 1
                        elif direction == 'down':
                            check_y += 1
                        elif direction == 'left':
                            check_x -= 1
                        elif direction == 'right':
                            check_x += 1
                        if (0 <= check_y < len(self.maze) and 
                            0 <= check_x < len(self.maze[0]) and 
                            self.maze[check_y][check_x] == 0):
                            break
                        self.players[hit_player]['direction'] = random.choice(['up', 'down', 'left', 'right'])
                else:
                    new_bullets.append(bullet)
            
            self.bullets = new_bullets
    
    def broadcast_game_state(self):
        with self.lock:
            game_state = {
                'type': 'update',
                'players': self.players,
                'bullets': self.bullets,
                'status': self.status_messages
            }
            state_json = json.dumps(game_state)
            for client_socket in self.clients.values():
                try:
                    client_socket.send(state_json.encode())
                except Exception as e:
                    print(f"Error sending to client: {e}")
    
    def game_loop(self):
        while True:
            self.update_game_state()
            self.broadcast_game_state()
            time.sleep(0.25)

    def start(self):
        threading.Thread(target=self.game_loop, daemon=True).start()
        client_id = 0
        while True:
            client_socket, addr = self.server_socket.accept()
            print(f"Client connected from {addr}")
            client_id += 1
            threading.Thread(target=self.handle_client, args=(client_socket, client_id), daemon=True).start()

if __name__ == "__main__":
    server = GameServer()
    server.start()