import pygame
from math import cos, sin, atan2, log, e, pi
from random import random, randint

pygame.init()
print(pygame.get_init())

SCREEN_WIDTH = 397
SCREEN_HEIGHT = 500
GAMESCREEN_HEIGHT = 394
FRAMERATE = 60
SPEED = (60*10)//FRAMERATE
WALL_LIST = ["left", "right", "top", "bottom"]
INVERTED_WALL_LIST = ["right", "left", "bottom", "top"]

window = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Brick Breaker")
window.fill((255, 255, 255))
game_window = window.subsurface((0, 11), (SCREEN_WIDTH, GAMESCREEN_HEIGHT))
pygame.draw.line(window, (0, 0, 0), (0, 406), (SCREEN_WIDTH, 406), width=3)
pygame.draw.line(window, (0, 0, 0), (0, 9), (SCREEN_WIDTH, 9), width=3)
pygame.display.flip()

stdFont = pygame.font.SysFont("SysFont", 15)
counterFont = pygame.font.SysFont("SysFont", 20)

all_sprites = pygame.sprite.Group()
blocks = pygame.sprite.Group()
bullets = pygame.sprite.Group()
bonuses = pygame.sprite.Group()
accumulated_bullets = 1
bullets_active = False
bullets_pos = (SCREEN_WIDTH//2, GAMESCREEN_HEIGHT-8)
num_bullets_left_bottom = 0
subframe = 0
first_hit_floor = False
delay_before_bottom_collision = 0
curr_round = 1
block_ids = []
bullets_to_add = 0

running = True
gameClock = pygame.time.Clock()


def get_color(round_num):
    return round((lambda r: (242-(r-5)/e**((r+15)/30)) if r < 160 else 242)(round_num)),\
           round((lambda r: -2.2*r+174 if r < 35 else 98)(round_num)),\
           round((lambda r: 116 if r < 9 else 85+(75/e**(.1*r)))(round_num))


def first_missing_int(id_list):
    if len(id_list) == 0:
        return 1
    bit = 0
    for ident in id_list:  # bit stores whether a number exists by having a one ORed into it after being shifted over
        # number times
        bit |= 1 << (ident-1)

    num_flag = 1
    if bit ^ (2 ** (len(bin(bit)) - 2) - 1) == 0:
        return max(id_list) + 1
    else:
        while bit != 0:
            if bit & 1 == 0:
                return num_flag

            num_flag += 1
            bit >>= 1


def difficulty_func(round_num):
    difficulty_mod = round_num if round_num <= 100 else 100
    probs = [((1+(difficulty_mod/100))/3)*(log(j+2))-.35 for j in range(1, 5)]
    spawn_num = 2
    spawn_pos_possible = [0, 1, 2, 3, 4, 5]
    spawn_pos_choice = []

    for prob in probs:
        if random() <= prob:
            spawn_num += 1

    for j in range(spawn_num):
        spawn_pos_choice.append(spawn_pos_possible.pop(randint(0, len(spawn_pos_possible)-1)))

    return spawn_pos_choice


def spawn_row(spawn_pattern):
    # spawn extra ball using pop

    bonus_to_add = Bonus((21+(66 * spawn_pattern.pop(len(spawn_pattern)-1)), 41))
    bonuses.add(bonus_to_add)
    all_sprites.add(bonus_to_add)

    for spawn_pos in spawn_pattern:
        block_id = first_missing_int(block_ids)
        block_to_add = Block((1+(spawn_pos*66), 35), curr_round, block_id)
        blocks.add(block_to_add)
        block_ids.append(block_id)
        all_sprites.add(block_to_add)


class Bonus(pygame.sprite.Sprite):
    def __init__(self, location):
        super(Bonus, self).__init__()
        self.image = pygame.Surface((24, 24))
        self.image.fill((255, 255, 255))
        self.image.set_colorkey((255, 255, 255))
        self.rect = self.image.get_rect(topleft=location)
        pygame.draw.circle(self.image, (55, 235, 120), (12, 12), 7, 0)
        pygame.draw.circle(self.image, (55, 235, 120), (12, 12), 12, 3)
        self.mask = pygame.mask.from_surface(self.image)

    def update(self):
        global accumulated_bullets
        self.rect.y += 36
        if self.rect.bottom >= GAMESCREEN_HEIGHT:
            accumulated_bullets += 1
            bonus_bullet = Bullet(bullets_pos)
            bullets.add(bonus_bullet)
            all_sprites.add(bonus_bullet)
            self.kill()


class Block(pygame.sprite.Sprite):
    def __init__(self, location, strength, ident):
        super(Block, self).__init__()
        self.image = pygame.Surface((65, 35))
        self.image.fill((255, 255, 255))
        self.rect = self.image.get_rect(topleft=location)
        self.in_border = self.image.subsurface((1, 1), (63, 33))
        self.strength = strength
        self.mask = pygame.mask.from_surface(self.image)
        self.ident = ident
        self.width_height_diff = self.rect.width-self.rect.height
        self.write_strength()

    def update(self):
        global running
        self.rect.y += 36
        if self.rect.bottom >= GAMESCREEN_HEIGHT:
            running = False

    def collided(self, collided_sprite, collided_location):
        # print(f"location of collision: {collided_location}, self location: {self.rect}")
        # send data to sprite that collided with self
        collided_sprite.collided(self.ident, collided_sprite=self, location_in_sprite=collided_location)

        # handle local consequences of collision
        self.strength -= 1
        self.write_strength()
        if self.strength == 0:
            # print(block_ids, self.ident)
            block_ids.pop(block_ids.index(self.ident))
            self.kill()
        elif self.strength < 0:
            print("Hit twice!")
            self.kill()

    def write_strength(self):
        color = get_color(self.strength/2)
        rendered_font = stdFont.render(str(self.strength), True, (255, 255, 255), color)
        self.in_border.fill(color)
        self.in_border.blit(rendered_font, ((self.rect.width - rendered_font.get_size()[0]) / 2,
                                            (self.rect.height - rendered_font.get_size()[1]) / 2))


class Bullet(pygame.sprite.Sprite):
    def __init__(self, location, ident=None, track=False):
        super(Bullet, self).__init__()
        self.image = pygame.Surface((16, 16))
        self.image.fill((255, 255, 255))
        self.image.set_colorkey((255, 255, 255))
        self.pos = pygame.math.Vector2(location)
        self.prev_pos = pygame.math.Vector2(location)
        self.rect = self.image.get_rect(center=location)
        self.dir = pygame.math.Vector2((1, 1)).normalize()
        self.active = False
        self.last_collided = None
        self.ident = ident
        self.track = track

        pygame.draw.circle(self.image, (65, 165, 195), (8, 8), 8, 0)
        self.mask = pygame.mask.from_surface(self.image)

    def update(self):
        self.prev_pos = self.pos
        if self.active:
            self.pos += self.dir
            self.rect.center = round(self.pos.x), round(self.pos.y)

        if self.rect.left < 0:
            self.collided("leftWall", side="left")
        if self.rect.right > SCREEN_WIDTH:
            self.collided("rightWall", side="right")
        if self.rect.bottom > GAMESCREEN_HEIGHT:
            self.collided("bottomWall", side="bottom")
        if self.rect.top < 0:
            self.collided("topWall", side="top")

    def collided(self, collided_id, collided_sprite=None, location_in_sprite=None, side=None):
        global first_hit_floor
        global bullets_pos

        # if the side of collision is known (currently only known when bullet hits a wall)
        if side is not None:
            # if hit right wall, push back in bounds and negate (reverse) x direction
            if collided_id == "rightWall" and self.rect.right > SCREEN_WIDTH:
                self.rect.right = SCREEN_WIDTH
                self.pos.x = self.rect.center[0]

            # if hit left wall, push back in bounds and negate (reverse) x direction
            elif collided_id == "leftWall" and self.rect.left < 0:
                self.rect.left = 0
                self.pos.x = self.rect.center[0]

            # if hit top wall, push back in bounds and negate (reverse) y direction
            elif collided_id == "topWall" and self.rect.top < 0:
                self.rect.top = 0
                self.pos.y = self.rect.center[1]

            # if hit bottom wall, push back in bound, turn off movement and check whether this is the first bullet to
            # hit the floor
            elif collided_id == "bottomWall" and self.rect.bottom > GAMESCREEN_HEIGHT and\
                    delay_before_bottom_collision == 0:
                self.rect.bottom = GAMESCREEN_HEIGHT
                self.pos.y = self.rect.center[1]
                self.active = False
                # if no other bullet has hit the floor, set the global bullet position to the center of this bullet
                if not first_hit_floor:
                    first_hit_floor = True
                    bullets_pos = self.rect.center
                # if other bullet(s) has hit the floor, set this bullets position to the global bullet position
                if first_hit_floor:
                    self.rect.center = self.pos = bullets_pos

        # if the side of collision is not known (currently when bullet hits a block)
        else:
            new_location = self.prev_pos
            # print(f"absolute location: {abs_location}, previous location: {self.prev_pos}, rect: "
                  # f"{collided_sprite.rect}\n rect vals: {collided_sprite.rect.bottom}, {collided_sprite.rect.top}, "
                  # f"{collided_sprite.rect.left}, {collided_sprite.rect.right}")

            if self.prev_pos.x > collided_sprite.rect.right:
                magnitude = (collided_sprite.rect.right - self.prev_pos.x) / self.dir.x
                new_location.y += magnitude * self.dir.y
                new_location.x = collided_sprite.rect.right
                side = "right"
                # print(f"right; magnitude: {magnitude}, new location: {new_location}")
            elif self.prev_pos.x < collided_sprite.rect.left:
                magnitude = (collided_sprite.rect.left - self.prev_pos.x) / self.dir.x
                new_location.y += magnitude * self.dir.y
                new_location.x = collided_sprite.rect.left
                side = "left"
                # print(f"left; magnitude: {magnitude}, new location: {new_location}")

            if self.prev_pos.y < collided_sprite.rect.top:
                magnitude = (collided_sprite.rect.top - self.prev_pos.y) / self.dir.y
                new_location.x += magnitude * self.dir.x
                new_location.y = collided_sprite.rect.top
                side = "top"
                # print(f"top; magnitude: {magnitude}, new location: {new_location}")
            elif self.prev_pos.y > collided_sprite.rect.bottom:
                magnitude = (collided_sprite.rect.bottom - self.prev_pos.y) / self.dir.y
                new_location.x += magnitude * self.dir.x
                new_location.y = collided_sprite.rect.bottom
                side = "bottom"
                # print(f"bottom; magnitude: {magnitude}, new location: {new_location}")

            self.rect.topleft = new_location
            self.pos = pygame.math.Vector2(self.rect.topleft)

        if collided_id != self.last_collided:
            if side == "left" or side == "right":
                self.dir.x *= -1
            if side == "top" or side == "bottom":
                self.dir.y *= -1

        self.last_collided = collided_id


bullets.add(Bullet(bullets_pos, track=True))

spawn_row(difficulty_func(curr_round))

all_sprites.add(blocks, bullets)
while running:
    game_window.fill((255, 255, 255))
    pygame.draw.rect(window, (255, 255, 255), pygame.Rect(0, 408, SCREEN_WIDTH, SCREEN_HEIGHT-408))
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and not bullets_active:
            mouse_pos = pygame.mouse.get_pos()
            if not mouse_pos[1] >= bullets_pos[1]:
                bullets_active = True
                delay_before_bottom_collision = (FRAMERATE*6)//60
                angle = atan2(bullets_pos[1]-mouse_pos[1], mouse_pos[0]-bullets_pos[0])
                if angle < pi/18:
                    angle = pi/18
                # print("clicked and bullets inactive")
                for bullet in bullets:
                    bullet.dir.x = cos(angle)
                    bullet.dir.y = -sin(angle)
            # print(str(angle), " ", str(bullet1.dir.x), " ", str(bullet1.dir.y))

    if bullets_active and num_bullets_left_bottom < accumulated_bullets and subframe == 1:
        bullets.sprites()[num_bullets_left_bottom].active = True
        num_bullets_left_bottom += 1

    all_sprites.draw(game_window)

    if bullets_active:
        for i in range(SPEED):
            bullets.update()
            for bullet, blocklist in pygame.sprite.groupcollide(bullets, blocks, False, False,
                                                                collided=pygame.sprite.collide_mask).items():
                # print(bullet, blocklist)
                for block in blocklist:
                    if block.ident != bullet.last_collided:
                        block.collided(bullet, collided_location=pygame.sprite.collide_mask(block, bullet))

            if pygame.sprite.groupcollide(bullets, bonuses, False, True, collided=pygame.sprite.collide_mask):
                bullets_to_add += 1

    if subframe == 1 and bullets_active:
        for bullet in bullets:
            # print("\nBullet ident: " + str(bullet.ident) + "\nBullet pos (rect): " + str(bullet.rect.center) +
            #     "\nBullet pos (movement): " + str(bullet.pos) + "\nBullet dir: " + str(bullet.dir))
            bullets_active = False
            if bullet.active:
                bullets_active = True
                break
        else:
            num_bullets_left_bottom = 0
            accumulated_bullets += bullets_to_add
            for i in range(bullets_to_add):
                bullet_to_add = Bullet(bullets_pos)
                bullets.add(bullet_to_add)
                all_sprites.add(bullet_to_add)
            bullets_to_add = 0
            first_hit_floor = False
            curr_round += 1

            blocks.update()
            bonuses.update()

            spawn_row(difficulty_func(curr_round))
            print("New round")

    if not bullets_active:
        bullet_counter_text = stdFont.render(f"x{accumulated_bullets}", True, (0, 0, 0), (255, 255, 255))
        window.blit(bullet_counter_text, (bullets_pos[0]-8, bullets_pos[1]+24))

    if subframe >= (FRAMERATE*2)//60:
        subframe = 0

    if delay_before_bottom_collision > 0:
        delay_before_bottom_collision -= 1

    subframe += 1

    gameClock.tick(FRAMERATE)
    pygame.display.flip()
