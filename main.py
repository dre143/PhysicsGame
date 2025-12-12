import sys
import pygame as pg
from . import settings as S
from .game import Game

def main():
    pg.init()
    pg.display.set_caption("Gravity Flip Runner")
    screen=pg.display.set_mode((S.WIDTH,S.HEIGHT))
    pg.key.set_repeat()
    pg.event.set_grab(True)
    game=Game(screen)
    running=True
    while running:
        dt=game.clock.tick(S.FPS)/1000.0
        keys=pg.key.get_pressed()
        for e in pg.event.get():
            if e.type==pg.QUIT:
                running=False
            if e.type==pg.KEYUP:
                if e.key==pg.K_SPACE and not game.game_over:
                    game.flip()
                if e.key==pg.K_r and game.game_over:
                    game.reset()
            if e.type==pg.KEYDOWN:
                if e.key==pg.K_LSHIFT or e.key==pg.K_RSHIFT:
                    dir=-1 if keys[pg.K_a] and not keys[pg.K_d] else (1 if keys[pg.K_d] else (1 if game.player.vx>=0 else -1))
                    game.player.dash(dir)
        game.update(dt,keys)
        game.draw()
        pg.display.flip()
    pg.quit()
    return 0

if __name__=="__main__":
    sys.exit(main())
