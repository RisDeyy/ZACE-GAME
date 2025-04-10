import pygame
import socket
import json
import threading
import sys

pygame.init()

CELL_SIZE = 30
WINDOW_WIDTH = 32 * CELL_SIZE
WINDOW_HEIGHT = 16 * CELL_SIZE + 100
FPS = 60

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
GRAY = (128, 128, 128)

class GameClient:
    def __init__(self, host='127.0.0.1', port=5555):
        self.host = host
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.player_id = None
        self.maze = []
        self.players = {}
        self.bullets = []
        self.status_messages = []
        
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Zace Game")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('Arial', 20)
        
        self.lock = threading.Lock()
        
        self.player_name = self.get_player_name()
        
        try:
            self.client_socket.connect((self.host, self.port))
            print(f"Connected to the server at {self.host}:{self.port}")
            # Chỉ gửi tên người chơi
            self.client_socket.send(self.player_name.encode())
        except Exception as e:
            print(f"Unable to connect to the server: {e}")
            sys.exit()
        
        self.running = True
        threading.Thread(target=self.receive_data, daemon=True).start()

    def receive_data(self):
        try:
            while self.running:
                data = self.client_socket.recv(4096).decode()
                if not data:
                    break
                try:
                    message = json.loads(data)
                    self.process_server_message(message)
                except json.JSONDecodeError:
                    print("Invalid JSON received")
                    continue
        except Exception as e:
            print(f"Error receiving data: {e}")
        finally:
            self.running = False
            print("Disconnected from server")
    
    def process_server_message(self, message):
        with self.lock:
            if message['type'] == 'init':
                self.player_id = message['id']
                self.maze = message['maze']
                self.players = message['players']
                self.bullets = message['bullets']
                print(f"Initialized as player {self.player_id}")
            
            elif message['type'] == 'update':
                self.players = message['players']
                self.bullets = message['bullets']
                self.status_messages = message.get('status', [])

    def send_action(self, action_type, **kwargs):
        message = {'type': action_type, **kwargs}
        try:
            self.client_socket.send(json.dumps(message).encode())
        except Exception as e:
            print(f"Error sending action: {e}")

    def draw_maze(self):
        for y in range(len(self.maze)):
            for x in range(len(self.maze[0])):
                rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                if self.maze[y][x] == 1:
                    pygame.draw.rect(self.screen, GRAY, rect)
                    pygame.draw.line(self.screen, (160, 160, 160), rect.topleft, rect.topright, 2)
                    pygame.draw.line(self.screen, (160, 160, 160), rect.topleft, rect.bottomleft, 2)
                    pygame.draw.line(self.screen, (100, 100, 100), rect.bottomleft, rect.bottomright, 2)
                    pygame.draw.line(self.screen, (100, 100, 100), rect.topright, rect.bottomright, 2)
                else:
                    pygame.draw.rect(self.screen, (20, 20, 30), rect)
                    pygame.draw.rect(self.screen, (30, 30, 40), rect, 1)

    def get_player_name(self):
        player_name = ""
        input_active = True
        input_box = pygame.Rect(WINDOW_WIDTH // 4, WINDOW_HEIGHT // 2, WINDOW_WIDTH // 2, 40)
        
        while input_active:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        input_active = False
                    elif event.key == pygame.K_BACKSPACE:
                        player_name = player_name[:-1]
                    else:
                        if len(player_name) < 15:
                            player_name += event.unicode
            
            self.screen.fill(BLACK)
            title_text = self.font.render("Enter your name:", True, WHITE)
            self.screen.blit(title_text, (WINDOW_WIDTH // 2 - title_text.get_width() // 2, WINDOW_HEIGHT // 2 - 60))
            pygame.draw.rect(self.screen, WHITE, input_box, 2)
            input_surface = self.font.render(player_name, True, WHITE)
            self.screen.blit(input_surface, (input_box.x + 5, input_box.y + 5))
            guide_text = self.font.render("Press <Enter> to start", True, GREEN)
            self.screen.blit(guide_text, (WINDOW_WIDTH // 2 - guide_text.get_width() // 2, WINDOW_HEIGHT // 2 + 60))
            pygame.display.flip()
            self.clock.tick(30)
        
        return player_name

    def draw_players(self):
        for player_id, player in self.players.items():
            color = GREEN if str(player_id) == str(self.player_id) else RED
            rect = pygame.Rect(player['x'] * CELL_SIZE, player['y'] * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(self.screen, color, rect)
    
            center_x = player['x'] * CELL_SIZE + CELL_SIZE // 2
            center_y = player['y'] * CELL_SIZE + CELL_SIZE // 2
            indicator_length = CELL_SIZE // 2 - 2
            
            if player['direction'] == 'up':
                pygame.draw.line(self.screen, BLUE, (center_x, center_y), 
                                (center_x, center_y - indicator_length), 3)
            elif player['direction'] == 'down':
                pygame.draw.line(self.screen, BLUE, (center_x, center_y), 
                                (center_x, center_y + indicator_length), 3)
            elif player['direction'] == 'left':
                pygame.draw.line(self.screen, BLUE, (center_x, center_y), 
                                (center_x - indicator_length, center_y), 3)
            elif player['direction'] == 'right':
                pygame.draw.line(self.screen, BLUE, (center_x, center_y), 
                                (center_x + indicator_length, center_y), 3)
            
            name = player.get('name', f"Player {player_id}")
            name_surface = pygame.font.SysFont('Arial', 14).render(name, True, WHITE)
            self.screen.blit(name_surface, 
                        (center_x - name_surface.get_width() // 2, 
                            player['y'] * CELL_SIZE - 18))
    
    def draw_bullets(self):
        for bullet in self.bullets:
            center_x = bullet['x'] * CELL_SIZE + CELL_SIZE // 2
            center_y = bullet['y'] * CELL_SIZE + CELL_SIZE // 2
            pygame.draw.circle(self.screen, YELLOW, (center_x, center_y), CELL_SIZE // 4)
    
    def draw_scoreboard(self):
        scoreboard_y = 16 * CELL_SIZE
        pygame.draw.rect(self.screen, BLACK, (0, scoreboard_y, WINDOW_WIDTH, 100))
        pygame.draw.line(self.screen, WHITE, (0, scoreboard_y), (WINDOW_WIDTH, scoreboard_y), 2)
        
        title = self.font.render("Scoreboard", True, WHITE)
        self.screen.blit(title, (20, scoreboard_y + 10))
        
        y_offset = scoreboard_y + 40
        x_position = 20
        for player_id, player in sorted(self.players.items(), key=lambda x: x[1]['score'], reverse=True):
            name = player.get('name', f"Player {player_id}")
            player_text = f"{name}: {player['score']} score(s)"
            color = GREEN if str(player_id) == str(self.player_id) else WHITE
            player_surface = self.font.render(player_text, True, color)
            self.screen.blit(player_surface, (x_position, y_offset))
            x_position += 220 
            if x_position > WINDOW_WIDTH - 220:
                x_position = 20
                y_offset += 25
        
        status_x = WINDOW_WIDTH - 300
        status_y = scoreboard_y + 10
        status_title = self.font.render("Status", True, WHITE)
        self.screen.blit(status_title, (status_x, status_y))
        
        # Hiển thị tối đa 5 trạng thái, trạng thái mới nhất ở dưới cùng
        visible_status = self.status_messages[-5:] if len(self.status_messages) > 5 else self.status_messages
        for i, msg in enumerate(visible_status):
            # Chỉ hiển thị nếu msg là chuỗi hợp lệ (không phải JSON thô)
            if isinstance(msg, str) and not msg.startswith("{"):
                status_surface = self.font.render(msg, True, YELLOW)
                self.screen.blit(status_surface, (status_x, status_y + 25 + i * 18))

    def run(self):
        last_shoot_time = 0
        
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        self.send_action('move', direction='up')
                    elif event.key == pygame.K_DOWN:
                        self.send_action('move', direction='down')
                    elif event.key == pygame.K_LEFT:
                        self.send_action('move', direction='left')
                    elif event.key == pygame.K_RIGHT:
                        self.send_action('move', direction='right')
                    elif event.key == pygame.K_SPACE:
                        current_time = pygame.time.get_ticks()
                        if current_time - last_shoot_time > 500:
                            self.send_action('shoot')
                            last_shoot_time = current_time
                    elif event.key == pygame.K_q:
                        self.running = False
            
            self.screen.fill(BLACK)
            with self.lock:
                if self.maze:
                    self.draw_maze()
                    self.draw_players()
                    self.draw_bullets()
                    self.draw_scoreboard()
            
            pygame.display.flip()
            self.clock.tick(FPS)
        
        self.client_socket.close()
        pygame.quit()

if __name__ == "__main__":
    client = GameClient()
    client.run()