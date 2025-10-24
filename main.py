import pygame
import random

# Initialize Pygame
pygame.init()

# Screen dimensions
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Advanced Car Game")

# Clock for controlling frame rate
clock = pygame.time.Clock()
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (50, 50, 50)
YELLOW = (255, 255, 0)
RED = (255, 0, 0)

# Road dimensions
ROAD_WIDTH = 400
LANE_MARKER_WIDTH = 10
LANE_COUNT = 3
ROAD_LEFT = (SCREEN_WIDTH - ROAD_WIDTH) // 2
LANE_WIDTH = ROAD_WIDTH // LANE_COUNT

# Load car image
car_img = pygame.image.load("car.png")  # Replace with your car image
car_width = 70
car_height = 90

# Car starting position (center lane)
car_x = SCREEN_WIDTH // 2 - car_width // 2
car_y = SCREEN_HEIGHT - car_height - 10
car_speed = 7

# Obstacles
obstacle_width = 40
obstacle_height = 80
obstacle_speed = 5
obstacles = []

# Generate initial obstacles
for _ in range(5):
    lane = random.randint(0, LANE_COUNT - 1)
    x = ROAD_LEFT + lane * LANE_WIDTH + (LANE_WIDTH - obstacle_width)//2
    y = random.randint(-600, -100)
    obstacles.append([x, y])

# Score
score = 0
font = pygame.font.SysFont(None, 35)

# Game loop flag
running = True

# Function to display score
def show_score(score):
    text = font.render(f"Score: {score}", True, BLACK)
    screen.blit(text, (10, 10))

# Draw road
def draw_road():
    # Draw road
    pygame.draw.rect(screen, GRAY, (ROAD_LEFT, 0, ROAD_WIDTH, SCREEN_HEIGHT))
    
    # Draw lane markers
    for i in range(1, LANE_COUNT):
        pygame.draw.rect(screen, YELLOW, (
            ROAD_LEFT + i*LANE_WIDTH - LANE_MARKER_WIDTH//2, 0,
            LANE_MARKER_WIDTH, SCREEN_HEIGHT
        ))

# Game loop
while running:
    screen.fill(WHITE)
    draw_road()
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    
    # Key presses
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT] and car_x > ROAD_LEFT:
        car_x -= car_speed
    if keys[pygame.K_RIGHT] and car_x < ROAD_LEFT + ROAD_WIDTH - car_width:
        car_x += car_speed

    # Move obstacles
    for obs in obstacles:
        obs[1] += obstacle_speed
        if obs[1] > SCREEN_HEIGHT:
            obs[1] = random.randint(-600, -100)
            lane = random.randint(0, LANE_COUNT - 1)
            obs[0] = ROAD_LEFT + lane * LANE_WIDTH + (LANE_WIDTH - obstacle_width)//2
            score += 1

        pygame.draw.rect(screen, RED, (obs[0], obs[1], obstacle_width, obstacle_height))

        # Collision detection
        if car_y < obs[1] + obstacle_height and car_y + car_height > obs[1]:
            if car_x < obs[0] + obstacle_width and car_x + car_width > obs[0]:
                print("Collision! Game Over!")
                running = False

    # Draw car
    screen.blit(pygame.transform.scale(car_img, (car_width, car_height)), (car_x, car_y))

    # Show score
    show_score(score)

    pygame.display.update()
    clock.tick(FPS)

pygame.quit()
