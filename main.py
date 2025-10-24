import pygame
import random
import os
import sys
from math import copysign

# -------------------- CONFIG --------------------
SCREEN_WIDTH, SCREEN_HEIGHT = 900, 700
FPS = 60

LANE_COUNT = 3
ROAD_WIDTH_RATIO = 0.62   # fraction of screen occupied by road
LANE_MARKER_WIDTH = 6

PLAYER_SCALE = 0.45       # scales the player sprite from its source size
ENEMY_SCALE = 0.42

LANE_SWITCH_TIME = 0.16   # seconds to move one lane (smooth interpolation)
BASE_OBSTACLE_SPEED = 300 # pixels per second (apparent world speed)
SPEED_RAMP = 5            # gradual increase in speed per minute
SPAWN_INTERVAL = 0.9      # average seconds between enemy spawns

ASSET_DIR = "assets"
PLAYER_IMG = os.path.join(ASSET_DIR, "car_player.png")
ENEMY_IMG  = os.path.join(ASSET_DIR, "car_enemy.png")
ROAD_IMG   = os.path.join(ASSET_DIR, "road.png")

# -------------------- INIT --------------------
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Polished Sprite-based Racer")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 36)

# -------------------- LAYOUT & PRECOMPUTE --------------------
ROAD_WIDTH = int(SCREEN_WIDTH * ROAD_WIDTH_RATIO)
ROAD_LEFT = (SCREEN_WIDTH - ROAD_WIDTH) // 2
LANE_WIDTH = ROAD_WIDTH / LANE_COUNT
LANE_CENTERS = [ROAD_LEFT + LANE_WIDTH*(i+0.5) for i in range(LANE_COUNT)]
PLAYER_Y = SCREEN_HEIGHT - 150  # vertical position of player's car bottom area

# -------------------- LOAD ASSETS with fallbacks --------------------
def load_image(path):
    try:
        return pygame.image.load(path).convert_alpha()
    except Exception:
        return None

player_sprite_src = load_image(PLAYER_IMG)
enemy_sprite_src  = load_image(ENEMY_IMG)
road_texture_src  = load_image(ROAD_IMG)

# Safe fallback sizes (if no sprites)
if player_sprite_src:
    p_src_w, p_src_h = player_sprite_src.get_size()
else:
    p_src_w, p_src_h = 140, 280

if enemy_sprite_src:
    e_src_w, e_src_h = enemy_sprite_src.get_size()
else:
    e_src_w, e_src_h = 140, 280

PLAYER_W = int(p_src_w * PLAYER_SCALE)
PLAYER_H = int(p_src_h * PLAYER_SCALE)
ENEMY_W  = int(e_src_w * ENEMY_SCALE)
ENEMY_H  = int(e_src_h * ENEMY_SCALE)

if player_sprite_src:
    player_sprite = pygame.transform.smoothscale(player_sprite_src, (PLAYER_W, PLAYER_H))
else:
    player_sprite = None

if enemy_sprite_src:
    enemy_sprite = pygame.transform.smoothscale(enemy_sprite_src, (ENEMY_W, ENEMY_H))
else:
    enemy_sprite = None

# road texture scaling helper
if road_texture_src:
    # tile the texture to road width
    tex_w = road_texture_src.get_width()
    scale = ROAD_WIDTH / tex_w
    road_texture = pygame.transform.smoothscale(road_texture_src, (ROAD_WIDTH, int(road_texture_src.get_height()*scale)))
else:
    road_texture = None

# -------------------- GAME STATE --------------------
player_lane = LANE_COUNT // 2
player_x = LANE_CENTERS[player_lane]  # current center x
player_target_x = player_x             # where we are moving to
lane_switch_timer = 0.0                # interpolation timer

obstacles = []  # list of dicts: {x, y, w, h, speed, lane}
spawn_timer = 0.0
game_speed = BASE_OBSTACLE_SPEED
score = 0
running = True
paused = False
elapsed_time = 0.0

