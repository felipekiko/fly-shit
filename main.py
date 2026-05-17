#!/usr/bin/env python3
"""FLY SHIT! - O jogo da mosca contaminante (2 jogadores)"""

import pygame
import sys
import math
import random
import json
import struct
from pathlib import Path
from pygame.math import Vector2

try:
    from platformdirs import user_data_dir
    HS_PATH = Path(user_data_dir("FlyShit", "KiKo")) / "highscore.json"
except ImportError:
    HS_PATH = Path("highscore.json")

pygame.mixer.pre_init(22050, -16, 1, 512)
pygame.init()
pygame.font.init()

# ═══════════════════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════════════════
W, H = 1280, 720
FPS  = 60
TITLE = "Fly Shit! — 2 Jogadores"

PHASE_POINTS = 20

BG         = (125, 155, 70)
BG_DARK    = (105, 135, 55)
BLACK      = (0, 0, 0)
WHITE      = (255, 255, 255)
YELLOW     = (255, 215, 0)
RED        = (220, 50, 50)
POOP_DARK  = (90, 58, 18)
POOP_MID   = (110, 72, 22)
POOP_LIGHT = (140, 95, 35)
WING_COL   = (190, 215, 255)
SKIN       = (255, 218, 175)

LOC_COLORS = {
    "house":       ((195, 155, 105), (155, 120, 80)),
    "bakery":      ((215, 185, 120), (175, 145, 90)),
    "restaurant":  ((185, 85, 85),   (145, 60, 60)),
    "supermarket": ((80, 130, 200),  (60, 100, 160)),
    "hospital":    ((225, 225, 235), (175, 175, 190)),
}

ROOM_COLORS = {
    "quarto":  ((175, 155, 210), (135, 118, 170)),
    "sala":    ((205, 185, 145), (165, 145, 110)),
    "cozinha": ((170, 215, 200), (130, 172, 158)),
}

ATTACK_COLORS = {
    "hand":    (220, 50,  50),
    "slipper": (200, 160, 80),
    "spray":   (60,  200, 80),
}

# Cores de fundo por fase (bg, tile_dark)
BG_PHASES = {
    1: ((125, 155,  70), (105, 135, 55)),   # dia ensolarado
    2: ((148, 140,  62), (120, 114, 46)),   # tarde quente
    3: ((155, 108,  60), (125,  85, 44)),   # entardecer
    4: (( 68,  72,  82), ( 50,  55, 64)),   # anoitecer
}

BR_GREEN  = (0, 130, 55)
BR_YELLOW = (255, 210, 0)
BR_BLUE   = (0,  45, 130)

DEATH_INSULTS = [
    "mosquinha filha da puta, morreu!",
    "vai pro inferno, fedorenta!",
    "toma essa, praga nojenta!",
    "que se lasque, moscão imundo!",
    "morreu a chata, aeeeee!",
    "xô mosca, xô! ia xô!",
    "foi pro brejo essa pragazinha!",
    "tá pensando que é quem, mosca?!",
    "apanha que é pro bem, mosca suja!",
    "uma mosca a menos nesse mundão!",
    "vai lavar a asa, fedida!",
    "morreu igual barata de banheiro!",
]


