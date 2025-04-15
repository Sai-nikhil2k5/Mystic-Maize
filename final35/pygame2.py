import pygame
import sys
import random
import time
import math
import os
import json
import tkinter as tk
from tkinter import filedialog
from collections import deque
from pygame.locals import *

# Initialize pygame
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

# Constants
WIDTH, HEIGHT = 800, 600  # Default screen size
ROWS, COLS = 21, 21  # Maze grid size
CELL_SIZE = min(WIDTH // COLS, HEIGHT // ROWS)
PLAYER_SPEED = 4
MAZE_OFFSET = 20
BULLET_SPEED = 6

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (50, 255, 100)
TIMER_COLOR = (225, 225, 225)
TEXT_COLOR = (232, 44, 5)
BORDER_COLOR = (20, 168, 249)
BACKGROUND_COLOR = (0, 0, 0)     # Black
HOVER_COLOR = (255, 215, 0)      # Gold
SELECTED_COLOR = (0, 255, 0)     # Green

# Screen setup
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption('MYSTIC MAIZE')

# Game states
MAIN_MENU = 0
GAME = 1
GAME_OVER = 2
GAME_WON = 3
PLAYER_SELECT = 4
DIFFICULTY_SELECT = 5
HELP_SCREEN = 6
ANIMATION = 7
HIGH_SCORES = 8

class Enemy:
    def __init__(self, start_x, start_y, image, grid):
        self.start_x, self.start_y = start_x, start_y
        self.x, self.y = start_x, start_y
        self.pixel_x, self.pixel_y = self.x * CELL_SIZE, self.y * CELL_SIZE + MAZE_OFFSET
        self.target_x, self.target_y = self.pixel_x, self.pixel_y
        self.speed = 1.3
        self.path = []
        self.is_alive = True
        self.is_visible = True
        self.original_image = image
        self.image = pygame.transform.scale(image, (CELL_SIZE - 6, CELL_SIZE - 6))
        self.last_time = time.time()
        self.grid = grid

    def move_towards_player(self, player_x, player_y):
        current_time = time.time()
        dt = current_time - self.last_time
        self.last_time = current_time

        if not self.is_visible:
            return

        target_x = int(player_x // CELL_SIZE)
        target_y = int((player_y - MAZE_OFFSET) // CELL_SIZE)

        if (self.x, self.y) != (target_x, target_y):
            self.path = self.bfs((self.x, self.y), (target_x, target_y))

        if not self.path:
            return

        if abs(self.pixel_x - self.target_x) < self.speed and abs(self.pixel_y - self.target_y) < self.speed:
            if self.path:
                next_x, next_y = self.path.pop(0)
                self.x, self.y = next_x, next_y
                self.target_x = self.x * CELL_SIZE
                self.target_y = self.y * CELL_SIZE + MAZE_OFFSET

        base_speed = 2
        self.speed = (CELL_SIZE / 30) * base_speed

        move_x = self.speed * dt * 60
        move_y = self.speed * dt * 60

        if self.pixel_x < self.target_x:
            self.pixel_x += min(self.speed, self.target_x - self.pixel_x)
        elif self.pixel_x > self.target_x:
            self.pixel_x -= min(self.speed, self.pixel_x - self.target_x)

        if self.pixel_y < self.target_y:
            self.pixel_y += min(self.speed, self.target_y - self.pixel_y)
        elif self.pixel_y > self.target_y:
            self.pixel_y -= min(self.speed, self.pixel_y - self.target_y)

    def bfs(self, start, goal):
        queue = deque([(start, [])])
        visited = set()

        while queue:
            (x, y), path = queue.popleft()

            if (x, y) == goal:
                return path

            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                nx, ny = x + dx, y + dy

                if 0 <= nx < COLS and 0 <= ny < ROWS and self.grid[ny][nx] == 0 and (nx, ny) not in visited:
                    queue.append(((nx, ny), path + [(nx, ny)]))
                    visited.add((nx, ny))

        return []

    def check_collision(self, player_x, player_y):
        if not self.is_visible:
            return False

        distance = math.sqrt((self.pixel_x - player_x) ** 2 + (self.pixel_y - player_y) ** 2)
        COLLISION_THRESHOLD = CELL_SIZE

        if distance < COLLISION_THRESHOLD:
            return True

        return False

    def draw(self, screen):
        if self.is_visible:
            screen.blit(self.image, (self.pixel_x, self.pixel_y))

class Game:
    def __init__(self):
        self.state = ANIMATION
        self.difficulty = None
        self.clock = pygame.time.Clock()
        self.start_time = 0
        self.elapsed_time = 0
        self.music_on = True
        self.collected_keys = 0
        self.goal_reached = False
        self.running = True
        self.selected_player = 0
        self.custom_player_image = None
        self.exit_button = None
        self.music_button = None
        self.high_scores = self.load_high_scores()

        # Load sounds
        self.shoot_sound = pygame.mixer.Sound("bullet2.mp3")
        self.enemy_killed_sound = pygame.mixer.Sound("enemy2.mp3")
        self.shoot_sound.set_volume(0.4)
        self.enemy_killed_sound.set_volume(0.7)

        # Load fonts
        try:
            self.font_large = pygame.font.Font('hulk.ttf', 104)
            self.font_medium = pygame.font.Font('hulk.ttf', 48)
            self.font_small = pygame.font.Font('hulk.ttf', 36)
            self.title_font = pygame.font.Font('hulk.ttf', 104)
        except:
            self.font_large = pygame.font.Font(None, 104)
            self.font_medium = pygame.font.Font(None, 48)
            self.font_small = pygame.font.Font(None, 36)
            self.title_font = pygame.font.Font(None, 104)

        # Load and play intro music
        pygame.mixer.music.load("bgm4.mp3")
        pygame.mixer.music.play(-1)  # Loop forever

        # Create default player images if missing
        for i in range(1, 7):
            if not os.path.exists(f'player{i}.png'):
                img = pygame.Surface((150, 150))
                img.fill((random.randint(50, 200), random.randint(50, 200), random.randint(50, 200)))
                pygame.draw.circle(img, (255, 255, 255), (75, 75), 50)
                pygame.image.save(img, f'player{i}.png')

        # Main menu setup
        self.main_menu_options = ["PLAY", "SELECT PLAYER", "HELP", "HIGH SCORES", "QUIT"]
        self.difficulty_options = ["MEDIUM", "HARD", "EXTREME"]
        self.option_rects = []
        self.selected_option = None

        # Game variables (will be initialized when starting a game)
        self.player_x = 0
        self.player_y = 0
        self.goal_x = 0
        self.goal_y = 0
        self.grid = []
        self.bullets = []
        self.enemies = []
        self.keys = []
        self.controls = {}
        self.player_image = None
        self.key_image = None
        self.bg = None
        self.enemy_image = None

        # Initialize buttons
        self.update_buttons()

    # --------------------- New Methods Below (not inside __init__) ---------------------

    def show_credits(self):
        WIDTH, HEIGHT = 800, 600
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Cinematic End Credits")

        BLACK = (0, 0, 0)
        WHITE = (255, 255, 255)
        GOLD = (255, 215, 0)

        # Fonts
        try:
            title_font = pygame.font.Font('kuku.ttf', 60)
            name_font = pygame.font.Font('la.ttf', 40)
            role_font = pygame.font.Font('pu.ttf', 30)
            extra_font = pygame.font.Font('mi.ttf', 60)
        except:
            title_font = pygame.font.SysFont(None, 60)
            name_font = pygame.font.SysFont(None, 40)
            role_font = pygame.font.SysFont(None, 30)
            extra_font = pygame.font.SysFont(None, 60)

        credits = [
            ("A Game By", None), ("Team i2D", None),
            ("Developers", None),
            ("KALEEM KHAN", ""), ("SAI NIKHIL", ""),
            ("Programers", None), ("Kaleem Khan", ""), ("Vinay", ""), ("Ajith", ""), ("Aditya", ""), ("Rahul", ""), ("Sai Nikhil", ""),
            ("UI & UX", None), ("kaleem khan", ""),
            ("Website", None), ("vinay", ""), ("rahul", ""),
            ("Music", None), ("Sai Nikhil", ""),
            ("", None),
            ("THE END", None),
        ]

        credit_items = []
        for text, role in credits:
            if text == "THE END":
                color = GOLD
                font = title_font
            elif text == "Team i2D":
                font = extra_font
                color = WHITE
            elif role is None:
                font = title_font if text in ["Developers", "Programers", "Music", "A Game By", "UI & UX", "Website"] else name_font
                color = WHITE
            else:
                font = role_font
                color = WHITE

            text_surface = font.render(text, True, color)
            text_rect = text_surface.get_rect(centerx=WIDTH // 2)

            if role:
                role_surface = role_font.render(role, True, (200, 200, 200))
                role_rect = role_surface.get_rect(centerx=WIDTH // 2)
                credit_items.append((text_surface, text_rect, role_surface, role_rect))
            else:
                credit_items.append((text_surface, text_rect, None, None))

        scroll_speed = 2
        y_position = HEIGHT
        spacing = 60
        total_height = len(credits) * spacing + HEIGHT

        stars = [(random.randint(0, WIDTH), random.randint(0, total_height), random.randint(1, 3)) for _ in range(100)]

        try:
            pygame.mixer.music.stop()  # Stop any ongoing music
            pygame.mixer.music.load("bgm4.mp3")
            pygame.mixer.music.set_volume(0.5)
            pygame.mixer.music.play(-1)
        except:
            print("No credit music found or failed to load.")

        clock = pygame.time.Clock()
        running = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    running = False

            y_position -= scroll_speed
            if y_position < -total_height:
                running = False  # End credits after full scroll

            screen.fill(BLACK)

            for x, y, size in stars:
                adjusted_y = (y + y_position) % total_height
                pygame.draw.circle(screen, WHITE, (x, adjusted_y), size)

            current_y = y_position
            for item in credit_items:
                text_surface, text_rect, role_surface, role_rect = item
                if current_y < -spacing or current_y > HEIGHT:
                    current_y += spacing
                    continue
                text_rect.centery = current_y
                screen.blit(text_surface, text_rect)
                if role_surface:
                    role_rect.centery = current_y + 30
                    screen.blit(role_surface, role_rect)
                current_y += spacing

            pygame.display.flip()
            clock.tick(60)

        pygame.mixer.music.stop()
        try:
         pygame.mixer.music.load("bgm5.mp3")  # Assuming this is your menu music
         pygame.mixer.music.play(-1)
        except:
         print("Could not load menu music")

    def end_game(self):
        pygame.time.delay(500)
        self.show_credits() 
        self.state=MAIN_MENU

    # -------------------------------------------------------------------------------------

    def load_high_scores(self):
        try:
            with open('high_scores.json', 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "MEDIUM": {"time": float('inf'), "date": ""},
                "HARD": {"time": float('inf'), "date": ""},
                "EXTREME": {"time": float('inf'), "date": ""}
            }

    def save_high_scores(self):
        with open('high_scores.json', 'w') as f:
            json.dump(self.high_scores, f)

    def update_high_score(self, difficulty, time_seconds):
        current_date = time.strftime("%Y-%m-%d %H:%M:%S")
        if time_seconds < self.high_scores[difficulty]["time"]:
            self.high_scores[difficulty] = {
                "time": time_seconds,
                "date": current_date
            }
            self.save_high_scores()
            return True
        return False

    def toggle_music(self):
        self.music_on = not self.music_on
        if self.music_on:
            pygame.mixer.music.unpause()
        else:
            pygame.mixer.music.pause()

    def handle_main_menu_click(self, selected_option):
        if selected_option == "PLAY":
            self.go_to_play()
        elif selected_option == "QUIT":
            self.running = False

    def run_animation(self):
        letters1 = ['M', 'Y', 'S', 'T', 'I', 'C']
        letters2 = ['M', 'A', 'I', 'Z', 'E']
        rendered_letters1 = [self.title_font.render(letter, True, TEXT_COLOR) for letter in letters1]
        rendered_letters2 = [self.title_font.render(letter, True, TEXT_COLOR) for letter in letters2]
        rects1 = [letter.get_rect() for letter in rendered_letters1]
        rects2 = [letter.get_rect() for letter in rendered_letters2]
        initial_positions1 = [(0, 200), (0, 0), (300, 0), (500, 0), (800, 0), (800, 200)]
        initial_positions2 = [(0, 300), (0, 600), (317, 600), (800, 600), (800, 300)]
        for i, rect in enumerate(rects1):
            rect.x, rect.y = initial_positions1[i]
        for i, rect in enumerate(rects2):
            rect.x, rect.y = initial_positions2[i]
        speeds1 = [(random.randint(2, 3), random.randint(1, 3)) for _ in rects1]
        speeds2 = [(random.randint(2, 3), random.randint(1, 3)) for _ in rects2]
        targets1 = [(180, 200), (279, 200), (350, 200), (415, 200), (492, 200), (527, 200)]
        targets2 = [(220, 300), (325, 305), (411, 300), (445, 300), (511, 305)]
        start_time = time.time()
        while time.time() - start_time < 13:
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == MOUSEBUTTONDOWN:
                    if self.music_button and self.music_button.collidepoint(event.pos):
                        self.toggle_music()
            for i, rect in enumerate(rects1):
                if rect.x < targets1[i][0]:
                    rect.x += speeds1[i][0]
                if rect.x > targets1[i][0]:
                    rect.x -= speeds1[i][0]
                if rect.y < targets1[i][1]:
                    rect.y += speeds1[i][1]
                if rect.y > targets1[i][1]:
                    rect.y -= speeds1[i][1]
                if abs(rect.x - targets1[i][0]) < speeds1[i][0]:
                    rect.x = targets1[i][0]
                if abs(rect.y - targets1[i][1]) < speeds1[i][1]:
                    rect.y = targets1[i][1]
            for i, rect in enumerate(rects2):
                if rect.x < targets2[i][0]:
                    rect.x += speeds2[i][0]
                if rect.x > targets2[i][0]:
                    rect.x -= speeds2[i][0]
                if rect.y < targets2[i][1]:
                    rect.y += speeds2[i][1]
                if rect.y > targets2[i][1]:
                    rect.y -= speeds2[i][1]
                if abs(rect.x - targets2[i][0]) < speeds2[i][0]:
                    rect.x = targets2[i][0]
                if abs(rect.y - targets2[i][1]) < speeds2[i][1]:
                    rect.y = targets2[i][1]
            screen.fill((250, 250, 250))
            flicker_effect = random.randint(-30, 30)
            brightness = max(0, min(225, 225 + flicker_effect))
            overlay = pygame.Surface((800, 600))
            overlay.set_alpha(brightness)
            overlay.fill((0, 0, 0))
            screen.blit(overlay, (0, 0))
            for _ in range(800):
                x, y = random.randint(0, 799), random.randint(0, 599)
                c = random.randint(0, 255)
                screen.set_at((x, y), (c, c, c))
            border_width = 3
            for offset_x in range(-border_width, border_width + 1):
                for offset_y in range(-border_width, border_width + 1):
                    if offset_x == 0 and offset_y == 0:
                        continue
                    if random.random() < 0.1:
                        border_color = WHITE
                    else:
                        border_color = BORDER_COLOR
                    for i, letter in enumerate(letters1):
                        border_letter = self.title_font.render(letter, True, border_color)
                        screen.blit(border_letter, (rects1[i].x + offset_x, rects1[i].y + offset_y))
                    for i, letter in enumerate(letters2):
                        border_letter = self.title_font.render(letter, True, border_color)
                        screen.blit(border_letter, (rects2[i].x + offset_x, rects2[i].y + offset_y))
            for i, (rect, letter) in enumerate(zip(rects1, letters1)):
                color = WHITE if random.random() < 0.1 else TEXT_COLOR
                text_surface = self.title_font.render(letter, True, color)
                screen.blit(text_surface, rect)
            for i, (rect, letter) in enumerate(zip(rects2, letters2)):
                color = WHITE if random.random() < 0.1 else TEXT_COLOR
                text_surface = self.title_font.render(letter, True, color)
                screen.blit(text_surface, rect)
            self.update_buttons()
            self.draw_music_button()
            pygame.display.flip()
            self.clock.tick(30)

    def draw_main_menu(self):
        screen.fill(BACKGROUND_COLOR)
        title = self.font_medium.render("MYSTIC MAIZE", True, TEXT_COLOR)
        screen.blit(title, (400 - title.get_width()//2, 50))
        for i, option in enumerate(self.main_menu_options):
            rect = pygame.Rect(200, 120 + i*80, 400, 50)
            color = HOVER_COLOR if rect.collidepoint(pygame.mouse.get_pos()) else (60, 60, 60)
            pygame.draw.rect(screen, BORDER_COLOR, rect, 5, border_radius=20)
            pygame.draw.rect(screen, color, rect.inflate(-10, -10), border_radius=20)
            text = self.font_medium.render(option, True, TEXT_COLOR)
            screen.blit(text, (400 - text.get_width()//2, 145 + i*80 - text.get_height()//2))
        self.update_buttons()
        self.draw_music_button()
        pygame.display.flip()

    def handle_main_menu_events(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            if self.music_button.collidepoint(mouse_pos):
                self.toggle_music()
                return
            for i, option in enumerate(self.main_menu_options):
                rect = pygame.Rect(200, 120 + i*80, 400, 50)
                if rect.collidepoint(mouse_pos):
                    if option == "PLAY":
                        self.state = DIFFICULTY_SELECT
                    elif option == "SELECT PLAYER":
                        self.state = PLAYER_SELECT
                    elif option == "HELP":
                        self.state = HELP_SCREEN
                    elif option == "HIGH SCORES":
                        self.state = HIGH_SCORES
                    elif option == "QUIT":
                        self.running = False

    def draw_difficulty_menu(self):
        screen.fill(BACKGROUND_COLOR)
        title = self.font_medium.render("SELECT DIFFICULTY", True, TEXT_COLOR)
        screen.blit(title, (400 - title.get_width()//2, 100))
        for i, diff in enumerate(self.difficulty_options):
            rect = pygame.Rect(225, 200 + i*100, 350, 60)
            color = HOVER_COLOR if rect.collidepoint(pygame.mouse.get_pos()) else (60, 60, 60)
            pygame.draw.rect(screen, BORDER_COLOR, rect, 5, border_radius=20)
            pygame.draw.rect(screen, color, rect.inflate(-10, -10), border_radius=20)
            text = self.font_medium.render(diff, True, TEXT_COLOR)
            screen.blit(text, (400 - text.get_width()//2, 230 + i*100 - text.get_height()//2))
        back_btn = pygame.Rect(50, 500, 200, 60)
        color = HOVER_COLOR if back_btn.collidepoint(pygame.mouse.get_pos()) else (60, 60, 60)
        pygame.draw.rect(screen, BORDER_COLOR, back_btn, 5, border_radius=20)
        pygame.draw.rect(screen, color, back_btn.inflate(-10, -10), border_radius=20)
        text = self.font_medium.render("BACK", True, TEXT_COLOR)
        screen.blit(text, (150 - text.get_width()//2, 530 - text.get_height()//2))
        self.update_buttons()
        self.draw_music_button()
        pygame.display.flip()

    def handle_difficulty_menu_events(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            if self.music_button.collidepoint(mouse_pos):
                self.toggle_music()
                return
            back_btn = pygame.Rect(50, 500, 200, 60)
            if back_btn.collidepoint(mouse_pos):
                self.state = MAIN_MENU
                return
            for i, diff in enumerate(self.difficulty_options):
                rect = pygame.Rect(225, 200 + i*100, 350, 60)
                if rect.collidepoint(mouse_pos):
                    self.start_game(diff)

    def draw_player_selection(self):
        screen.fill(BACKGROUND_COLOR)
        title = self.font_medium.render("SELECT PLAYER", True, TEXT_COLOR)
        screen.blit(title, (400 - title.get_width()//2, 50))
        for i in range(6):
            x = 150 + (i % 3) * 200
            y = 150 + (i // 3) * 200
            rect = pygame.Rect(x, y, 150, 150)
            if i == self.selected_player:
                pygame.draw.rect(screen, SELECTED_COLOR, rect, 5)
            try:
                img = pygame.image.load(f'player{i+1}.png')
                img = pygame.transform.scale(img, (140, 140))
                screen.blit(img, (x+5, y+5))
            except:
                pygame.draw.rect(screen, (255, 0, 0), rect)
                txt = self.font_small.render(f"Player {i+1}", True, TEXT_COLOR)
                screen.blit(txt, (x + 75 - txt.get_width()//2, y + 75 - txt.get_height()//2))
        if self.selected_player == 6 and self.custom_player_image:
            x, y = 150 + (6 % 3) * 200, 150 + (6 // 3) * 200
            rect = pygame.Rect(x, y, 150, 150)
            pygame.draw.rect(screen, SELECTED_COLOR, rect, 5)
            img = pygame.transform.scale(self.custom_player_image, (140, 140))
            screen.blit(img, (x+5, y+5))
        back_btn = pygame.Rect(50, 500, 350, 80)
        gallery_btn = pygame.Rect(400, 500, 350, 80)
        pygame.draw.rect(screen, BORDER_COLOR, back_btn, 5, border_radius=15)
        pygame.draw.rect(screen, BORDER_COLOR, gallery_btn, 5, border_radius=15)
        pygame.draw.rect(screen, (0, 0, 0), back_btn.inflate(-10, -10), border_radius=15)
        pygame.draw.rect(screen, (0, 0, 0), gallery_btn.inflate(-10, -10), border_radius=15)
        if back_btn.collidepoint(pygame.mouse.get_pos()):
            pygame.draw.rect(screen, HOVER_COLOR, back_btn.inflate(-10, -10), border_radius=15)
        if gallery_btn.collidepoint(pygame.mouse.get_pos()):
            pygame.draw.rect(screen, HOVER_COLOR, gallery_btn.inflate(-10, -10), border_radius=15)
        back_txt = self.font_medium.render("BACK", True, TEXT_COLOR)
        gallery_txt = self.font_medium.render("GALLERY", True, TEXT_COLOR)
        screen.blit(back_txt, (back_btn.x + 175 - back_txt.get_width()//2, back_btn.y + 40 - back_txt.get_height()//2))
        screen.blit(gallery_txt, (gallery_btn.x + 175 - gallery_txt.get_width()//2, gallery_btn.y + 40 - gallery_txt.get_height()//2))
        self.update_buttons()
        self.draw_music_button()
        pygame.display.flip()

    def handle_player_selection_events(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            if self.music_button.collidepoint(mouse_pos):
                self.toggle_music()
                return
            for i in range(6):
                x = 150 + (i % 3) * 200
                y = 150 + (i // 3) * 200
                rect = pygame.Rect(x, y, 150, 150)
                if rect.collidepoint(mouse_pos):
                    self.selected_player = i
                    self.custom_player_image = None
            back_btn = pygame.Rect(50, 500, 350, 80)
            gallery_btn = pygame.Rect(400, 500, 350, 80)
            if back_btn.collidepoint(mouse_pos):
                self.state = MAIN_MENU
            if gallery_btn.collidepoint(mouse_pos):
                root = tk.Tk()
                root.withdraw()
                file_path = filedialog.askopenfilename(
                    title="Select Player Image",
                    filetypes=[("Image files", ".png;.jpg;*.jpeg")]
                )
                if file_path:
                    try:
                        self.custom_player_image = pygame.image.load(file_path)
                        self.selected_player = 6
                    except:
                        print("Error loading image")

    def draw_help_screen(self):
        screen.fill(BACKGROUND_COLOR)
        title = self.font_medium.render("HELP", True, TEXT_COLOR)
        text1 = self.font_small.render("Use arrow keys to move", True, TEXT_COLOR)
        text2 = self.font_small.render("Collect all items to win", True, TEXT_COLOR)
        back = self.font_small.render("Click anywhere to return", True, TEXT_COLOR)
        screen.blit(title, (400 - title.get_width()//2, 100))
        screen.blit(text1, (400 - text1.get_width()//2, 200))
        screen.blit(text2, (400 - text2.get_width()//2, 250))
        screen.blit(back, (400 - back.get_width()//2, 400))
        self.update_buttons()
        self.draw_music_button()
        pygame.display.flip()

    def handle_help_screen_events(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            if self.music_button.collidepoint(mouse_pos):
                self.toggle_music()
                return
            self.state = MAIN_MENU

    def draw_high_scores(self):
        screen.fill(BACKGROUND_COLOR)
        title = self.font_medium.render("HIGH SCORES", True, TEXT_COLOR)
        screen.blit(title, (400 - title.get_width()//2, 50))
        y_offset = 150
        for difficulty in self.difficulty_options:
            score = self.high_scores[difficulty]
            diff_text = self.font_small.render(f"{difficulty}:", True, TEXT_COLOR)
            screen.blit(diff_text, (250, y_offset))
            if score["time"] != float('inf'):
                time_text = self.font_small.render(f"Time: {score['time']:.2f} sec", True, WHITE)
                date_text = self.font_small.render(f"Date: {score['date']}", True, WHITE)
                screen.blit(time_text, (450, y_offset))
                screen.blit(date_text, (450, y_offset + 40))
            else:
                no_score = self.font_small.render("No record yet", True, WHITE)
                screen.blit(no_score, (450, y_offset))
            y_offset += 100
        back_btn = pygame.Rect(300, 500, 200, 60)
        color = HOVER_COLOR if back_btn.collidepoint(pygame.mouse.get_pos()) else (60, 60, 60)
        pygame.draw.rect(screen, BORDER_COLOR, back_btn, 5, border_radius=20)
        pygame.draw.rect(screen, color, back_btn.inflate(-10, -10), border_radius=20)
        text = self.font_medium.render("BACK", True, TEXT_COLOR)
        screen.blit(text, (400 - text.get_width()//2, 530 - text.get_height()//2))
        self.update_buttons()
        self.draw_music_button()
        pygame.display.flip()

    def handle_high_scores_events(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            if self.music_button.collidepoint(mouse_pos):
                self.toggle_music()
                return
            back_btn = pygame.Rect(300, 500, 200, 60)
            if back_btn.collidepoint(mouse_pos):
                self.state = MAIN_MENU

    def start_game(self, difficulty):
        self.difficulty = difficulty
        self.state = GAME
        self.goal_reached = False
        self.collected_keys = 0
        self.bullets = []
        if difficulty == "MEDIUM":
            self.init_level(1)
        elif difficulty == "HARD":
            self.init_level(2)
        else:
            self.init_level(3)
        self.start_time = time.time()
        pygame.mixer.music.stop()
        pygame.mixer.music.load("bgm.mp3")
        pygame.mixer.music.play(-1)

    def init_level(self, level):
        self.grid = [[1 if (row < 2 or row >= ROWS - 2 or col < 2 or col >= COLS - 2) else 1
                      for col in range(COLS)] for row in range(ROWS)]
        DIRECTIONS = [(2, 0), (-2, 0), (0, 2), (0, -2)]
        self.carve_maze(3, 3, DIRECTIONS)
        self.start_pos = (3, 3)
        self.end_pos = (COLS - 5, ROWS - 5)
        self.grid[self.end_pos[1]][self.end_pos[0]] = 0
        self.player_x, self.player_y = self.start_pos[0] * CELL_SIZE, self.start_pos[1] * CELL_SIZE + MAZE_OFFSET
        self.goal_x, self.goal_y = self.end_pos[0] * CELL_SIZE, self.end_pos[1] * CELL_SIZE + MAZE_OFFSET
        try:
            self.bg = pygame.image.load("back.png").convert()
            self.bg = pygame.transform.scale(self.bg, (WIDTH, HEIGHT))
            if self.selected_player == 6 and self.custom_player_image:
                self.player_image = self.custom_player_image
            else:
                self.player_image = pygame.image.load(f"player{self.selected_player+1}.png").convert_alpha()
            self.player_image = pygame.transform.scale(self.player_image, (CELL_SIZE - 6, CELL_SIZE - 6))
            if level == 3:
                self.key_image = pygame.image.load("key.png").convert_alpha()
                self.key_image = pygame.transform.scale(self.key_image, (CELL_SIZE - 10, CELL_SIZE - 10))
            self.enemy_image = pygame.image.load("enemy.png").convert_alpha()
            self.enemy_image = pygame.transform.scale(self.enemy_image, (CELL_SIZE - 6, CELL_SIZE - 6))
        except:
            self.bg = pygame.Surface((WIDTH, HEIGHT))
            self.bg.fill((100, 100, 100))
            self.player_image = pygame.Surface((CELL_SIZE - 6, CELL_SIZE - 6))
            self.player_image.fill((0, 0, 255))
            if level == 3:
                self.key_image = pygame.Surface((CELL_SIZE - 10, CELL_SIZE - 10))
                self.key_image.fill((255, 255, 0))
            self.enemy_image = pygame.Surface((CELL_SIZE - 6, CELL_SIZE - 6))
            self.enemy_image.fill((255, 0, 0))
        MOVES = {
            "UP": (0, -1),
            "DOWN": (0, 1),
            "LEFT": (-1, 0),
            "RIGHT": (1, 0)
        }
        keys = [pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT]
        random.shuffle(keys)
        self.controls = {
            keys[0]: MOVES["UP"],
            keys[1]: MOVES["DOWN"],
            keys[2]: MOVES["LEFT"],
            keys[3]: MOVES["RIGHT"]
        }
        self.enemies = []
        if level >= 2:
            e = [
                Enemy(COLS // 2, ROWS // 2, self.enemy_image, self.grid),
                Enemy(COLS - 2, ROWS - 2, self.enemy_image, self.grid),
                Enemy(COLS // 2, ROWS // 4, self.enemy_image, self.grid)
            ]
            random.shuffle(e)
            self.enemies = [e[0], e[1], e[2]]
        self.keys = []
        if level == 3:
            self.keys = self.generate_key_positions(3)

    def carve_maze(self, x, y, DIRECTIONS):
        self.grid[y][x] = 0
        random.shuffle(DIRECTIONS)
        for dx, dy in DIRECTIONS:
            nx, ny = x + dx, y + dy
            if 1 <= nx < COLS - 1 and 1 <= ny < ROWS - 1 and self.grid[ny][nx] == 1:
                self.grid[y + dy // 2][x + dx // 2] = 0
                self.carve_maze(nx, ny, DIRECTIONS)

    def generate_key_positions(self, num_keys):
        key_positions = []
        while len(key_positions) < num_keys:
            x, y = random.randint(1, COLS - 2), random.randint(1, ROWS - 2)
            if self.grid[y][x] == 0 and (x, y) != self.start_pos and (x, y) != self.end_pos and (x, y) not in key_positions:
                key_positions.append((x, y))
        return key_positions

    def run_game(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.VIDEORESIZE:
                self.update_screen_size(event.w, event.h)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if hasattr(self, 'exit_button') and self.exit_button.collidepoint(event.pos):
                    self.state = MAIN_MENU
                elif hasattr(self, 'music_button') and self.music_button.collidepoint(event.pos):
                    self.toggle_music()
        keys_pressed = pygame.key.get_pressed()
        if self.difficulty in ["HARD", "EXTREME"]:
            if keys_pressed[pygame.K_w]: self.shoot("up")
            if keys_pressed[pygame.K_s]: self.shoot("down")
            if keys_pressed[pygame.K_a]: self.shoot("left")
            if keys_pressed[pygame.K_d]: self.shoot("right")
        vel_x, vel_y = 0, 0
        for key, move in self.controls.items():
            if keys_pressed[key]:
                vel_x += move[0] * PLAYER_SPEED
                vel_y += move[1] * PLAYER_SPEED
        new_x, new_y = self.player_x + vel_x, self.player_y + vel_y
        if self.can_move(new_x, self.player_y):
            self.player_x = new_x
        if self.can_move(self.player_x, new_y):
            self.player_y = new_y
        if self.difficulty in ["HARD", "EXTREME"]:
            self.move_bullets()
        for enemy in self.enemies:
            enemy.move_towards_player(self.player_x, self.player_y)
            if enemy.check_collision(self.player_x, self.player_y):
                self.state = GAME_OVER
                self.end_game()  # End game on enemy collision
                return
        if self.difficulty == "EXTREME":
            player_grid_x = int(self.player_x // CELL_SIZE)
            player_grid_y = int((self.player_y - MAZE_OFFSET) // CELL_SIZE)
            for key_pos in self.keys[:]:
                if (player_grid_x, player_grid_y) == key_pos:
                    self.keys.remove(key_pos)
                    self.collected_keys += 1
        player_rect = pygame.Rect(self.player_x + 10, self.player_y + 10, CELL_SIZE - 15, CELL_SIZE - 15)
        goal_rect = pygame.Rect(self.goal_x, self.goal_y, CELL_SIZE, CELL_SIZE)
        if player_rect.colliderect(goal_rect):
            if self.difficulty != "EXTREME" or (self.difficulty == "EXTREME" and self.collected_keys == 3):
                self.goal_reached = True
                self.elapsed_time = time.time() - self.start_time
                is_new_high_score = self.update_high_score(self.difficulty, self.elapsed_time)
                self.state = GAME_WON
                self.end_game()  # End game on reaching goal
        self.draw_game()

    def draw_game(self):
        screen.blit(self.bg, (0, 0))
        for row in range(ROWS):
            for col in range(COLS):
                if self.grid[row][col] == 0:
                    pygame.draw.rect(screen, (200, 200, 200, 50),
                                     (col * CELL_SIZE, row * CELL_SIZE + MAZE_OFFSET, CELL_SIZE, CELL_SIZE))
        radius = CELL_SIZE
        corners = [
            (0, MAZE_OFFSET),
            (COLS * CELL_SIZE - radius, MAZE_OFFSET),
            (0, ROWS * CELL_SIZE - radius + MAZE_OFFSET),
            (COLS * CELL_SIZE - radius, ROWS * CELL_SIZE - radius + MAZE_OFFSET)
        ]
        for x, y in corners:
            pygame.draw.arc(screen, BLACK, (x, y, radius, radius), 0, 1.57, 5)
        if not self.goal_reached:
            pygame.draw.rect(screen, GREEN, (self.goal_x, self.goal_y, CELL_SIZE, CELL_SIZE))
        if self.difficulty == "EXTREME":
            for x, y in self.keys:
                screen.blit(self.key_image, (x * CELL_SIZE, y * CELL_SIZE + MAZE_OFFSET))
        if self.difficulty in ["HARD", "EXTREME"]:
            for bullet in self.bullets:
                pygame.draw.rect(screen, BLACK, (bullet[0], bullet[1], 6, 6))
        for enemy in self.enemies:
            enemy.draw(screen)
        screen.blit(self.player_image, (self.player_x, self.player_y))
        self.update_buttons()
        self.draw_buttons()
        elapsed_time = time.time() - self.start_time
        self.draw_timer(elapsed_time)
        if self.difficulty == "EXTREME":
            key_text = self.font_small.render(f"Keys: {self.collected_keys}/3", True, WHITE)
            screen.blit(key_text, (WIDTH - 150, self.music_button.y + self.music_button.height + 10))
        pygame.display.flip()
        self.clock.tick(60)

    def can_move(self, new_x, new_y):
        player_rect = pygame.Rect(new_x, new_y, CELL_SIZE - 6, CELL_SIZE - 6)
        for row in range(ROWS):
            for col in range(COLS):
                if self.grid[row][col] == 1:
                    wall_rect = pygame.Rect(col * CELL_SIZE, row * CELL_SIZE + MAZE_OFFSET, CELL_SIZE, CELL_SIZE)
                    if player_rect.colliderect(wall_rect):
                        return False
        return True

    def shoot(self, direction):
        self.shoot_sound.play()
        if direction == "up":
            self.bullets.append((self.player_x + CELL_SIZE // 2, self.player_y, 0, -1))
        elif direction == "down":
            self.bullets.append((self.player_x + CELL_SIZE // 2, self.player_y + CELL_SIZE, 0, 1))
        elif direction == "left":
            self.bullets.append((self.player_x, self.player_y + CELL_SIZE // 2, -1, 0))
        elif direction == "right":
            self.bullets.append((self.player_x + CELL_SIZE, self.player_y + CELL_SIZE // 2, 1, 0))

    def move_bullets(self):
        new_bullets = []
        for bx, by, dx, dy in self.bullets:
            new_bx = bx + BULLET_SPEED * dx
            new_by = by + BULLET_SPEED * dy
            grid_x = int(new_bx // CELL_SIZE)
            grid_y = int((new_by - MAZE_OFFSET) // CELL_SIZE)
            if 0 <= grid_x < COLS and 0 <= grid_y < ROWS and self.grid[grid_y][grid_x] == 1:
                continue
            bullet_rect = pygame.Rect(new_bx, new_by, 6, 6)
            hit_enemy = None
            for enemy in self.enemies:
                enemy_rect = pygame.Rect(enemy.pixel_x, enemy.pixel_y, CELL_SIZE - 6, CELL_SIZE - 6)
                if bullet_rect.colliderect(enemy_rect):
                    hit_enemy = enemy
                    break
            if hit_enemy:
                self.enemy_killed_sound.play()
                self.enemies.remove(hit_enemy)
                start_x, start_y = self.get_random_spawn()
                new_enemy = Enemy(start_x, start_y, hit_enemy.image, self.grid)
                self.enemies.append(new_enemy)
            else:
                new_bullets.append((new_bx, new_by, dx, dy))
        self.bullets = new_bullets

    def get_random_spawn(self):
        while True:
            x = random.randint(1, COLS - 2)
            y = random.randint(1, ROWS - 2)
            if self.grid[y][x] == 0:
                return x, y

    def update_screen_size(self, new_width, new_height):
        global WIDTH, HEIGHT, CELL_SIZE
        WIDTH, HEIGHT = new_width, new_height
        CELL_SIZE = min(WIDTH // COLS, HEIGHT // ROWS)
        try:
            self.bg = pygame.transform.scale(pygame.image.load("back.png").convert(), (WIDTH, HEIGHT))
            if self.selected_player == 6 and self.custom_player_image:
                self.player_image = pygame.transform.scale(self.custom_player_image, (CELL_SIZE - 6, CELL_SIZE - 6))
            else:
                self.player_image = pygame.transform.scale(pygame.image.load(f"player{self.selected_player+1}.png").convert_alpha(), (CELL_SIZE - 6, CELL_SIZE - 6))
            if self.difficulty == "EXTREME":
                self.key_image = pygame.transform.scale(pygame.image.load("key.png").convert_alpha(), (CELL_SIZE - 10, CELL_SIZE - 10))
        except:
            pass
        self.player_x, self.player_y = self.start_pos[0] * CELL_SIZE, self.start_pos[1] * CELL_SIZE + MAZE_OFFSET
        self.goal_x, self.goal_y = self.end_pos[0] * CELL_SIZE, self.end_pos[1] * CELL_SIZE + MAZE_OFFSET
        for enemy in self.enemies:
            enemy.pixel_x = enemy.x * CELL_SIZE
            enemy.pixel_y = enemy.y * CELL_SIZE + MAZE_OFFSET
            enemy.target_x = enemy.x * CELL_SIZE
            enemy.target_y = enemy.y * CELL_SIZE + MAZE_OFFSET
            enemy.image = pygame.transform.scale(enemy.original_image, (CELL_SIZE - 6, CELL_SIZE - 6))
        screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)

    def update_buttons(self):
        button_width = max(WIDTH // 15, 40)
        button_height = max(HEIGHT // 20, 25)
        self.exit_button = pygame.Rect(10, 10, button_width, button_height)
        self.music_button = pygame.Rect(WIDTH - button_width - 10, 10, button_width, button_height)

    def draw_buttons(self):
        font = pygame.font.Font(None, min(WIDTH // 10, 14))
        pygame.draw.rect(screen, (0, 200, 0), self.exit_button)
        exit_text = font.render("BACK", True, BLACK)
        screen.blit(exit_text, self.exit_button.move(self.exit_button.width // 8, self.exit_button.height // 4))
        self.draw_music_button()

    def draw_music_button(self):
        font = pygame.font.Font(None, min(WIDTH // 10, 14))
        music_color = (0, 200, 0) if self.music_on else (200, 0, 0)
        pygame.draw.rect(screen, music_color, self.music_button)
        music_text = font.render("MUSIC", True, BLACK)
        screen.blit(music_text, self.music_button.move(self.music_button.width // 8, self.music_button.height // 4))

    def draw_timer(self, elapsed_time):
        elapsed_seconds = int(elapsed_time)
        font = pygame.font.Font(None, 36)
        text = font.render(f"Time: {elapsed_seconds}", True, TIMER_COLOR)
        text_rect = text.get_rect(midtop=(WIDTH // 2, 10))
        screen.blit(text, text_rect)

    def show_game_over(self):
        screen.fill(BLACK)
        font = pygame.font.Font(None, 72)
        text = font.render("GAME OVER", True, (255, 0, 0))
        text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))
        screen.blit(text, text_rect)
        small_font = pygame.font.Font(None, 50)
        exit_text = small_font.render("Click to continue", True, WHITE)
        exit_text_rect = exit_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 50))
        screen.blit(exit_text, exit_text_rect)
        pygame.display.flip()
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    waiting = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    waiting = False
        self.state = MAIN_MENU

    def show_game_won(self):
        screen.fill(BLACK)
        font = pygame.font.Font(None, 72)
        text = font.render(f"Time: {int(self.elapsed_time)} seconds", True, WHITE)
        text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))
        screen.blit(text, text_rect)
        is_new_high_score = self.update_high_score(self.difficulty, self.elapsed_time)
        if is_new_high_score:
            high_score_text = self.font_medium.render("NEW HIGH SCORE!", True, SELECTED_COLOR)
            screen.blit(high_score_text, (400 - high_score_text.get_width()//2, HEIGHT // 2 + 20))
        small_font = pygame.font.Font(None, 50)
        exit_text = small_font.render("CONGRATULATIONS!", True, SELECTED_COLOR)
        exit_text_rect = exit_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 80))
        screen.blit(exit_text, exit_text_rect)
        pygame.display.flip()
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    waiting = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    waiting = False
        self.state = MAIN_MENU

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                if self.state == MAIN_MENU:
                    self.handle_main_menu_events(event)
                elif self.state == DIFFICULTY_SELECT:
                    self.handle_difficulty_menu_events(event)
                elif self.state == PLAYER_SELECT:
                    self.handle_player_selection_events(event)
                elif self.state == HELP_SCREEN:
                    self.handle_help_screen_events(event)
                elif self.state == HIGH_SCORES:
                    self.handle_high_scores_events(event)
                elif self.state == GAME:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        if self.exit_button.collidepoint(event.pos):
                            self.state = MAIN_MENU
                        elif self.music_button.collidepoint(event.pos):
                            self.toggle_music()
                elif self.state == GAME_OVER:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        self.state = MAIN_MENU
                elif self.state == GAME_WON:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        self.state = MAIN_MENU
            if self.state == ANIMATION:
                self.run_animation()
                self.state = MAIN_MENU
            elif self.state == MAIN_MENU:
                self.draw_main_menu()
            elif self.state == DIFFICULTY_SELECT:
                self.draw_difficulty_menu()
            elif self.state == PLAYER_SELECT:
                self.draw_player_selection()
            elif self.state == HELP_SCREEN:
                self.draw_help_screen()
            elif self.state == HIGH_SCORES:
                self.draw_high_scores()
            elif self.state == GAME:
                self.run_game()
            elif self.state == GAME_OVER:
                self.show_game_over()
            elif self.state == GAME_WON:
                self.show_game_won()
            self.clock.tick(60)
        pygame.quit()
        sys.exit()

# Main game loop
if __name__ == "__main__":
    game = Game()
    game.run()