# Pre-generate some enemy lanes to avoid stacking at start
for _ in range(2):
    lane = random.randint(0, LANE_COUNT-1)
    x = LANE_CENTERS[lane]
    y = -random.randint(120, 800)
    obstacles.append({"lane": lane, "x": x, "y": y, "w": ENEMY_W, "h": ENEMY_H})

# -------------------- UTILITIES --------------------
def lerp(a, b, t):
    return a + (b - a) * t

def spawn_enemy(offscreen_range=(100, 600)):
    lane = random.randint(0, LANE_COUNT-1)
    x = LANE_CENTERS[lane]
    y = -random.randint(*offscreen_range)
    obstacles.append({"lane": lane, "x": x, "y": y, "w": ENEMY_W, "h": ENEMY_H})

def draw_road(surface, offset_y):
    # grass sides
    surface.fill((102, 176, 85))
    # road rectangle base
    road_rect = pygame.Rect(ROAD_LEFT, 0, ROAD_WIDTH, SCREEN_HEIGHT)
    if road_texture:
        # tile texture vertically
        tex_h = road_texture.get_height()
        # compute start so movement appears continuous
        start = int(offset_y) % tex_h
        y = -start
        while y < SCREEN_HEIGHT:
            surface.blit(road_texture, (ROAD_LEFT, y))
            y += tex_h
    else:
        pygame.draw.rect(surface, (45, 45, 45), road_rect)
    # lane markers (dashed)
    dash_h = 28
    gap_h = 20
    for i in range(1, LANE_COUNT):
        x = ROAD_LEFT + i * LANE_WIDTH
        marker_rect_w = LANE_MARKER_WIDTH
        # draw down the road with gaps to simulate motion
        y = -offset_y % (dash_h + gap_h) - (dash_h+gap_h)
        while y < SCREEN_HEIGHT:
            pygame.draw.rect(surface, (240, 220, 90), (x - marker_rect_w//2, int(y), marker_rect_w, dash_h))
            y += dash_h + gap_h

    # side strips
    pygame.draw.line(surface, (230, 230, 230), (ROAD_LEFT,0), (ROAD_LEFT,SCREEN_HEIGHT), 6)
    pygame.draw.line(surface, (230, 230, 230), (ROAD_LEFT+ROAD_WIDTH,0), (ROAD_LEFT+ROAD_WIDTH,SCREEN_HEIGHT), 6)

# -------------------- MAIN GAME LOOP --------------------
while running:
    dt_ms = clock.tick(FPS)
    dt = dt_ms / 1000.0
    if not paused:
        elapsed_time += dt

    # events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE,):
                running = False
            elif event.key in (pygame.K_p,):
                paused = not paused
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                if player_lane > 0:
                    player_lane -= 1
                    player_target_x = LANE_CENTERS[player_lane]
                    lane_switch_timer = 0.0
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                if player_lane < LANE_COUNT - 1:
                    player_lane += 1
                    player_target_x = LANE_CENTERS[player_lane]
                    lane_switch_timer = 0.0

    # update only when not paused
    if not paused:
        # ramp game speed gently with time
        game_speed = BASE_OBSTACLE_SPEED + (SPEED_RAMP * (elapsed_time / 60.0))

        # lane switching interpolation
        if abs(player_x - player_target_x) > 1:
            lane_switch_timer += dt / LANE_SWITCH_TIME
            t = min(1.0, lane_switch_timer)
            # ease out interpolation for snappier feel
            t_ease = 1 - (1 - t)**2
            player_x = lerp(player_x, player_target_x, t_ease)
        else:
            player_x = player_target_x

        # spawn logic (randomized interval)
        spawn_timer += dt
        if spawn_timer >= random.uniform(0.7 * SPAWN_INTERVAL, 1.4 * SPAWN_INTERVAL):
            spawn_timer = 0.0
            spawn_enemy((150, 650))

        # update obstacles
        for obs in obstacles:
            obs["y"] += game_speed * dt
        # remove or recycle off-screen enemies
        new_obs = []
        for obs in obstacles:
            if obs["y"] > SCREEN_HEIGHT + 200:
                # player passed it
                score += 1
                # small chance to keep it spawned for variety (or respawn)
                if random.random() < 0.4:
                    obs["lane"] = random.randint(0, LANE_COUNT-1)
                    obs["x"] = LANE_CENTERS[obs["lane"]]
                    obs["y"] = -random.randint(120, 600)
                    new_obs.append(obs)
                # else drop it
            else:
                new_obs.append(obs)
        obstacles = new_obs

        # collision detection (AABB improved)
        player_rect = pygame.Rect(0,0, PLAYER_W, PLAYER_H)
        player_rect.centerx = int(player_x)
        player_rect.bottom = PLAYER_Y + PLAYER_H//2  # approximate correct bottom place
        collided = False
        for obs in obstacles:
            obs_rect = pygame.Rect(0,0, obs["w"], obs["h"])
            obs_rect.centerx = int(obs["x"])
            obs_rect.y = int(obs["y"])
            # slightly shrink rects so collisions feel fair
            shrink = 8
            if player_rect.inflate(-shrink, -shrink).colliderect(obs_rect.inflate(-shrink, -shrink)):
                collided = True
                break

        if collided:
            # simple game over flow: quick flash + stop
            pygame.time.wait(120)
            # game over screen
            screen.fill((10,10,10))
            go_font = pygame.font.Font(None, 96)
            t1 = go_font.render("GAME OVER", True, (220,40,40))
            t2 = font.render(f"Score: {score}", True, (230,230,230))
            screen.blit(t1, (SCREEN_WIDTH//2 - t1.get_width()//2, SCREEN_HEIGHT//2 - 80))
            screen.blit(t2, (SCREEN_WIDTH//2 - t2.get_width()//2, SCREEN_HEIGHT//2 + 20))
            pygame.display.update()
            pygame.time.wait(1600)
            running = False

    # ----------- DRAW -----------
    # road offset for animated dash movement: use elapsed_time and game_speed to simulate motion
    road_offset = int((elapsed_time * game_speed * 0.5))  # tweak divisor to change dash speed feel
    draw_road(screen, road_offset)

    # draw obstacles sorted front-to-back (bigger y = closer)
    for obs in sorted(obstacles, key=lambda o: o["y"], reverse=False):
        if enemy_sprite:
            # render sprite at obs position (scale slightly with proximity to bottom for parallax)
            sprite = enemy_sprite
            rect = sprite.get_rect(center=(int(obs["x"]), int(obs["y"])))
            # clamp vertical draw so enemies appear on road
            screen.blit(sprite, rect)
        else:
            pygame.draw.rect(screen, (200, 30, 30), (int(obs["x"]-obs["w"]/2), int(obs["y"]), obs["w"], obs["h"]))
            pygame.draw.rect(screen, (255, 120, 120), (int(obs["x"]-obs["w"]/4), int(obs["y"]+obs["h"]/6), obs["w"]/2, obs["h"]/2), 2)

    # draw player centered on player_x and fixed vertical
    if player_sprite:
        p_rect = player_sprite.get_rect(center=(int(player_x), PLAYER_Y))
        screen.blit(player_sprite, p_rect)
    else:
        pr = pygame.Rect(0,0, PLAYER_W, PLAYER_H)
        pr.centerx = int(player_x)
        pr.bottom = PLAYER_Y + PLAYER_H//2
        pygame.draw.rect(screen, (20,120,200), pr)
        pygame.draw.rect(screen, (200,230,255), (pr.x + pr.w*0.18, pr.y + pr.h*0.12, pr.w*0.64, pr.h*0.36))

    # HUD
    score_surf = font.render(f"Score: {score}", True, (20,20,20))
    speed_surf = font.render(f"Speed: {int(game_speed)}", True, (20,20,20))
    pause_surf = font.render("P: Pause", True, (20,20,20))
    screen.blit(score_surf, (12, 12))
    screen.blit(speed_surf, (12, 48))
    screen.blit(pause_surf, (SCREEN_WIDTH-120, 12))

    pygame.display.flip()

pygame.quit()
sys.exit()