def _draw_br_flag(surf, x, y, w=18, h=12):
    """Desenha uma mini bandeira do Brasil."""
    pygame.draw.rect(surf, BR_GREEN, (x, y, w, h))
    diamond = [(x + w // 2, y + 1), (x + w - 2, y + h // 2),
               (x + w // 2, y + h - 1), (x + 2, y + h // 2)]
    pygame.draw.polygon(surf, BR_YELLOW, diamond)
    pygame.draw.circle(surf, BR_BLUE, (x + w // 2, y + h // 2), max(2, h // 4))

# controles por jogador
P1_KEYS = {
    "up": pygame.K_w, "down": pygame.K_s,
    "left": pygame.K_a, "right": pygame.K_d,
}
P2_KEYS = {
    "up": pygame.K_UP, "down": pygame.K_DOWN,
    "left": pygame.K_LEFT, "right": pygame.K_RIGHT,
}

# cores das moscas
P1_CLEAN  = (28,  28,  28)
P1_LOADED = (100, 65,  15)
P2_CLEAN  = (20,  55, 160)
P2_LOADED = (80,  55,  10)
P2_WING   = (200, 215, 245)
P2_EYE    = (140, 40,  200)


# ═══════════════════════════════════════════════════════════
#  PARTICLE
# ═══════════════════════════════════════════════════════════
class Particle:
    def __init__(self, pos, text, color, size=20):
        self.pos      = Vector2(pos)
        self.vel      = Vector2(random.uniform(-0.8, 0.8), -2.8)
        self.text     = text
        self.color    = color
        self.life     = 80
        self.max_life = 80
        self.font     = pygame.font.SysFont("Arial", size, bold=True)

    def update(self):
        self.pos += self.vel
        self.vel.y += 0.04
        self.life -= 1

    def draw(self, surf):
        a = max(0, int(255 * self.life / self.max_life))
        s = self.font.render(self.text, True, self.color)
        s.set_alpha(a)
        surf.blit(s, (self.pos.x - s.get_width() // 2, self.pos.y))

    @property
    def dead(self):
        return self.life <= 0


# ═══════════════════════════════════════════════════════════
#  DOT PARTICLE  (poop pickup effect)
# ═══════════════════════════════════════════════════════════
class DotParticle:
    def __init__(self, pos, color, radius=4):
        self.pos      = Vector2(pos)
        self.vel      = Vector2(random.uniform(-2.5, 2.5), random.uniform(-3.0, -0.5))
        self.color    = color
        self.radius   = radius
        self.life     = random.randint(20, 35)
        self.max_life = self.life

    def update(self):
        self.pos   += self.vel
        self.vel.y += 0.15
        self.life  -= 1

    def draw(self, surf):
        a = max(0, int(255 * self.life / self.max_life))
        s = pygame.Surface((self.radius * 2 + 2, self.radius * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, a), (self.radius + 1, self.radius + 1), self.radius)
        surf.blit(s, (int(self.pos.x) - self.radius - 1, int(self.pos.y) - self.radius - 1))

    @property
    def dead(self):
        return self.life <= 0


# ═══════════════════════════════════════════════════════════
#  SLIPPER
# ═══════════════════════════════════════════════════════════
class Slipper:
    SPEED    = 4.5
    LIFETIME = 70
    RADIUS   = 12

    def __init__(self, origin: Vector2, target: Vector2):
        self.pos   = Vector2(origin)
        diff       = target - origin
        self.vel   = diff.normalize() * self.SPEED if diff.length() > 0 else Vector2(0, -self.SPEED)
        self.life  = self.LIFETIME
        self.angle = math.degrees(math.atan2(-diff.y, diff.x))

    def update(self):
        self.pos  += self.vel
        self.life -= 1
        self.angle += 15

    def check_hit(self, fly) -> bool:
        return (fly.pos - self.pos).length() < self.RADIUS + fly.radius

    def draw(self, surf):
        x, y = int(self.pos.x), int(self.pos.y)
        s = pygame.Surface((38, 22), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (205, 175, 125), (0, 5, 38, 14))
        pygame.draw.ellipse(s, (165, 130, 85),  (0, 5, 38, 14), 2)
        pygame.draw.line(s, (110, 70, 30), (19, 0),  (19, 8),  3)
        pygame.draw.line(s, (110, 70, 30), (19, 8),  (7,  17), 3)
        pygame.draw.line(s, (110, 70, 30), (19, 8),  (31, 17), 3)
        rotated = pygame.transform.rotate(s, self.angle)
        surf.blit(rotated, (x - rotated.get_width() // 2, y - rotated.get_height() // 2))

    @property
    def dead(self):
        return self.life <= 0


# ═══════════════════════════════════════════════════════════
#  SPRAY CLOUD
# ═══════════════════════════════════════════════════════════
class SprayCloud:
    SPEED    = 2.2
    LIFETIME = 55
    MIN_R    = 7
    MAX_R    = 30

    def __init__(self, origin: Vector2, target: Vector2):
        self.pos  = Vector2(origin)
        diff      = target - origin
        self.vel  = diff.normalize() * self.SPEED if diff.length() > 0 else Vector2(0, -self.SPEED)
        self.life = self.LIFETIME
        self.dots = [(random.uniform(-1, 1) * 5, random.uniform(-1, 1) * 5) for _ in range(6)]

    @property
    def radius(self) -> float:
        return self.MIN_R + (self.MAX_R - self.MIN_R) * (1 - self.life / self.LIFETIME)

    def update(self):
        self.pos  += self.vel
        self.vel  *= 0.96
        self.life -= 1

    def check_hit(self, fly) -> bool:
        return (fly.pos - self.pos).length() < self.radius + fly.radius

    def draw(self, surf):
        r = max(1, int(self.radius))
        a = int(190 * self.life / self.LIFETIME)
        x, y = int(self.pos.x), int(self.pos.y)
        cloud = pygame.Surface((r * 2 + 10, r * 2 + 10), pygame.SRCALPHA)
        cx = r + 5
        pygame.draw.circle(cloud, (100, 210, 70, a),       (cx, cx), r)
        pygame.draw.circle(cloud, (160, 240, 100, a // 2), (cx, cx), r, 2)
        dr = max(2, r // 4)
        for dx, dy in self.dots:
            pygame.draw.circle(cloud, (210, 255, 120, min(255, a + 40)),
                               (cx + int(dx * r / 5), cx + int(dy * r / 5)), dr)
        surf.blit(cloud, (x - r - 5, y - r - 5))

    @property
    def dead(self):
        return self.life <= 0


# ═══════════════════════════════════════════════════════════
#  HUMAN
# ═══════════════════════════════════════════════════════════
class Human:
    CATCH_RADIUS  = 13
    PATROL_RADIUS = 42

    def __init__(self, pos: Vector2, bounds: pygame.Rect,
                 speed: float, detect: float, tier: int = 0):
        self.pos         = Vector2(pos)
        self.home        = Vector2(pos)
        self.bounds      = bounds
        self.base_speed  = speed
        self.base_detect = detect
        self.speed       = speed
        self.detect      = detect
        self.tier        = tier
        self.attack_type = "hand"
        self.state       = "patrol"
        self.ptarget     = Vector2(pos)
        self.ptimer      = 0
        self.projectile  = None
        self.throw_cd    = 0
        r = random.random()
        if r < 0.22:
            self.shirt = BR_GREEN
        elif r < 0.42:
            self.shirt = BR_YELLOW
        else:
            hue = random.randint(0, 360)
            c   = pygame.Color(0)
            c.hsva = (hue, 70, 80, 100)
            self.shirt = tuple(c)[:3]
        self.has_havaiana = random.random() < 0.45
        self.has_cap      = random.random() < 0.30
        self.cap_col      = BR_GREEN if random.random() < 0.5 else BR_YELLOW
        self.has_beer     = random.random() < 0.28

    def update(self, fly_positions: list):
        """Persegue a mosca viva mais próxima."""
        if not fly_positions:
            return
        nearest = min(fly_positions, key=lambda p: (p - self.pos).length())
        dist    = (nearest - self.pos).length()

        if dist < self.detect:
            self.state = "chase"
        elif dist > self.detect * 1.4:
            self.state = "patrol"

        if self.state == "chase":
            if dist > 1:
                move_speed = self.speed * (0.5 if self.attack_type == "slipper" else 1.0)
                d = (nearest - self.pos).normalize()
                self.pos += d * move_speed
                pad = self.bounds.inflate(25, 15)
                self.pos.x = max(pad.left, min(pad.right,  self.pos.x))
                self.pos.y = max(pad.top,  min(pad.bottom, self.pos.y))
            if self.throw_cd <= 0:
                if self.attack_type == "slipper" and dist < self.detect * 0.70:
                    self.projectile = Slipper(Vector2(self.pos), Vector2(nearest))
                    self.throw_cd   = 140
                elif self.attack_type == "spray" and dist < self.detect * 0.78:
                    self.projectile = SprayCloud(Vector2(self.pos), Vector2(nearest))
                    self.throw_cd   = 95
        else:
            self.ptimer -= 1
            if self.ptimer <= 0:
                self.ptarget = Vector2(
                    self.home.x + random.uniform(-self.PATROL_RADIUS, self.PATROL_RADIUS),
                    self.home.y + random.uniform(-self.PATROL_RADIUS * 0.5, self.PATROL_RADIUS * 0.5),
                )
                self.ptarget.x = max(self.bounds.left + 8,  min(self.bounds.right - 8,  self.ptarget.x))
                self.ptarget.y = max(self.bounds.top  + 20, min(self.bounds.bottom - 8, self.ptarget.y))
                self.ptimer = random.randint(60, 180)
            if (self.ptarget - self.pos).length() > 2:
                d = (self.ptarget - self.pos).normalize()
                self.pos += d * (self.speed * 0.38)

        self.throw_cd = max(0, self.throw_cd - 1)
        if self.projectile:
            self.projectile.update()
            if self.projectile.dead:
                self.projectile = None

    def check_kill(self, fly) -> bool:
        if (fly.pos - self.pos).length() < self.CATCH_RADIUS + fly.radius:
            if self.attack_type != "slipper":
                return True
        return self.projectile is not None and self.projectile.check_hit(fly)

    def draw(self, surf):
        x, y    = int(self.pos.x), int(self.pos.y)
        chasing = self.state == "chase"
        atc     = self.attack_type
        pygame.draw.ellipse(surf, (0, 0, 0), (x - 8, y + 13, 16, 7))
        pygame.draw.line(surf, self.shirt, (x - 3, y + 6),  (x - 6, y + 16), 3)
        pygame.draw.line(surf, self.shirt, (x + 3, y + 6),  (x + 6, y + 16), 3)
        pygame.draw.rect(surf, self.shirt, (x - 7, y - 8, 14, 15), border_radius=4)
        if chasing:
            pygame.draw.line(surf, self.shirt, (x - 7, y - 4), (x - 16, y - 13), 3)
            pygame.draw.line(surf, self.shirt, (x + 7, y - 4), (x + 16, y - 13), 3)
            pygame.draw.circle(surf, ATTACK_COLORS[atc], (x, y - 27), 5)
            pygame.draw.circle(surf, WHITE, (x, y - 27), 5, 1)
        else:
            pygame.draw.line(surf, self.shirt, (x - 7, y - 4), (x - 14, y + 2), 3)
            pygame.draw.line(surf, self.shirt, (x + 7, y - 4), (x + 14, y + 2), 3)
        pygame.draw.circle(surf, SKIN,  (x, y - 14), 8)
        pygame.draw.circle(surf, BLACK, (x - 3, y - 15), 2)
        pygame.draw.circle(surf, BLACK, (x + 3, y - 15), 2)
        if chasing:
            pygame.draw.line(surf, BLACK, (x - 6, y - 20), (x - 1, y - 18), 2)
            pygame.draw.line(surf, BLACK, (x + 1, y - 18), (x + 6, y - 20), 2)
        if chasing:
            if atc == "slipper":
                s = pygame.Surface((22, 13), pygame.SRCALPHA)
                pygame.draw.ellipse(s, (200, 170, 120), (0, 3, 22, 8))
                pygame.draw.line(s, (110, 70, 30), (11, 0), (11, 5), 2)
                pygame.draw.line(s, (110, 70, 30), (11, 5), (5, 10), 2)
                pygame.draw.line(s, (110, 70, 30), (11, 5), (17, 10), 2)
                surf.blit(s, (x + 13, y - 15))
            elif atc == "spray":
                pygame.draw.rect(surf, (40, 170, 60),    (x + 13, y - 16, 7, 14), border_radius=2)
                pygame.draw.circle(surf, (200, 235, 200), (x + 16, y - 17), 3)
                pygame.draw.rect(surf, (20, 20, 20),     (x + 18, y - 13, 5, 3))
                if self.throw_cd < 20:
                    ms = pygame.Surface((14, 10), pygame.SRCALPHA)
                    pygame.draw.circle(ms, (100, 220, 80, 120), (7, 5), 5)
                    surf.blit(ms, (x + 21, y - 16))
        # havaianas
        if self.has_havaiana:
            pygame.draw.ellipse(surf, (15, 75, 210), (x - 9, y + 17, 9, 4))
            pygame.draw.ellipse(surf, (15, 75, 210), (x + 1,  y + 17, 9, 4))
        # boné
        if self.has_cap:
            pygame.draw.rect(surf, self.cap_col, (x - 7, y - 22, 14, 6), border_radius=2)
            pygame.draw.rect(surf, self.cap_col, (x - 7, y - 17, 20, 3), border_radius=1)
        # latinha (só em patrol)
        if not chasing and self.has_beer:
            pygame.draw.rect(surf, (205, 30, 30), (x + 12, y - 6, 6, 12), border_radius=2)
            pygame.draw.rect(surf, (240, 195, 40), (x + 12, y - 6, 6, 4))
        if self.projectile:
            self.projectile.draw(surf)


# ═══════════════════════════════════════════════════════════
#  LOCATION
# ═══════════════════════════════════════════════════════════
class Location:
    def __init__(self, rect, name: str, loc_type: str, points: int,
                 n_humans: int, speed: float, detect: float):
        self.rect     = pygame.Rect(rect)
        self.name     = name
        self.loc_type = loc_type
        self.points   = points
        self.humans: list[Human] = []
        self.fsmall   = pygame.font.SysFont("Arial", 13, bold=True)
        self.fpts     = pygame.font.SysFont("Arial", 11)
        self._spawn(n_humans, speed, detect)

    def _spawn(self, n, speed, detect):
        tier = 0 if self.points <= 4 else (1 if self.points <= 7 else 2)
        for i in range(n):
            px = self.rect.x + (i + 1) * self.rect.w // (n + 1)
            py = self.rect.centery + 10
            self.humans.append(Human(Vector2(px, py), self.rect, speed, detect, tier))

    @property
    def colors(self):
        return LOC_COLORS.get(self.loc_type, ((160,160,160),(120,120,120)))

    def update(self, fly_positions: list):
        for h in self.humans:
            h.update(fly_positions)

    def contains(self, fly) -> bool:
        return self.rect.collidepoint(fly.pos)

    def _draw_deco(self, surf):
        x, y, w, h = self.rect.x, self.rect.y, self.rect.w, self.rect.h
        cx = x + w // 2

        # toldinho listrado verde/amarelo sobre a entrada
        aw_x = cx - 30
        for i in range(6):
            col = BR_GREEN if i % 2 == 0 else BR_YELLOW
            pygame.draw.rect(surf, col, (aw_x + i * 10, y + 18, 10, 7))
        pygame.draw.rect(surf, (80, 60, 30), (aw_x, y + 24, 60, 2))

        # mini bandeira canto direito
        _draw_br_flag(surf, x + w - 22, y + 27, 18, 12)

        if self.name == "Padaria":
            # placa + xícara de café + pão de queijo
            pygame.draw.rect(surf, (200, 160, 60), (x + 5, y + 28, 55, 18), border_radius=3)
            t = self.fpts.render("Pão de Queijo!", True, (80, 40, 10))
            surf.blit(t, (x + 7, y + 31))
            pygame.draw.ellipse(surf, (60, 35, 12), (x + 5, y + 50, 14, 10))
            pygame.draw.arc(surf, (60, 35, 12), (x + 17, y + 52, 5, 6), 0, math.pi, 2)
            pygame.draw.ellipse(surf, (220, 170, 80), (x + 6, y + 52, 12, 5))

        elif self.name == "Restaurante":
            # placa + espetinho + churrasqueira
            pygame.draw.rect(surf, (170, 55, 40), (x + 5, y + 28, 60, 16), border_radius=3)
            t = self.fpts.render("Rodízio R$49!", True, WHITE)
            surf.blit(t, (x + 7, y + 31))
            pygame.draw.line(surf, (150, 85, 20), (x + 10, y + 52), (x + 10, y + 68), 2)
            for yy in [y + 54, y + 59, y + 64]:
                pygame.draw.circle(surf, (180, 55, 30), (x + 10, yy), 4)
                pygame.draw.circle(surf, (200, 100, 20), (x + 10, yy), 2)
            # fumaça
            for fx in [x+8, x+12]:
                pygame.draw.arc(surf, (160, 160, 160),
                                (fx, y + 46, 6, 6), 0, math.pi, 2)

        elif self.name == "Supermercado":
            pygame.draw.rect(surf, (55, 80, 185), (x + 5, y + 28, 65, 16), border_radius=3)
            t = self.fpts.render("OFERTA DO DIA!", True, BR_YELLOW)
            surf.blit(t, (x + 7, y + 31))
            # carrinho de compras
            pygame.draw.lines(surf, (45, 65, 155),
                              False, [(x+6,y+52),(x+10,y+47),(x+24,y+47),(x+26,y+54)], 2)
            pygame.draw.circle(surf, (45, 65, 155), (x + 11, y + 57), 3)
            pygame.draw.circle(surf, (45, 65, 155), (x + 23, y + 57), 3)
            # açaí
            pygame.draw.rect(surf, (100, 40, 140), (x + 30, y + 48, 10, 14), border_radius=2)
            t2 = self.fpts.render("açaí", True, (180, 100, 220))
            surf.blit(t2, (x + 28, y + 64))

        elif self.name == "Hospital":
            pygame.draw.rect(surf, (200, 210, 230), (x + 5, y + 28, 65, 16), border_radius=3)
            t = self.fpts.render("PRONTO SUS", True, (140, 30, 30))
            surf.blit(t, (x + 7, y + 31))
            pygame.draw.rect(surf, RED, (x + 13, y + 50, 14, 4))
            pygame.draw.rect(surf, RED, (x + 18, y + 45,  4, 14))
            # ambulância mini
            pygame.draw.rect(surf, WHITE, (x + 32, y + 55, 22, 12), border_radius=2)
            pygame.draw.rect(surf, RED,   (x + 32, y + 55, 10, 12), border_radius=2)
            pygame.draw.rect(surf, RED,   (x + 35, y + 51,  4,  4))
            pygame.draw.circle(surf, (40, 40, 40), (x + 36, y + 67), 3)
            pygame.draw.circle(surf, (40, 40, 40), (x + 50, y + 67), 3)

        elif self.name == "Churrascaria":
            pygame.draw.rect(surf, (165, 80, 30), (x + 5, y + 28, 65, 16), border_radius=3)
            t = self.fpts.render("Churrasco +Chope", True, WHITE)
            surf.blit(t, (x + 7, y + 31))
            # caneca de chope
            pygame.draw.rect(surf, (215, 190, 70), (x + 5, y + 48, 14, 18), border_radius=3)
            pygame.draw.arc(surf, (215, 190, 70), (x + 16, y + 51, 6, 10), 0, math.pi*2, 2)
            pygame.draw.rect(surf, WHITE, (x + 6, y + 49, 12, 5), border_radius=1)
            # churrasco na brasa
            pygame.draw.rect(surf, (80, 50, 20),  (x + 24, y + 58, 30, 6), border_radius=2)
            pygame.draw.rect(surf, (220, 80, 20),  (x + 26, y + 58, 26, 3))
            pygame.draw.line(surf, (160, 90, 20), (x + 30, y + 48), (x + 30, y + 58), 2)
            for yy in [y+50, y+54]:
                pygame.draw.ellipse(surf, (185, 60, 30), (x+27, yy, 8, 5))

        elif self.name == "Escola":
            pygame.draw.rect(surf, (60, 120, 65), (x + 5, y + 28, 60, 16), border_radius=3)
            t = self.fpts.render("Escola Municipal", True, WHITE)
            surf.blit(t, (x + 7, y + 31))
            # mastro com bandeira BR
            pygame.draw.line(surf, (100, 70, 40), (x + 8, y + 47), (x + 8, y + 70), 2)
            _draw_br_flag(surf, x + 9, y + 47, 22, 14)
            # lousa
            pygame.draw.rect(surf, (25, 65, 30), (x + 36, y + 48, 30, 20), border_radius=2)
            lt = self.fpts.render("BRASIL", True, BR_YELLOW)
            surf.blit(lt, (x + 37, y + 52))

        elif self.name == "Lanchonete":
            pygame.draw.rect(surf, (210, 145, 35), (x + 5, y + 28, 60, 16), border_radius=3)
            t = self.fpts.render("X-Búrgão R$15", True, (60, 30, 5))
            surf.blit(t, (x + 7, y + 31))
            # burguer camadas
            for i, col in enumerate([(180,110,40),(100,170,50),(220,55,35),(215,175,75)]):
                pygame.draw.ellipse(surf, col, (x + 5, y + 50 + i * 4, 22, 5))
            # guaraná
            pygame.draw.rect(surf, (20, 140, 30), (x + 32, y + 48, 10, 18), border_radius=3)
            pygame.draw.rect(surf, BR_YELLOW,     (x + 32, y + 48, 10, 6))
            gt = self.fpts.render("Gu", True, (20, 100, 25))
            surf.blit(gt, (x + 30, y + 67))

        elif self.name == "Farmácia":
            pygame.draw.rect(surf, (20, 140, 60), (x + 5, y + 28, 65, 16), border_radius=3)
            t = self.fpts.render("Farmácia Popular", True, WHITE)
            surf.blit(t, (x + 7, y + 31))
            pygame.draw.rect(surf, BR_GREEN, (x + 10, y + 50, 14, 4))
            pygame.draw.rect(surf, BR_GREEN, (x + 15, y + 45,  4, 14))
            # remédios
            for i, col in enumerate([(220, 50, 50), (50, 100, 220), (220, 180, 30)]):
                pygame.draw.rect(surf, col, (x + 30 + i*10, y + 52, 8, 12), border_radius=3)
                pygame.draw.line(surf, WHITE, (x+30+i*10, y+58), (x+37+i*10, y+58), 1)

    def draw(self, surf):
        main, dark = self.colors
        pygame.draw.rect(surf, dark, self.rect.inflate(4, 4), border_radius=7)
        pygame.draw.rect(surf, main, self.rect,               border_radius=6)
        roof = pygame.Rect(self.rect.x, self.rect.y, self.rect.w, 20)
        pygame.draw.rect(surf, dark, roof, border_radius=6)
        dw, dh = 14, 22
        dx, dy = self.rect.centerx - dw // 2, self.rect.bottom - dh
        pygame.draw.rect(surf, dark, (dx, dy, dw, dh), border_radius=3)
        pygame.draw.circle(surf, (200,180,120), (dx + dw - 4, dy + dh // 2), 2)
        self._draw_deco(surf)
        lbl = self.fsmall.render(self.name, True, WHITE)
        surf.blit(lbl, (self.rect.centerx - lbl.get_width() // 2, self.rect.y + 3))
        p_txt = self.fpts.render(f"+{self.points}pts", True, (255, 235, 60))
        surf.blit(p_txt, (self.rect.centerx - p_txt.get_width() // 2, self.rect.bottom - 16))
        for h in self.humans:
            h.draw(surf)


# ═══════════════════════════════════════════════════════════
#  ROOM
# ═══════════════════════════════════════════════════════════
class Room:
    def __init__(self, rect, room_type: str, points: int,
                 n_humans: int, speed: float, detect: float):
        self.rect      = pygame.Rect(rect)
        self.room_type = room_type
        self.points    = points
        self.humans: list[Human] = []
        self.fname     = pygame.font.SysFont("Arial", 11, bold=True)
        self.fpts      = pygame.font.SysFont("Arial", 10)
        self._spawn(n_humans, speed, detect)

    def _spawn(self, n, speed, detect):
        tier = 0 if self.points <= 3 else (1 if self.points <= 5 else 2)
        for i in range(n):
            px = self.rect.x + (i + 1) * self.rect.w // (n + 1)
            py = self.rect.centery + 8
            self.humans.append(Human(Vector2(px, py), self.rect, speed, detect, tier))

    @property
    def colors(self):
        return ROOM_COLORS.get(self.room_type, ((160,160,160),(120,120,120)))

    def update(self, fly_positions: list):
        for h in self.humans:
            h.update(fly_positions)

    def contains(self, fly) -> bool:
        return self.rect.collidepoint(fly.pos)

    def check_kills(self, fly) -> bool:
        return any(h.check_kill(fly) for h in self.humans)

    def _draw_furniture(self, surf):
        x, y, w, h = self.rect
        cx, cy = x + w // 2, y + h // 2
        if self.room_type == "quarto":
            pygame.draw.rect(surf, (140, 100, 70),  (cx-28, cy,   56, 32), border_radius=3)
            pygame.draw.rect(surf, (220, 200, 180), (cx-28, cy,   56, 14), border_radius=3)
            pygame.draw.rect(surf, (200, 180, 160), (cx-22, cy+2, 20, 10), border_radius=2)
            pygame.draw.rect(surf, (200, 180, 160), (cx+2,  cy+2, 20, 10), border_radius=2)
            # mini bandeira na parede
            _draw_br_flag(surf, x + 4, y + 4, 14, 9)
        elif self.room_type == "sala":
            pygame.draw.rect(surf, (120, 80, 60),  (cx-35, cy+4,  70, 22), border_radius=4)
            pygame.draw.rect(surf, (150, 100, 75), (cx-35, cy-4,  70, 12), border_radius=3)
            pygame.draw.rect(surf, (40, 40, 40),   (cx-18, cy-32, 36, 24), border_radius=2)
            pygame.draw.rect(surf, (80, 160, 220), (cx-15, cy-30, 30, 18))
            # bola de futebol
            pygame.draw.circle(surf, WHITE,   (x + 8, cy + 16), 7)
            pygame.draw.circle(surf, (30,30,30), (x + 8, cy + 16), 7, 1)
            pygame.draw.polygon(surf, (30,30,30),
                [(x+8, cy+10),(x+5,cy+14),(x+8,cy+18),(x+11,cy+14)])
        elif self.room_type == "cozinha":
            pygame.draw.rect(surf, (160, 160, 155), (cx-38, cy+4,  76, 18), border_radius=3)
            pygame.draw.rect(surf, (80, 80, 80),    (cx-38, cy-18, 36, 22), border_radius=2)
            pygame.draw.circle(surf, (200, 80, 30), (cx-26, cy-10), 5)
            pygame.draw.circle(surf, (200, 80, 30), (cx-14, cy-10), 5)
            pygame.draw.rect(surf, (230, 230, 235), (cx+4,  cy-22, 28, 42), border_radius=3)
            pygame.draw.line(surf, (180,180,180), (cx+4, cy-2), (cx+32, cy-2), 2)
            # lata de feijão
            pygame.draw.rect(surf, (180, 90, 30), (x + 4, cy - 2, 10, 14), border_radius=2)
            pygame.draw.rect(surf, (220, 140, 60), (x + 4, cy - 2, 10, 5))

    def draw(self, surf):
        main, dark = self.colors
        pygame.draw.rect(surf, dark, self.rect.inflate(2, 2), border_radius=3)
        pygame.draw.rect(surf, main, self.rect,               border_radius=3)
        self._draw_furniture(surf)
        names = {"quarto": "Quarto", "sala": "Sala", "cozinha": "Cozinha"}
        lbl = self.fname.render(names.get(self.room_type, ""), True, (30, 30, 30))
        surf.blit(lbl, (self.rect.centerx - lbl.get_width() // 2, self.rect.y + 3))
        pts = self.fpts.render(f"+{self.points}pts", True, (60, 40, 10))
        surf.blit(pts, (self.rect.centerx - pts.get_width() // 2, self.rect.bottom - 14))
        for h in self.humans:
            h.draw(surf)


# ═══════════════════════════════════════════════════════════
#  HOUSE
# ═══════════════════════════════════════════════════════════
class House:
    WALL = (130, 100, 68)
    ROOF = (155, 80, 60)

    def __init__(self, rect):
        self.rect  = pygame.Rect(rect)
        self.rooms: list[Room] = []
        self.fname = pygame.font.SysFont("Arial", 13, bold=True)
        self._build()

    def _build(self):
        x, y, w, h = self.rect
        ix, iy  = x + 2, y + 22
        iw, ih  = w - 4, h - 24
        top_h   = ih // 2 - 2
        bot_h   = ih - top_h - 4
        mid_y   = iy + top_h + 4
        left_w  = iw // 2 - 2
        right_w = iw - left_w - 2
        self.rooms = [
            Room((ix,              iy,    left_w,  top_h), "quarto",  2, 1, 0.42, 60),
            Room((ix + left_w + 2, iy,    right_w, top_h), "sala",    3, 1, 0.58, 68),
            Room((ix,              mid_y, iw,      bot_h), "cozinha", 4, 1, 0.70, 76),
        ]

    def update(self, fly_positions: list):
        for r in self.rooms:
            r.update(fly_positions)

    def score_room(self, fly):
        if not fly.loaded:
            return 0, ""
        for r in self.rooms:
            if r.contains(fly):
                fly.loaded = False
                return r.points, r.room_type
        return 0, ""

    def check_kills(self, fly) -> bool:
        return any(r.check_kills(fly) for r in self.rooms)

    def draw(self, surf):
        pygame.draw.rect(surf, (100, 75, 48), self.rect.inflate(6, 6), border_radius=10)
        pygame.draw.rect(surf, (190, 150, 105), self.rect, border_radius=8)
        roof = pygame.Rect(self.rect.x, self.rect.y, self.rect.w, 22)
        pygame.draw.rect(surf, self.ROOF, roof, border_radius=8)
        x, y, w, h = self.rect
        ix, iy  = x + 2, y + 22
        iw, ih  = w - 4, h - 24
        top_h   = ih // 2 - 2
        mid_y   = iy + top_h + 4
        mid_x   = ix + iw // 2
        pygame.draw.line(surf, self.WALL, (mid_x, iy),     (mid_x, mid_y - 4), 3)
        pygame.draw.line(surf, self.WALL, (ix, mid_y - 2), (ix + iw, mid_y - 2), 3)
        lbl = self.fname.render("Casa", True, WHITE)
        surf.blit(lbl, (self.rect.centerx - lbl.get_width() // 2, self.rect.y + 4))
        pygame.draw.rect(surf, (100, 70, 40),
                         (self.rect.centerx - 7, self.rect.bottom - 18, 14, 18), border_radius=2)
        for r in self.rooms:
            r.draw(surf)


# ═══════════════════════════════════════════════════════════
#  FLY  (player)
# ═══════════════════════════════════════════════════════════
class Fly:
    SPEED  = 3.8
    RADIUS = 11

    def __init__(self, pos, controls: dict,
                 clean_color=(28, 28, 28), loaded_color=(100, 65, 15),
                 wing_color=None, eye_color=(180, 30, 30), label=""):
        self.pos          = Vector2(pos)
        self.vel          = Vector2(0, 0)
        self.loaded       = False
        self.alive        = True
        self.controls     = controls
        self.clean_color  = clean_color
        self.loaded_color = loaded_color
        self.wing_color   = wing_color or (190, 215, 255)
        self.eye_color    = eye_color
        self.label        = label
        self.wangle       = 0
        self.bob          = 0.0
        self.bob_d        = 1
        self.facing       = 1
        self.radius       = self.RADIUS
        self.flabel_font  = pygame.font.SysFont("Arial", 12, bold=True)

    def handle_input(self):
        keys = pygame.key.get_pressed()
        v = Vector2(0, 0)
        if keys[self.controls["left"]]:  v.x -= 1
        if keys[self.controls["right"]]: v.x += 1
        if keys[self.controls["up"]]:    v.y -= 1
        if keys[self.controls["down"]]:  v.y += 1
        if v.x > 0: self.facing =  1
        if v.x < 0: self.facing = -1
        self.vel = v.normalize() * self.SPEED if v.length() > 0 else Vector2(0, 0)

    def update(self):
        self.handle_input()
        self.pos += self.vel
        self.pos.x = max(self.radius, min(W - self.radius, self.pos.x))
        self.pos.y = max(self.radius, min(H - self.radius, self.pos.y))
        self.wangle = (self.wangle + 28) % 360
        self.bob += 0.12 * self.bob_d
        if abs(self.bob) > 2.2:
            self.bob_d *= -1

    def draw(self, surf):
        x   = int(self.pos.x)
        y   = int(self.pos.y + self.bob)
        col = self.loaded_color if self.loaded else self.clean_color
        wc  = self.wing_color
        ec  = self.eye_color

        # label acima
        lbl = self.flabel_font.render(self.label, True, WHITE)
        ls = pygame.Surface((lbl.get_width() + 6, lbl.get_height() + 2), pygame.SRCALPHA)
        ls.fill((0, 0, 0, 160))
        ls.blit(lbl, (3, 1))
        surf.blit(ls, (x - ls.get_width() // 2, y - 36))

        pygame.draw.ellipse(surf, (0, 0, 0), (x - 10, y + 11, 20, 7))
        w_off = int(math.sin(math.radians(self.wangle)) * 9)
        for ox in (-22, 2):
            ws = pygame.Surface((20, 12), pygame.SRCALPHA)
            pygame.draw.ellipse(ws, (*wc, 180), (0, 0, 20, 12))
            surf.blit(ws, (x + ox, y - 9 + w_off))
        pygame.draw.ellipse(surf, col, (x - 9, y - 5, 17, 11))
        pygame.draw.circle(surf, col, (x + 4 * self.facing, y - 2), 5)
        pygame.draw.circle(surf, col, (x + 8 * self.facing, y - 1), 4)
        pygame.draw.circle(surf, ec,  (x + 9 * self.facing, y - 3), 2)
        pygame.draw.circle(surf, ec,  (x + 9 * self.facing, y + 1), 2)
        for lx in (-5, 0, 5):
            pygame.draw.line(surf, col, (x + lx, y + 4), (x + lx - 6, y + 10), 1)
            pygame.draw.line(surf, col, (x + lx, y + 4), (x + lx + 6, y + 10), 1)
        if self.loaded:
            pygame.draw.circle(surf, POOP_MID,  (x, y - 20), 6)
            pygame.draw.circle(surf, POOP_DARK, (x, y - 20), 6, 1)


# ═══════════════════════════════════════════════════════════
#  POOP PILE
# ═══════════════════════════════════════════════════════════
class PoopPile:
    def __init__(self, pos, r=24):
        self.pos    = Vector2(pos)
        self.radius = r

    def draw(self, surf):
        x, y = int(self.pos.x), int(self.pos.y)
        s = self.radius / 24.0   # fator de escala

        # sombra no chão
        pygame.draw.ellipse(surf, (70, 48, 10),
                            (x - int(s*28), y + int(s*18), int(s*56), int(s*14)))

        # base: três montes grandes
        pygame.draw.circle(surf, POOP_DARK, (x,             y + int(s*6)),  int(s*17))
        pygame.draw.circle(surf, POOP_DARK, (x - int(s*9),  y + int(s*2)),  int(s*13))
        pygame.draw.circle(surf, POOP_DARK, (x + int(s*9),  y + int(s*2)),  int(s*13))
        # camadas do meio
        pygame.draw.circle(surf, POOP_MID,  (x,             y - int(s*4)),  int(s*11))
        pygame.draw.circle(surf, POOP_MID,  (x,             y - int(s*13)), int(s*8))
        # topo com brilho
        pygame.draw.circle(surf, POOP_LIGHT,(x - int(s*2),  y - int(s*4)),  int(s*5))
        pygame.draw.circle(surf, POOP_LIGHT,(x,             y - int(s*15)), int(s*3))

        # olhos estilo emoji
        ey = y - int(s * 7)
        for ex_off in (-int(s*3.5), int(s*3.5)):
            pygame.draw.circle(surf, WHITE, (x + ex_off, ey), max(2, int(s*3.5)))
            pygame.draw.circle(surf, BLACK, (x + ex_off, ey), max(1, int(s*1.8)))
            pygame.draw.circle(surf, WHITE, (x + ex_off - max(1,int(s)), ey - max(1,int(s))),
                               max(1, int(s*0.9)))

        # sorriso
        pygame.draw.arc(surf, BLACK,
                        (x - int(s*4.5), ey + int(s*2), int(s*9), int(s*4)),
                        math.pi, 2*math.pi, max(1, int(s*1.5)))

        # linhas de cheiro animadas
        t = pygame.time.get_ticks() / 600.0
        for i, ox_off in enumerate([-int(s*8), 0, int(s*8)]):
            phase = t + i * 1.3
            py0   = y - int(s*22)
            for seg in range(5):
                ly1 = py0 - seg * int(s*5)
                ly2 = ly1 - int(s*4)
                lx1 = x + ox_off + int(math.sin(phase + seg * 0.9) * s * 4)
                lx2 = x + ox_off + int(math.sin(phase + seg * 0.9 + 0.8) * s * 4)
                alpha = 160 - seg * 32
                if alpha > 0:
                    pygame.draw.line(surf, (130, 95, 28), (lx1, ly1), (lx2, ly2),
                                     max(1, int(s*1.4)))


# ═══════════════════════════════════════════════════════════
#  GAME
# ═══════════════════════════════════════════════════════════
class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption(TITLE)
        self.clock   = pygame.time.Clock()
        self.f_huge  = pygame.font.SysFont("Arial", 56, bold=True)
        self.f_large = pygame.font.SysFont("Arial", 34, bold=True)
        self.f_med   = pygame.font.SysFont("Arial", 22, bold=True)
        self.f_small = pygame.font.SysFont("Arial", 16)
        self.f_tiny  = pygame.font.SysFont("Arial", 13)
        self.high_score  = self._load_hs()
        self.mode        = "solo"   # "solo" | "duo"
        self.mode_cursor = 0        # 0=solo  1=duo
        self.state       = "mode_select"
        self._init_sounds()
        self._new_game()

    def _init_sounds(self):
        sr = 22050

        def make(samples):
            buf = bytearray(len(samples) * 2)
            for i, v in enumerate(samples):
                struct.pack_into('<h', buf, i * 2,
                                 max(-32768, min(32767, int(v * 32767))))
            return pygame.mixer.Sound(buffer=bytes(buf))

        # ── helpers ────────────────────────────────────────
        def bell(freq, dur=0.22, decay=0.09):
            n = int(sr * dur)
            return [(math.sin(2*math.pi*freq*i/sr)*0.7 +
                     math.sin(2*math.pi*freq*1.5*i/sr)*0.3) *
                    math.exp(-i/(sr*decay)) * 0.55 for i in range(n)]

        def pip(freq, dur=0.13, decay=0.05):
            n = int(sr * dur)
            return [math.sin(2*math.pi*freq*i/sr) *
                    math.exp(-i/(sr*decay)) * 0.50 for i in range(n)]

        def two_tone(f1, f2, dur=0.20, decay=0.07):
            n = int(sr * dur)
            mid = n // 2
            return [(math.sin(2*math.pi*(f1 if i < mid else f2)*i/sr) *
                     max(0.0, 1.0 - (i % mid)/(mid*0.7))) * 0.52
                    for i in range(n)]

        def double_beep(freq=800, dur=0.22):
            n   = int(sr * dur)
            gap = n // 3
            s   = []
            for i in range(n):
                seg = i % (gap + gap // 2)
                s.append(math.sin(2*math.pi*freq*i/sr) *
                         max(0.0, 1.0 - seg / (gap * 0.55)) * 0.50
                         if seg < gap else 0.0)
            return s

        def sizzle(dur=0.20, decay=0.09):
            n = int(sr * dur)
            return [random.uniform(-1, 1) *
                    math.exp(-i/(sr*decay)) * 0.52 for i in range(n)]

        # ── peido realista (phase accumulation) ────────────
        n_fart = int(sr * 0.58)
        fart   = []
        ph     = 0.0
        for i in range(n_fart):
            t    = i / sr
            prog = i / n_fart
            freq = 118 * math.exp(-prog * 0.95) + 46
            ph  += 2 * math.pi * freq / sr
            flutter = max(0.07,
                          abs(math.sin(2*math.pi*14*t)) *
                          abs(math.sin(2*math.pi*8.3*t + 0.6)))
            v = (math.sin(ph)       * 1.00 +
                 math.sin(ph * 2)   * 0.65 +
                 math.sin(ph * 3)   * 0.42 +
                 math.sin(ph * 4.8) * 0.15 +
                 random.uniform(-0.22, 0.22))
            v   /= 2.44
            env  = (prog / 0.04 if prog < 0.04
                    else max(0.0, (1.0 - prog) / 0.96))
            fart.append(v * flutter * env * 0.60)
        self.snd_poop = make(fart)

        # ── sons por estabelecimento ────────────────────────
        self.snd_score = {
            "Padaria":      make(bell(880,  0.22, 0.09)),   # sino de padaria
            "Restaurante":  make(sizzle(0.22, 0.10)),       # chiado de churrasco
            "Supermercado": make(two_tone(1200, 1500, 0.18, 0.05)),  # caixa registradora
            "Hospital":     make(pip(660,   0.13, 0.05)),   # bipe médico
            "Churrascaria": make(sizzle(0.28, 0.13)),       # grelha
            "Escola":       make(bell(700,  0.30, 0.15)),   # sino de escola
            "Lanchonete":   make(two_tone(500, 750, 0.20, 0.07)),  # jingle alegre
            "Farmácia":     make(double_beep(820, 0.22)),   # duplo bipe digital
            "quarto":       make(pip(523,   0.20, 0.12)),   # sino suave
            "sala":         make(two_tone(440, 550, 0.20, 0.07)),  # jingle de TV
            "cozinha":      make(bell(600,  0.18, 0.07)),   # ping de panela
        }

        # ── morte: glissando descendente + splat ───────────
        n_die = int(sr * 0.55)
        death = [
            math.sin(2*math.pi*(480 - 400*i/n_die)*i/sr) * 0.55 *
            max(0.0, 1.0 - i/n_die*1.1) +
            random.uniform(-0.12, 0.12) * max(0.0, 1.0 - i/n_die)
            for i in range(n_die)
        ]
        self.snd_die = make(death)

        # ── jingle de fase: fanfara ascendente (C-E-G-C) ───
        jingle = []
        for freq in [261, 329, 392, 523]:
            n_note = int(sr * 0.11)
            jingle += [
                math.sin(2*math.pi*freq*i/sr) * 0.5 *
                max(0.0, 1.0 - i / n_note * 0.6)
                for i in range(n_note)
            ]
        self.snd_phase = make(jingle)

    def _load_hs(self) -> int:
        try:
            HS_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(HS_PATH) as f:
                return json.loads(f.read()).get("hs", 0)
        except Exception:
            return 0

    def _save_hs(self):
        try:
            HS_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(HS_PATH, "w") as f:
                f.write(json.dumps({"hs": self.high_score}))
        except Exception:
            pass

    # ── game init ────────────────────────────────────────
    def _new_game(self):
        fly1 = Fly((85,  630), P1_KEYS,
                   P1_CLEAN, P1_LOADED,
                   eye_color=(180, 30, 30),
                   label="J1 — WASD" if self.mode == "duo" else "")
        if self.mode == "duo":
            fly2 = Fly((130, 610), P2_KEYS,
                       P2_CLEAN, P2_LOADED,
                       wing_color=P2_WING, eye_color=P2_EYE, label="J2 — Setas")
            self.flies = [fly1, fly2]
        else:
            self.flies = [fly1]
        self.score        = 0
        self.combo        = 0
        self.particles    = []
        self.flash        = 0
        self.shake        = 0
        self.freeze       = 0
        self.phase        = 1
        self.phase_score  = 0
        self.phase_banner = 0
        self.dead_label   = ""   # quem morreu
        self.death_insult = ""
        # estrelas fixas para cenas noturnas (fase 4+)
        self.phase_stars  = [(random.randint(0, W), random.randint(0, H - 230))
                              for _ in range(45)]

        self.poops = [PoopPile((105, H - 105), r=62)]

        # Layout: col1 x=200..470 | rua 85px | col2 x=555..785 | rua 100px | col3 x=885..1095
        self.house = House((200, 20, 270, 158))

        ldata = [
            # nome             tipo           pts  n   spd   det  (x,   y,   w,   h)
            ("Padaria",      "bakery",        5,   1,  0.75,  78, (555,  30, 175, 105)),
            ("Restaurante",  "restaurant",    7,   2,  1.05,  95, (885,  30, 180, 105)),
            ("Supermercado", "supermarket",  10,   3,  1.40, 112, (200, 238, 225, 112)),
            ("Hospital",     "hospital",     15,   4,  1.85, 122, (555, 238, 225, 112)),
            ("Churrascaria", "restaurant",    8,   2,  1.15,  98, (885, 238, 210, 112)),
            ("Escola",       "house",         4,   2,  0.65,  72, (200, 448, 170, 102)),
            ("Lanchonete",   "bakery",        6,   1,  0.90,  85, (555, 448, 170, 102)),
            ("Farmácia",     "hospital",      9,   2,  1.25, 105, (885, 448, 170, 102)),
        ]
        self.locations = [
            Location(rect, name, ltype, pts, nhum, spd, det)
            for name, ltype, pts, nhum, spd, det, rect in ldata
        ]

    # ── phase management ─────────────────────────────────
    def _advance_phase(self):
        self.phase_score  = max(0, self.phase_score - PHASE_POINTS)
        self.phase       += 1
        self.phase_banner = 210
        self.snd_phase.play()
        self._upgrade_difficulty()

    def _upgrade_difficulty(self):
        p           = self.phase
        speed_mult  = min(1.0 + (p - 1) * 0.18, 2.8)
        detect_mult = min(1.0 + (p - 1) * 0.10, 1.9)
        for idx, h in enumerate(self._all_humans()):
            h.speed       = h.base_speed  * speed_mult
            h.detect      = h.base_detect * detect_mult
            h.attack_type = self._assign_attack(p, h.tier, idx)

    def _assign_attack(self, phase: int, tier: int, idx: int) -> str:
        if phase == 1: return "hand"
        if phase == 2:
            if tier == 2: return "slipper"
            if tier == 1: return "slipper" if idx % 2 == 0 else "hand"
            return "hand"
        if phase == 3:
            if tier == 2: return ["hand", "slipper", "spray"][idx % 3]
            if tier == 1: return "slipper" if idx % 2 == 0 else "hand"
            return "spray" if idx % 4 == 0 else "hand"
        return ["hand", "slipper", "spray"][idx % 3]

    def _all_humans(self) -> list:
        h = []
        for loc in self.locations: h.extend(loc.humans)
        for r in self.house.rooms:  h.extend(r.humans)
        return h

    # ── score / death ────────────────────────────────────
    def _apply_score(self, base_pts: int, pos: Vector2, sound_key: str = ""):
        self.combo       += 1
        mult              = 1 + (self.combo - 1) * 0.5
        pts               = int(base_pts * mult)
        self.score       += pts
        self.phase_score += pts
        if self.score > self.high_score:
            self.high_score = self.score
        self.particles.append(Particle((pos.x, pos.y - 22), f"+{pts}", YELLOW, size=22))
        if self.combo >= 2:
            self.particles.append(Particle(
                (pos.x, pos.y - 46), f"COMBO ×{self.combo}!", (255, 130, 50), size=18))
        snd = self.snd_score.get(sound_key)
        if snd:
            snd.play()
        self.freeze = 4

    def _kill(self, fly: "Fly"):
        if fly.alive:
            fly.alive        = False
            self.dead_label  = fly.label.split("—")[0].strip() or "A MOSCA"
            self.death_insult = random.choice(DEATH_INSULTS)
            self.shake       = 8
            self.snd_die.play()
            self.state       = "game_over"
            self._save_hs()

    def _quit(self):
        self._save_hs()
        pygame.quit()
        sys.exit()

    # ── main loop ────────────────────────────────────────
    def run(self):
        while True:
            self._events()
            self._update()
            self._draw()
            self.clock.tick(FPS)

    def _events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self._quit()
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    if self.state == "playing":
                        self.state = "mode_select"
                    else:
                        self._quit()

                # ── tela de seleção de modo ──
                if self.state == "mode_select":
                    if ev.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_1, pygame.K_2):
                        self.mode_cursor = 1 - self.mode_cursor
                    if ev.key == pygame.K_1: self.mode_cursor = 0
                    if ev.key == pygame.K_2: self.mode_cursor = 1
                    if ev.key in (pygame.K_SPACE, pygame.K_RETURN):
                        self.mode  = "solo" if self.mode_cursor == 0 else "duo"
                        self.state = "playing"
                        self._new_game()

                # ── game over ──
                if self.state == "game_over":
                    if ev.key == pygame.K_SPACE:
                        self.state = "playing"
                        self._new_game()
                    if ev.key == pygame.K_m:
                        self.state = "mode_select"

    def _update(self):
        if self.state != "playing":
            return

        if self.freeze > 0:
            self.freeze -= 1
            for p in self.particles:
                p.update()
            self.particles = [p for p in self.particles if not p.dead]
            return

        self.flash        = max(0, self.flash - 1)
        self.phase_banner = max(0, self.phase_banner - 1)

        if self.phase_score >= PHASE_POINTS:
            self._advance_phase()

        alive_positions = [f.pos for f in self.flies if f.alive]

        # update human AI (perseguem a mosca mais próxima)
        self.house.update(alive_positions)
        for loc in self.locations:
            loc.update(alive_positions)

        for fly in self.flies:
            if not fly.alive:
                continue

            fly.update()

            # poop pickup
            if not fly.loaded:
                for p in self.poops:
                    if (fly.pos - p.pos).length() < p.radius + fly.radius:
                        fly.loaded = True
                        self.flash = 18
                        self.snd_poop.play()
                        for _ in range(3):
                            self.particles.append(DotParticle(
                                (fly.pos.x + random.uniform(-8, 8),
                                 fly.pos.y + random.uniform(-8, 8)),
                                POOP_MID, radius=random.randint(3, 5)))
                        break

            # house scoring
            pts, room_key = self.house.score_room(fly)
            if pts:
                self._apply_score(pts, fly.pos, room_key)

            # location scoring
            for loc in self.locations:
                if fly.loaded and loc.contains(fly):
                    self._apply_score(loc.points, fly.pos, loc.name)
                    fly.loaded = False

            # kill checks
            if self.house.check_kills(fly):
                self._kill(fly)
                break
            for loc in self.locations:
                for h in loc.humans:
                    if h.check_kill(fly):
                        self._kill(fly)
                        break
                if self.state == "game_over":
                    break

        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if not p.dead]

    # ── drawing ──────────────────────────────────────────
    def _draw(self):
        {
            "mode_select": self._draw_mode_select,
            "playing":     self._draw_playing,
            "game_over":   self._draw_gameover,
        }[self.state]()
        pygame.display.flip()

    def _draw_bg(self):
        bg, bg_dark = BG_PHASES.get(min(self.phase, 4), BG_PHASES[4])
        self.screen.fill(bg)
        for gx in range(0, W, 64):
            for gy in range(0, H, 64):
                if (gx // 64 + gy // 64) % 2 == 0:
                    pygame.draw.rect(self.screen, bg_dark, (gx, gy, 64, 64))
        if self.phase >= 4:
            for sx, sy in self.phase_stars:
                pygame.draw.circle(self.screen, (230, 230, 210), (sx, sy), 1)

    def _draw_roads(self):
        ASPH = (188, 190, 183)
        CURB = (152, 154, 146)
        MARK = (232, 212, 48)
        bx   = 195   # início horizontal (depois da zona do cocô)

        # ── Rua horizontal 1 (entre fileiras 1 e 2): y=178..238
        pygame.draw.rect(self.screen, ASPH, (bx, 178, W - bx, 60))
        pygame.draw.line(self.screen, CURB, (bx, 178), (W, 178), 3)
        pygame.draw.line(self.screen, CURB, (bx, 238), (W, 238), 3)
        for mx in range(bx + 20, W, 44):
            pygame.draw.rect(self.screen, MARK, (mx, 204, 26, 5))

        # ── Rua horizontal 2 (entre fileiras 2 e 3): y=350..448
        pygame.draw.rect(self.screen, ASPH, (bx, 350, W - bx, 98))
        pygame.draw.line(self.screen, CURB, (bx, 350), (W, 350), 3)
        pygame.draw.line(self.screen, CURB, (bx, 448), (W, 448), 3)
        for mx in range(bx + 20, W, 44):
            pygame.draw.rect(self.screen, MARK, (mx, 392, 26, 5))
            pygame.draw.rect(self.screen, MARK, (mx, 402, 26, 5))

        # ── Rua vertical A (entre colunas 1 e 2): x=470..555
        pygame.draw.rect(self.screen, ASPH, (470, 0, 85, H - 175))
        pygame.draw.line(self.screen, CURB, (470, 0), (470, H - 175), 3)
        pygame.draw.line(self.screen, CURB, (555, 0), (555, H - 175), 3)
        for my in range(10, H - 180, 44):
            pygame.draw.rect(self.screen, MARK, (507, my, 5, 26))

        # ── Rua vertical B (entre colunas 2 e 3): x=780..885
        pygame.draw.rect(self.screen, ASPH, (780, 0, 105, H - 175))
        pygame.draw.line(self.screen, CURB, (780, 0), (780, H - 175), 3)
        pygame.draw.line(self.screen, CURB, (885, 0), (885, H - 175), 3)
        for my in range(10, H - 180, 44):
            pygame.draw.rect(self.screen, MARK, (831, my, 5, 26))

    def _apply_shake(self):
        if self.shake <= 0:
            return
        self.shake -= 1
        ox = random.randint(-4, 4)
        oy = random.randint(-3, 3)
        if ox == 0 and oy == 0:
            return
        bg, _ = BG_PHASES.get(min(self.phase, 4), BG_PHASES[4])
        tmp = self.screen.copy()
        self.screen.fill(bg)
        self.screen.blit(tmp, (ox, oy))

    def _draw_playing(self):
        self._draw_bg()
        self._draw_roads()
        for p in self.poops:
            p.draw(self.screen)
        lbl = self.f_tiny.render("ZONA DO COCÔ", True, (200, 160, 70))
        self.screen.blit(lbl, (105 - lbl.get_width() // 2, H - 185))
        self.house.draw(self.screen)
        for loc in self.locations:
            loc.draw(self.screen)
        for fly in self.flies:
            if fly.alive:
                fly.draw(self.screen)
        for p in self.particles:
            p.draw(self.screen)
        self._draw_hud()
        if self.flash > 0:
            a  = int(160 * self.flash / 18)
            fl = pygame.Surface((W, H), pygame.SRCALPHA)
            fl.fill((120, 80, 20, a))
            self.screen.blit(fl, (0, 0))
            if self.flash > 12:
                msg = self.f_large.render("CONTAMINADA!", True, (255, 220, 80))
                self.screen.blit(msg, (W // 2 - msg.get_width() // 2, H // 2 - 20))
        if self.phase_banner > 0:
            self._draw_phase_banner()
        self._apply_shake()

    def _draw_hud(self):
        # score
        sc_txt = self.f_med.render(f"Pontos: {self.score}", True, WHITE)
        hs_txt = self.f_small.render(f"Recorde: {self.high_score}", True, YELLOW)
        box_w  = max(sc_txt.get_width(), hs_txt.get_width()) + 24
        pygame.draw.rect(self.screen, BLACK, (8, 8, box_w, 58), border_radius=8)
        pygame.draw.rect(self.screen, (50,50,50), (8, 8, box_w, 58), border_radius=8, width=2)
        self.screen.blit(sc_txt, (20, 14))
        self.screen.blit(hs_txt, (20, 42))

        # fase
        ph_colors = {1:(50,120,220), 2:(200,100,30), 3:(170,40,40)}
        ph_color  = ph_colors.get(self.phase, (130,20,160))
        ph_labels = {1:f"FASE {self.phase} — só as mãos",
                     2:f"FASE {self.phase} — chinelos no ar!",
                     3:f"FASE {self.phase} — mão+chinelo+spray!"}
        ph_label  = ph_labels.get(self.phase, f"FASE {self.phase} — CAOS TOTAL!")
        ph_surf   = self.f_tiny.render(ph_label, True, WHITE)
        bw        = ph_surf.get_width() + 16
        pygame.draw.rect(self.screen, ph_color, (8, 70, bw, 22), border_radius=6)
        self.screen.blit(ph_surf, (16, 73))
        prog = min(self.phase_score / PHASE_POINTS, 1.0)
        pygame.draw.rect(self.screen, (40,40,40), (8, 94, bw, 8), border_radius=4)
        if prog > 0:
            pygame.draw.rect(self.screen, ph_color, (8, 94, int(bw * prog), 8), border_radius=4)
        self.screen.blit(
            self.f_tiny.render(f"{self.phase_score}/{PHASE_POINTS}pts", True, (180,180,180)),
            (bw + 12, 93))

        if self.phase >= 3:
            for i, (txt, col) in enumerate([("● Mão",(220,50,50)),
                                             ("● Chinelo",(200,160,80)),
                                             ("● Spray",(60,200,80))]):
                t = self.f_tiny.render(txt, True, col)
                self.screen.blit(t, (W - t.get_width() - 12, 8 + i * 18))

        if self.combo >= 2:
            cb = self.f_med.render(f"COMBO ×{self.combo}", True, (255, 140, 40))
            pygame.draw.rect(self.screen, BLACK,
                             (W - cb.get_width() - 26, 60, cb.get_width() + 18, 34), border_radius=8)
            self.screen.blit(cb, (W - cb.get_width() - 17, 65))

        # status dos jogadores (barra inferior)
        fly_border = [P1_CLEAN, P2_CLEAN]
        for i, fly in enumerate(self.flies):
            if not fly.alive:
                st, col = "MORTA", RED
            elif fly.loaded:
                st, col = "CONTAMINADA — pouse na comida!", (220, 130, 40)
            else:
                st, col = "Vá ao COCÔ para se contaminar!", (100, 220, 100)
            prefix = f"J{i+1}: " if self.mode == "duo" else ""
            stxt   = self.f_small.render(prefix + st, True, col)
            if self.mode == "duo":
                ox = 10 + i * (W // 2)
            else:
                ox = W // 2 - stxt.get_width() // 2 - 8
            pygame.draw.rect(self.screen, BLACK,
                             (ox, H - 30, stxt.get_width() + 16, 26), border_radius=5)
            pygame.draw.rect(self.screen, fly_border[i],
                             (ox, H - 30, stxt.get_width() + 16, 26), border_radius=5, width=2)
            self.screen.blit(stxt, (ox + 8, H - 27))

    def _draw_phase_banner(self):
        t = self.phase_banner
        a = int(220 * (210-t)/30) if t > 180 else (int(220*t/30) if t < 30 else 220)
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, min(a, 160)))
        self.screen.blit(ov, (0, 0))
        banners = {
            2: ("FASE 2!", (255,120,30), "Os humanos começaram a jogar chinelos!", "Trabalhem em equipe!"),
            3: ("FASE 3!", (220,50,50),  "Três ameaças: mão, chinelo e SPRAY!",    "● Vermelho=mão  ● Bege=chinelo  ● Verde=spray"),
            4: ("FASE 4!", (170,30,200), "TODOS os tipos em TODOS os lugares!",    "Boa sorte — vão precisar!"),
        }
        tt, tc, l1, l2 = banners.get(self.phase,
            (f"FASE {self.phase}!", (140,0,180), "Dificuldade máxima!", "Sobrevivam se conseguirem!"))
        for txt, col, y in [(tt, tc, H//2-85), (l1, WHITE, H//2+5), (l2, (255,220,80), H//2+55)]:
            font  = self.f_huge if y < H//2 else (self.f_large if y == H//2+5 else self.f_med)
            surf  = font.render(txt, True, col)
            surf.set_alpha(a)
            self.screen.blit(surf, (W//2 - surf.get_width()//2, y))

    def _draw_mode_select(self):
        self.screen.fill((30, 50, 18))

        # título
        title = self.f_huge.render("FLY SHIT!", True, (185, 240, 90))
        self.screen.blit(title, (W//2 - title.get_width()//2, 38))
        sub = self.f_med.render("O jogo da mosca contaminante", True, (140, 190, 90))
        self.screen.blit(sub, (W//2 - sub.get_width()//2, 106))

        # cards de modo
        card_w, card_h = 380, 310
        card_y = 148
        cards = [
            {"label": "1 JOGADOR", "cx": W//2 - 210, "idx": 0,
             "fly_colors": [(P1_CLEAN, (180,30,30), (190,215,255))],
             "controls": ["WASD — mover"],
             "desc": ["Jogue sozinho", "contra os humanos"]},
            {"label": "2 JOGADORES", "cx": W//2 + 210, "idx": 1,
             "fly_colors": [(P1_CLEAN, (180,30,30), (190,215,255)),
                            (P2_CLEAN, P2_EYE,     P2_WING)],
             "controls": ["J1: WASD", "J2: ↑↓←→"],
             "desc": ["Cooperativo —", "1 morreu = fim!"]},
        ]
        for card in cards:
            cx    = card["cx"]
            rect  = pygame.Rect(cx - card_w//2, card_y, card_w, card_h)
            sel   = self.mode_cursor == card["idx"]
            bg    = (55, 80, 35) if sel else (38, 55, 22)
            bord  = (140, 210, 80) if sel else (70, 100, 45)
            bw    = 4 if sel else 2
            pygame.draw.rect(self.screen, bg,   rect, border_radius=14)
            pygame.draw.rect(self.screen, bord, rect, border_radius=14, width=bw)

            # label do card
            lbl_col = (220, 255, 120) if sel else (160, 200, 100)
            lbl = self.f_large.render(card["label"], True, lbl_col)
            self.screen.blit(lbl, (cx - lbl.get_width()//2, card_y + 16))

            # mini flies desenhadas à mão
            fly_y = card_y + 80
            n = len(card["fly_colors"])
            for fi, (fc, ec, wc) in enumerate(card["fly_colors"]):
                fx = cx + (fi - (n-1)/2) * 55
                self._draw_mini_fly(int(fx), fly_y, fc, ec, wc)

            # controles
            for i, ctrl in enumerate(card["controls"]):
                ct = self.f_small.render(ctrl, True, (200, 230, 160))
                self.screen.blit(ct, (cx - ct.get_width()//2, card_y + 148 + i * 26))

            # descrição
            for i, d in enumerate(card["desc"]):
                dt = self.f_small.render(d, True, (160, 190, 130))
                self.screen.blit(dt, (cx - dt.get_width()//2, card_y + 218 + i * 26))

            # ✓ se selecionado
            if sel:
                ck = self.f_large.render("✓ SELECIONADO", True, (140, 230, 100))
                self.screen.blit(ck, (cx - ck.get_width()//2, card_y + card_h - 38))

        # instrução de navegação
        nav = self.f_small.render("← → ou  1 / 2  para escolher", True, (160, 200, 130))
        self.screen.blit(nav, (W//2 - nav.get_width()//2, card_y + card_h + 18))

        # fases (coluna central-inferior)
        phase_y = card_y + card_h + 50
        ph_lines = [
            ("Fase 1", "— só as mãos"),
            ("Fase 2", "— chinelos"),
            ("Fase 3", "— mão + chinelo + spray"),
            ("Fase 4+","— tudo + mais rápido"),
        ]
        for i, (k, v) in enumerate(ph_lines):
            kt = self.f_tiny.render(k, True, YELLOW)
            vt = self.f_tiny.render(v, True, (170, 210, 140))
            bx = W//2 - 170
            self.screen.blit(kt, (bx, phase_y + i * 22))
            self.screen.blit(vt, (bx + 70, phase_y + i * 22))

        if self.high_score > 0:
            hs = self.f_med.render(f"Recorde: {self.high_score}", True, YELLOW)
            self.screen.blit(hs, (W//2 - hs.get_width()//2, phase_y + 100))

        blink = int(pygame.time.get_ticks() / 600) % 2
        if blink:
            st = self.f_large.render("ESPAÇO / ENTER para jogar", True, WHITE)
            self.screen.blit(st, (W//2 - st.get_width()//2, phase_y + 132))

    def _draw_mini_fly(self, x, y, body_col, eye_col, wing_col):
        """Desenha uma versão pequena da mosca para o card de seleção."""
        s = pygame.Surface((52, 32), pygame.SRCALPHA)
        # asa esquerda
        pygame.draw.ellipse(s, (*wing_col, 160), (0, 4, 18, 10))
        # asa direita
        pygame.draw.ellipse(s, (*wing_col, 160), (34, 4, 18, 10))
        # corpo
        pygame.draw.ellipse(s, body_col, (14, 8, 18, 10))
        # cabeça
        pygame.draw.circle(s, body_col, (36, 12), 6)
        # olhos
        pygame.draw.circle(s, eye_col, (38, 10), 2)
        pygame.draw.circle(s, eye_col, (38, 14), 2)
        self.screen.blit(s, (x - 26, y - 16))

    def _draw_gameover(self):
        self._draw_playing()
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 170))
        self.screen.blit(ov, (0, 0))

        dead = self.f_huge.render(f"{self.dead_label} SE FODEU!", True, (230, 50, 50))
        self.screen.blit(dead, (W//2 - dead.get_width()//2, 140))
        ins = self.f_large.render(f'"{self.death_insult}"', True, (255, 130, 30))
        self.screen.blit(ins, (W//2 - ins.get_width()//2, 210))

        sc_label = "Pontuação da Dupla" if self.mode == "duo" else "Pontuação Final"
        sc = self.f_large.render(f"{sc_label}: {self.score}", True, WHITE)
        self.screen.blit(sc, (W//2 - sc.get_width()//2, 245))

        ph = self.f_med.render(f"Chegaram até a Fase {self.phase}", True, (180, 200, 255))
        self.screen.blit(ph, (W//2 - ph.get_width()//2, 293))

        if self.score > 0 and self.score >= self.high_score:
            hs = self.f_large.render("★  NOVO RECORDE!  ★", True, YELLOW)
            self.screen.blit(hs, (W//2 - hs.get_width()//2, 343))
        else:
            hs = self.f_med.render(f"Recorde: {self.high_score}", True, (210, 200, 90))
            self.screen.blit(hs, (W//2 - hs.get_width()//2, 343))

        r = self.f_large.render("ESPAÇO — jogar novamente", True, (140, 255, 140))
        self.screen.blit(r, (W//2 - r.get_width()//2, 415))
        m = self.f_med.render("M — escolher modo", True, (140, 200, 140))
        self.screen.blit(m, (W//2 - m.get_width()//2, 462))


# ═══════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    Game().run()
