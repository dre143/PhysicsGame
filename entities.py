import math
import random
import pygame as pg
from . import settings as S

class Player:
    def __init__(self,x,y):
        self.w=38
        self.h=54
        self.rect=pg.Rect(x,y,self.w,self.h)
        self.vx=0
        self.vy=0
        self.grav_dir=1
        self.grav_scale=1.0
        self.on_surface=False
        self.surface_friction=S.GROUND_FRICTION
        self.bounce_coef=S.BOUNCE_COEF
        self.flip_cooldown=0.25
        self.flip_timer=0
        self.extra_flips=0
        self.shield_charges=0
        self.slowmo=False
        self.slowmo_timer=0
        self.doubleflip_timer=0
        self.bounce_timer=0
        self.color=S.COLOR_PLAYER
        self.trail=[]
        self.dash_cd=0
        self.turbo_timer=0
        self.turbo=False

    def input(self,dt,keys):
        ax=0
        acc=S.PLAYER_ACC*(S.TURBO_ACC_SCALE if self.turbo else 1.0)
        vmax=S.PLAYER_MAX_VX*(S.TURBO_SPEED_SCALE if self.turbo else 1.0)
        if keys[pg.K_a]: ax-=acc
        if keys[pg.K_d]: ax+=acc
        self.vx+=ax*dt
        if abs(self.vx)>vmax:
            self.vx=vmax*(1 if self.vx>0 else -1)

    def apply_physics(self,dt):
        self.vy+=S.GRAVITY*self.grav_dir*self.grav_scale*dt
        if not self.on_surface:
            self.vx-=self.vx*S.AIR_DRAG
        if self.on_surface:
            f=self.surface_friction
            self.vx-=self.vx*f
            if abs(self.vx)<8: self.vx=0
        if self.vy> S.TERMINAL_VY: self.vy=S.TERMINAL_VY
        if self.vy< -S.TERMINAL_VY: self.vy=-S.TERMINAL_VY
        self.rect.x+=int(self.vx*dt)
        self.rect.y+=int(self.vy*dt)
        if self.flip_timer>0: self.flip_timer-=dt
        if self.slowmo_timer>0:
            self.slowmo_timer-=dt
            if self.slowmo_timer<=0: self.slowmo=False
        if self.doubleflip_timer>0:
            self.doubleflip_timer-=dt
            if self.doubleflip_timer<=0: self.extra_flips=0
        if self.bounce_timer>0:
            self.bounce_timer-=dt
        if self.turbo_timer>0:
            self.turbo_timer-=dt
            if self.turbo_timer<=0: self.turbo=False
        self.trail.append(self.rect.center)
        if len(self.trail)>S.TRAIL_LENGTH:
            self.trail.pop(0)
        if self.dash_cd>0:
            self.dash_cd-=dt

    def flip_gravity(self):
        if self.flip_timer>0: 
            if self.extra_flips>0:
                self.extra_flips-=1
            else:
                return False
        self.grav_dir*=-1
        self.vy*=-0.6
        self.on_surface=False
        self.flip_timer=self.flip_cooldown
        return True

    def dash(self,dir):
        if self.dash_cd>0: return False
        self.vx+=dir*S.DASH_SPEED
        self.dash_cd=S.DASH_COOLDOWN
        return True

    def grant_shield(self):
        self.shield_charges=1

    def grant_slowmo(self):
        self.slowmo=True
        self.slowmo_timer=S.SLOW_MO_DURATION

    def grant_bounce(self):
        self.bounce_timer=6.0
        self.bounce_coef=0.9

    def grant_doubleflip(self):
        self.doubleflip_timer=S.DOUBLE_FLIP_DURATION
        self.extra_flips=1
    def grant_turbo(self):
        self.turbo=True
        self.turbo_timer=S.TURBO_DURATION

    def draw(self,screen):
        for i,p in enumerate(self.trail):
            a=int(180*(i/len(self.trail))) if self.trail else 0
            r=4+int(6*(i/len(self.trail)))
            s=pg.Surface((r*2,r*2),pg.SRCALPHA)
            tc=(255,220,120,a) if not self.turbo else (255,140,40,a)
            pg.draw.circle(s,tc,(r,r),r)
            screen.blit(s,(p[0]-r,p[1]-r))
        sh=pg.Surface((self.rect.w+20,self.rect.h//3),pg.SRCALPHA)
        pg.draw.ellipse(sh,(0,0,0,60),(0,0,sh.get_width(),sh.get_height()))
        if self.grav_dir>0:
            screen.blit(sh,(self.rect.centerx-sh.get_width()//2,self.rect.bottom-8))
        else:
            screen.blit(sh,(self.rect.centerx-sh.get_width()//2,self.rect.top- sh.get_height()+8))
        pg.draw.rect(screen,(20,20,20),self.rect.inflate(6,6),border_radius=9)
        c=self.color if not self.turbo else S.COLOR_TURBO
        pg.draw.rect(screen,c,self.rect,border_radius=8)
        if self.shield_charges>0:
            pg.draw.rect(screen,(120,220,255),self.rect.inflate(10,10),2,border_radius=10)

class Particle:
    def __init__(self,x,y,color,life=0.6,vx=0,vy=0,rad=3):
        self.x=x; self.y=y
        self.vx=vx; self.vy=vy
        self.color=color
        self.life=life
        self.rad=rad
    def update(self,dt):
        self.life-=dt
        self.x+=self.vx*dt
        self.y+=self.vy*dt
        self.vy+=200*dt
    def draw(self,screen):
        if self.life<=0: return
        a=int(255*max(self.life,0))
        pg.draw.circle(screen,(*self.color[:3],a),(int(self.x),int(self.y)),self.rad)

class Platform:
    def __init__(self,x,y,w,h,ice=False,bounce=False,move=None,conveyor_vx=0):
        self.rect=pg.Rect(x,y,w,h)
        self.ice=ice
        self.bounce=bounce
        self.move=move
        self.base_y=y
        self.base_x=x
        self.t=0
        self.conveyor_vx=conveyor_vx
    def update(self,dt):
        if self.move:
            amp=self.move.get('amp',50)
            spd=self.move.get('spd',1)
            axis=self.move.get('axis','y')
            self.t+=dt*spd
            off=int(math.sin(self.t)*amp)
            if axis=='y':
                self.rect.y=self.base_y+off
            else:
                self.rect.x=self.base_x+off
    def draw(self,screen):
        c=S.COLOR_ICE if self.ice else S.COLOR_PLATFORM
        pg.draw.rect(screen,c,self.rect)

class Spike:
    def __init__(self,x,y,w,h,top=True):
        self.rect=pg.Rect(x,y,w,h)
        self.top=top
    def update(self,dt):
        pass
    def draw(self,screen):
        c=S.COLOR_SPIKE
        w=self.rect.w//10
        for i in range(10):
            bx=self.rect.x+i*w
            if self.top:
                pts=[(bx,self.rect.bottom),(bx+w//2,self.rect.top),(bx+w,self.rect.bottom)]
            else:
                pts=[(bx,self.rect.top),(bx+w//2,self.rect.bottom),(bx+w,self.rect.top)]
            pg.draw.polygon(screen,c,pts)

class Pendulum:
    def __init__(self,ax,ay,len_pix=160,rad=18,spd=1.0):
        self.ax=ax
        self.ay=ay
        self.len=len_pix
        self.rad=rad
        self.t=0
        self.spd=spd
        self.pos=(ax,ay+len_pix)
        self.rect=pg.Rect(0,0,rad*2,rad*2)
    def update(self,dt):
        self.t+=dt*self.spd
        ang=math.sin(self.t)*0.9
        x=self.ax+math.sin(ang)*self.len
        y=self.ay+math.cos(ang)*self.len
        self.pos=(int(x),int(y))
        self.rect.center=self.pos
    def draw(self,screen):
        pg.draw.line(screen,(200,200,200),(self.ax,self.ay),self.pos,2)
        pg.draw.circle(screen,S.COLOR_PENDULUM,self.pos,self.rad)

class Bomb:
    def __init__(self,x,y):
        self.rect=pg.Rect(x,y,20,20)
        self.vy=120
    def update(self,dt):
        self.rect.y+=int(self.vy*dt)
    def draw(self,screen):
        pg.draw.circle(screen,S.COLOR_BOMB,self.rect.center,10)

class PowerUp:
    def __init__(self,x,y,kind):
        self.rect=pg.Rect(x,y,24,24)
        self.kind=kind
        self.alive=True
    def update(self,dt):
        pass
    def draw(self,screen):
        pg.draw.rect(screen,S.COLOR_POWERUP,self.rect,border_radius=6)
        f=pg.font.SysFont(S.FONT_NAME,16)
        txt={'shield':'S','slow':'T','bounce':'B','dflip':'D','turbo':'T+'}[self.kind]
        im=f.render(txt,True,(30,40,40))
        r=im.get_rect(center=self.rect.center)
        screen.blit(im,r)

class Saw:
    def __init__(self,x,y,rad=18,spd=180,amp=60):
        self.rad=rad
        self.center=[x,y]
        self.rect=pg.Rect(0,0,rad*2,rad*2)
        self.rect.center=self.center
        self.spd=spd
        self.amp=amp
        self.t=0
    def update(self,dt):
        self.t+=dt
        self.center[0]+=int(math.cos(self.t)*self.spd*dt)
        self.center[1]+=int(math.sin(self.t*1.6)*0)
        self.rect.center=self.center
    def draw(self,screen):
        pg.draw.circle(screen,(230,230,230),self.rect.center,self.rad)
        for i in range(8):
            ang=i*math.pi/4
            x=self.rect.centerx+int(math.cos(ang)*self.rad)
            y=self.rect.centery+int(math.sin(ang)*self.rad)
            pg.draw.line(screen,(180,180,180),self.rect.center,(x,y),2)

class LaserGate:
    def __init__(self,x,y,h=180,period=2.2):
        self.rect=pg.Rect(x,y,12,h)
        self.period=period
        self.t=0
        self.active=True
    def update(self,dt):
        self.t+=dt
        self.active=(self.t%self.period)<(self.period*0.6)
    def draw(self,screen):
        c=(255,60,60) if self.active else (120,40,40)
        pg.draw.rect(screen,c,self.rect)

class Slope:
    def __init__(self,x1,y1,x2,y2,thickness=16):
        self.x1,self.y1,self.x2,self.y2=x1,y1,x2,y2
        minx=min(x1,x2); maxx=max(x1,x2)
        miny=min(y1,y2); maxy=max(y1,y2)
        self.rect=pg.Rect(minx,miny,maxx-minx,maxy-miny+thickness)
        self.thickness=thickness
    def y_at(self,x):
        if self.x2==self.x1: return self.y1
        t=(x-self.x1)/(self.x2-self.x1)
        return int(self.y1+t*(self.y2-self.y1))
    def update(self,dt):
        pass
    def draw(self,screen):
        pg.draw.line(screen,S.COLOR_SLOPE,(self.x1,self.y1),(self.x2,self.y2),self.thickness)

class WindZone:
    def __init__(self,x,y,w,h,wind_vx=180):
        self.rect=pg.Rect(x,y,w,h)
        self.wind_vx=wind_vx
    def update(self,dt):
        pass
    def draw(self,screen):
        pg.draw.rect(screen,S.COLOR_WIND,self.rect,2)

class GravityZone:
    def __init__(self,x,y,w,h,scale=0.6):
        self.rect=pg.Rect(x,y,w,h)
        self.scale=scale
    def update(self,dt):
        pass
    def draw(self,screen):
        pg.draw.rect(screen,S.COLOR_GRAV_ZONE,self.rect,2)

class Wall:
    def __init__(self,x,y,h,width=16):
        self.rect=pg.Rect(x,y,width,h)
    def update(self,dt):
        pass
    def draw(self,screen):
        pg.draw.rect(screen,(160,160,200),self.rect)

class Crate:
    def __init__(self,x,y,w=40,h=40):
        self.rect=pg.Rect(x,y,w,h)
        self.vx=0
        self.vy=0
        self.on_surface=False
    def update(self,dt):
        self.vy+=S.GRAVITY*dt
        if self.on_surface:
            self.vx-=self.vx*S.GROUND_FRICTION
        self.rect.x+=int(self.vx*dt)
        self.rect.y+=int(self.vy*dt)
        self.on_surface=False
    def draw(self,screen):
        pg.draw.rect(screen,S.COLOR_CRATE,self.rect)

class Springboard:
    def __init__(self,x,y,w=80,h=18):
        self.rect=pg.Rect(x,y,w,h)
    def update(self,dt):
        pass
    def draw(self,screen):
        pg.draw.rect(screen,S.COLOR_SPRING,self.rect)

class GravityWell:
    def __init__(self,x,y,r=120,sign=1):
        self.x=x; self.y=y; self.r=r; self.sign=sign
        self.rect=pg.Rect(x-r,y-r,r*2,r*2)
    def update(self,dt):
        pass
    def draw(self,screen):
        pg.draw.circle(screen,S.COLOR_WELL,(self.x,self.y),self.r,2)
        pg.draw.circle(screen,S.COLOR_WELL,(self.x,self.y),int(self.r*0.6),1)
        pg.draw.circle(screen,S.COLOR_WELL,(self.x,self.y),int(self.r*0.3),1)

class LiquidZone:
    def __init__(self,x,y,w,h):
        self.rect=pg.Rect(x,y,w,h)
    def update(self,dt):
        pass
    def draw(self,screen):
        pg.draw.rect(screen,S.COLOR_WATER,self.rect)

class Bullet:
    def __init__(self,x,y,vx,vy=0):
        self.rect=pg.Rect(x,y,10,10)
        self.vx=vx
        self.vy=vy
        self.alive=True
    def update(self,dt):
        self.rect.x+=int(self.vx*dt)
        self.rect.y+=int(self.vy*dt)
    def draw(self,screen):
        pg.draw.rect(screen,(255,80,80),self.rect)

class Turret:
    def __init__(self,x,y,period=1.2,speed=420):
        self.rect=pg.Rect(x,y,28,28)
        self.t=0
        self.period=period
        self.speed=speed
    def update(self,dt):
        self.t+=dt
    def can_fire(self):
        return self.t>=self.period
    def fire(self):
        self.t=0
        return Bullet(self.rect.centerx,self.rect.centery,-self.speed,0)
    def draw(self,screen):
        pg.draw.rect(screen,(220,120,120),self.rect)

class Drone:
    def __init__(self,x,y):
        self.rect=pg.Rect(x,y,24,24)
        self.vx=-120
        self.vy=0
        self.acc=220
    def update(self,dt,player=None):
        if player:
            dy=player.rect.centery-self.rect.centery
            self.vy+=max(-self.acc,min(self.acc,dy*0.6))*dt
            self.vy=max(-200,min(200,self.vy))
        self.rect.x+=int(self.vx*dt)
        self.rect.y+=int(self.vy*dt)
    def draw(self,screen):
        pg.draw.rect(screen,(255,180,90),self.rect,border_radius=6)

class Crusher:
    def __init__(self,x,top=True,range_h=260,spd=520,width=36):
        self.top=top
        y=0 if top else S.HEIGHT-range_h
        self.rect=pg.Rect(x,y,width,range_h)
        self.spd=spd
        self.dir=1
    def update(self,dt):
        dy=int(self.spd*self.dir*dt)
        self.rect.y+= dy if self.top else -dy
        if self.top and (self.rect.y<0 or self.rect.bottom> S.HEIGHT//2): self.dir*=-1
        if not self.top and (self.rect.bottom> S.HEIGHT or self.rect.top< S.HEIGHT//2): self.dir*=-1
    def draw(self,screen):
        pg.draw.rect(screen,(200,100,200),self.rect)

class PopSpike:
    def __init__(self,x,y,w=120,h=26,period=1.3,up=True):
        self.rect=pg.Rect(x,y,w,h)
        self.period=period
        self.t=0
        self.active=False
        self.up=up
    def update(self,dt):
        self.t+=dt
        self.active=(self.t%self.period)>(self.period*0.4)
    def draw(self,screen):
        c=S.COLOR_SPIKE
        if not self.active:
            pg.draw.rect(screen,(120,60,60),self.rect)
            return
        w=self.rect.w//10
        for i in range(10):
            bx=self.rect.x+i*w
            if self.up:
                pts=[(bx,self.rect.bottom),(bx+w//2,self.rect.top),(bx+w,self.rect.bottom)]
            else:
                pts=[(bx,self.rect.top),(bx+w//2,self.rect.bottom),(bx+w,self.rect.top)]
            pg.draw.polygon(screen,c,pts)

class FallingPlatform:
    def __init__(self,x,y,w,h):
        self.rect=pg.Rect(x,y,w,h)
        self.triggered=False
        self.vy=0
    def update(self,dt):
        if self.triggered:
            self.vy+=S.GRAVITY*dt
            self.rect.y+=int(self.vy*dt)
    def draw(self,screen):
        pg.draw.rect(screen,(200,200,120),self.rect)
