import random
import math
import pygame as pg
from . import settings as S
from .entities import Player, Platform, Spike, Pendulum, Bomb, PowerUp, Saw, LaserGate, Particle
from .level import Level

class Game:
    def __init__(self,screen):
        self.screen=screen
        self.clock=pg.time.Clock()
        self.font=pg.font.SysFont(S.FONT_NAME,22)
        self.bigfont=pg.font.SysFont(S.FONT_NAME,48)
        self.reset()

    def reset(self):
        self.level=Level()
        self.player=Player(320,S.HEIGHT-180)
        self.lives=3
        self.score=0
        self.game_over=False
        self.time_scale=1.0
        self.flash_timer=0
        self.shake_timer=0
        self.bg=self.make_bg()
        self.particles=[]
        self.theme_index=0
        self.themes=[
            {'name':'Desert','bg_top':(60,48,28),'bg_bottom':(20,16,10),'parallax':[(40,32,20),(90,70,40),(140,110,70)]},
            {'name':'Factory','bg_top':(40,44,54),'bg_bottom':(12,14,18),'parallax':[(30,34,42),(60,70,90),(90,110,140)]},
            {'name':'Ocean','bg_top':(28,48,72),'bg_bottom':(10,18,28),'parallax':[(20,40,60),(40,70,110),(70,110,160)]},
        ]
        self.apply_theme(0,initial=True)
        self.milestone_shown=False
        self.milestone_timer=0
        self.font=self.choose_font(S.UI_FONTS,22)
        self.bigfont=self.choose_font(S.DISPLAY_FONTS,48)
        self.bannerfont=self.choose_font(S.DISPLAY_FONTS,72)
        self.gwfont=self.choose_font(['arialblack','poppins','bahnschrift','segoeui','verdana','arial'],84)
        self.turbo_banner_timer=0
        self.shield_banner_timer=0

    def update(self,dt,keys):
        if self.game_over: return
        ts= self.player.slowmo and S.SLOW_MO_SCALE or 1.0
        dt*=ts
        self.player.input(dt,keys)
        self.level.update(dt)
        for t in getattr(self.level,'turrets',[]):
            if t.can_fire():
                b=t.fire()
                if not hasattr(self.level,'bullets'): self.level.bullets=[]
                self.level.bullets.append(b)
        for d in getattr(self.level,'drones',[]):
            d.update(dt,self.player)
        for c in getattr(self.level,'crates',[]):
            c.update(dt)
        self.handle_collisions(dt)
        self.player.apply_physics(dt)
        self.update_particles(dt)
        self.score+=S.SCROLL_SPEED*dt*0.1
        new_index=int(self.score//1000)%len(self.themes)
        if new_index!=self.theme_index:
            self.apply_theme(new_index)
        if not self.milestone_shown and self.score>=2000:
            self.milestone_shown=True
            self.milestone_timer=4.0
        if self.player.rect.top> S.HEIGHT+80 or self.player.rect.bottom< -80:
            self.hit()

    def handle_collisions(self,dt):
        self.player.on_surface=False
        self.player.surface_friction=S.GROUND_FRICTION
        self.player.grav_scale=1.0
        for p in self.level.platforms:
            if self.player.rect.colliderect(p.rect):
                if self.player.grav_dir>0:
                    self.player.rect.bottom=p.rect.top
                    self.player.vy= -abs(self.player.vy)* (p.bounce and self.player.bounce_coef or 0)
                else:
                    self.player.rect.top=p.rect.bottom
                    self.player.vy= abs(self.player.vy)* (p.bounce and self.player.bounce_coef or 0)
                self.player.on_surface=True
                self.player.surface_friction= S.ICE_FRICTION if p.ice else S.GROUND_FRICTION
                if getattr(p,'conveyor_vx',0)!=0:
                    self.player.vx+=p.conveyor_vx*dt
        for s in getattr(self.level,'springs',[]):
            if self.player.rect.colliderect(s.rect):
                sp=abs(self.player.vy)
                self.player.vy= -self.player.grav_dir* max(380, sp*S.SPRING_COEF)
                self.spawn_particles(self.player.rect.centerx,self.player.rect.bottom if self.player.grav_dir>0 else self.player.rect.top,(255,220,120),count=20,speed=240)
        for fp in getattr(self.level,'falls',[]):
            if self.player.rect.colliderect(fp.rect):
                if self.player.grav_dir>0:
                    self.player.rect.bottom=fp.rect.top
                    self.player.vy=0
                else:
                    self.player.rect.top=fp.rect.bottom
                    self.player.vy=0
                self.player.on_surface=True
                fp.triggered=True
        for sl in getattr(self.level,'slopes',[]):
            if self.player.rect.colliderect(sl.rect):
                x=self.player.rect.centerx
                ys=sl.y_at(x)
                if self.player.grav_dir>0:
                    if self.player.rect.bottom>=ys and self.player.vy>0:
                        self.player.rect.bottom=ys
                        self.player.vy=0
                        self.player.on_surface=True
                else:
                    if self.player.rect.top<=ys and self.player.vy<0:
                        self.player.rect.top=ys
                        self.player.vy=0
                        self.player.on_surface=True
        for s in self.level.spikes:
            if self.player.rect.colliderect(s.rect):
                self.hazard()
        for b in self.level.bombs:
            if self.player.rect.colliderect(b.rect):
                self.hazard()
        for pend in self.level.pendulums:
            if self.player.rect.colliderect(pend.rect):
                self.hazard()
        for saw in self.level.saws:
            if self.player.rect.colliderect(saw.rect):
                self.hazard()
        for l in self.level.lasers:
            if l.active and self.player.rect.colliderect(l.rect):
                self.hazard()
        for ps in getattr(self.level,'popspikes',[]):
            if ps.active and self.player.rect.colliderect(ps.rect):
                self.hazard()
        for b in getattr(self.level,'bullets',[]):
            if self.player.rect.colliderect(b.rect):
                b.alive=False
                self.hazard()
        for d in getattr(self.level,'drones',[]):
            if self.player.rect.colliderect(d.rect):
                self.hazard()
        for c in getattr(self.level,'crushers',[]):
            if self.player.rect.colliderect(c.rect):
                self.hazard()
        for w in getattr(self.level,'winds',[]):
            if self.player.rect.colliderect(w.rect):
                self.player.vx+=w.wind_vx*dt
        in_grav=False
        for g in getattr(self.level,'gravzones',[]):
            if self.player.rect.colliderect(g.rect):
                self.player.grav_scale=g.scale
                in_grav=True
        if not in_grav:
            self.player.grav_scale=1.0
        for wl in getattr(self.level,'walls',[]):
            if self.player.rect.colliderect(wl.rect):
                if self.player.vx>0:
                    self.player.rect.right=wl.rect.left
                elif self.player.vx<0:
                    self.player.rect.left=wl.rect.right
                self.player.vx=0
        for cr in getattr(self.level,'crates',[]):
            if self.player.rect.colliderect(cr.rect):
                if self.player.vx>0:
                    self.player.rect.right=cr.rect.left
                    cr.vx+= self.player.vx*0.6
                elif self.player.vx<0:
                    self.player.rect.left=cr.rect.right
                    cr.vx+= self.player.vx*0.6
                self.player.vx*=0.6
                if self.player.grav_dir>0 and self.player.vy>0 and self.player.rect.bottom<=cr.rect.centery:
                    self.player.rect.bottom=cr.rect.top
                    self.player.vy=0
                    self.player.on_surface=True
                if self.player.grav_dir<0 and self.player.vy<0 and self.player.rect.top>=cr.rect.centery:
                    self.player.rect.top=cr.rect.bottom
                    self.player.vy=0
                    self.player.on_surface=True
        for well in getattr(self.level,'wells',[]):
            dx=well.x-self.player.rect.centerx
            dy=well.y-self.player.rect.centery
            dist=max(1,(dx*dx+dy*dy)**0.5)
            if dist<well.r:
                ax= well.sign* S.WELL_STRENGTH* dx/(dist*dist)
                ay= well.sign* S.WELL_STRENGTH* dy/(dist*dist)
                self.player.vx+=ax*dt
                self.player.vy+=ay*dt
        for lq in getattr(self.level,'liquids',[]):
            if self.player.rect.colliderect(lq.rect):
                self.player.grav_scale=S.LIQUID_GRAV_SCALE
                self.player.vx-= self.player.vx* S.LIQUID_DRAG
        for pu in self.level.powerups:
            if pu.alive and self.player.rect.colliderect(pu.rect):
                pu.alive=False
                self.score+=100
                if pu.kind=='shield': 
                    self.player.grant_shield()
                    self.shield_banner_timer=2.5
                if pu.kind=='slow': self.player.grant_slowmo()
                if pu.kind=='bounce': self.player.grant_bounce()
                if pu.kind=='dflip': self.player.grant_doubleflip()
                if pu.kind=='turbo': 
                    self.player.grant_turbo()
                    self.turbo_banner_timer=2.5

    def hazard(self):
        if self.player.shield_charges>0:
            self.player.shield_charges-=1
            self.flash_timer=0.4
            self.shake_timer=S.SHAKE_TIME
            self.spawn_particles(self.player.rect.centerx,self.player.rect.centery,(255,80,80),count=20,speed=280)
            return
        self.hit()

    def hit(self):
        self.lives-=1
        self.flash_timer=0.6
        self.shake_timer=S.SHAKE_TIME
        self.spawn_particles(self.player.rect.centerx,self.player.rect.centery,(255,120,120),count=40,speed=320)
        if self.lives<=0:
            self.game_over=True
        else:
            self.player.rect.y=S.HEIGHT//2
            self.player.vx=0
            self.player.vy=0

    def flip(self):
        ok=self.player.flip_gravity()
        if ok:
            self.spawn_particles(self.player.rect.centerx,self.player.rect.centery,(255,230,120),count=30,speed=220)
        return ok

    def draw(self):
        offx=offy=0
        if self.shake_timer>0:
            self.shake_timer-=1/ S.FPS
            offx=random.randint(-S.SHAKE_AMPL,S.SHAKE_AMPL)
            offy=random.randint(-S.SHAKE_AMPL,S.SHAKE_AMPL)
        self.screen.blit(self.bg,(0,0))
        self.draw_parallax(offx)
        self.level.draw(self.screen)
        if self.milestone_timer>0:
            self.milestone_timer-=1/ S.FPS
            a=max(0,int(140*self.milestone_timer/4.0))
            text=self.bannerfont.render("KWATRO LANG MA'AM",True,(255,220,140))
            s=pg.Surface((text.get_width()+40,text.get_height()+20),pg.SRCALPHA)
            s.fill((0,0,0,a))
            self.screen.blit(s,(S.WIDTH//2 - s.get_width()//2,S.HEIGHT//2 - s.get_height()//2))
            r=text.get_rect(center=(S.WIDTH//2,S.HEIGHT//2))
            self.draw_text("KWATRO LANG MA'AM",self.bannerfont,(S.WIDTH//2,S.HEIGHT//2),(255,220,140),center=True)
        for p in self.particles: p.draw(self.screen)
        self.player.draw(self.screen)
        hud=f"Score {int(self.score)}   Lives {self.lives}   Grav {'Down' if self.player.grav_dir>0 else 'Up'}"
        self.draw_text(hud,self.font,(16,12),S.COLOR_TEXT)
        pu=[]
        if self.player.shield_charges>0: pu.append('Shield')
        if self.player.slowmo: pu.append('SlowMo')
        if self.player.bounce_timer>0: pu.append('Bounce')
        if self.player.doubleflip_timer>0: pu.append('DoubleFlip')
        im2=self.font.render("PowerUps: "+(", ".join(pu) if pu else "None"),True,S.COLOR_TEXT)
        self.screen.blit(im2,(16,40))
        if self.flash_timer>0:
            self.flash_timer-=1/ S.FPS
            overlay=pg.Surface((S.WIDTH,S.HEIGHT),pg.SRCALPHA)
            a=int(140*max(self.flash_timer,0))
            overlay.fill((255,80,80,a))
            self.screen.blit(overlay,(0,0))
        if self.game_over:
            self.draw_text("Game Over",self.bigfont,(S.WIDTH//2,S.HEIGHT//2-30),(255,200,200),center=True)
            self.draw_text("Press R to restart",self.font,(S.WIDTH//2,S.HEIGHT//2+20),S.COLOR_TEXT,center=True)
        if self.turbo_banner_timer>0:
            self.turbo_banner_timer-=1/ S.FPS
            a=max(0,int(160*self.turbo_banner_timer/2.5))
            self.draw_gw_text("CABEROY",(S.WIDTH//2,S.HEIGHT//3),a)
        if self.shield_banner_timer>0:
            self.shield_banner_timer-=1/ S.FPS
            a=max(0,int(160*self.shield_banner_timer/2.5))
            self.draw_gw_text("CABEROY",(S.WIDTH//2, S.HEIGHT*2//3),a)

    def make_bg(self):
        surf=pg.Surface((S.WIDTH,S.HEIGHT))
        top=getattr(self,'bg_top',S.BG_TOP); bot=getattr(self,'bg_bottom',S.BG_BOTTOM)
        for y in range(S.HEIGHT):
            t=y/S.HEIGHT
            c=(int(top[0]*(1-t)+bot[0]*t),int(top[1]*(1-t)+bot[1]*t),int(top[2]*(1-t)+bot[2]*t))
            pg.draw.line(surf,c,(0,y),(S.WIDTH,y))
        return surf

    def draw_parallax(self,offx=0):
        x=self.level.scroll_x
        cols=getattr(self,'parallax_colors',S.PARALLAX_COLORS)
        for i,col in enumerate(cols):
            sp=S.PARALLAX_SPEEDS[i]
            base=int((x*sp)/300)%S.WIDTH
            ybase= S.HEIGHT- (140-i*50)
            for k in range(-1,3):
                px= k*S.WIDTH - base + offx
                pg.draw.polygon(self.screen,col,[(px,ybase),(px+220,ybase-40),(px+440,ybase),(px+660,ybase-50),(px+880,ybase)])

    def apply_theme(self,index,initial=False):
        self.theme_index=index
        th=self.themes[index]
        self.bg_top=th['bg_top']
        self.bg_bottom=th['bg_bottom']
        self.parallax_colors=th['parallax']
        self.level.set_theme(th['name'])
        self.bg=self.make_bg()
        if not initial:
            self.flash_timer=0.5
            self.shake_timer=0.4
            self.spawn_particles(S.WIDTH//2,S.HEIGHT//2,(200,200,255),count=80,speed=280)

    def choose_font(self,names,size):
        available=set(pg.font.get_fonts())
        for nm in names:
            key=nm.replace(" ","").lower()
            if key in available:
                return pg.font.SysFont(key,size)
        return pg.font.SysFont(S.FONT_NAME,size)

    def draw_text(self,text,font,pos,color,center=False):
        im=font.render(text,True,color)
        r=im.get_rect()
        if center:
            r.center=pos
        else:
            r.topleft=pos
        shadow=pg.Surface((r.width+6,r.height+6),pg.SRCALPHA)
        shadow.fill(S.COLOR_TEXT_SHADOW)
        self.screen.blit(shadow,(r.x+3,r.y+3))
        outline_col=S.COLOR_TEXT_OUTLINE
        o=1
        base=font.render(text,True,outline_col)
        self.screen.blit(base,(r.x-o,r.y))
        self.screen.blit(base,(r.x+o,r.y))
        self.screen.blit(base,(r.x,r.y-o))
        self.screen.blit(base,(r.x,r.y+o))
        self.screen.blit(im,r)

    def draw_gw_text(self,text,center,alpha_val):
        t=self.level.t
        font=self.gwfont
        letters=list(text)
        mats=[]
        for ch in letters:
            surf=font.render(ch,True,(255,120,190))
            mats.append(surf)
        total=0
        scales=[]
        for i,sf in enumerate(mats):
            sc=1.0+0.06*math.sin(t*6+i*0.5)
            scales.append(sc)
            total+=int(sf.get_width()*sc)
        x0=center[0]-total//2
        y0=center[1]
        bg=pg.Surface((total+40,max(m.get_height() for m in mats)+30),pg.SRCALPHA)
        bg.fill((0,0,0,alpha_val))
        self.screen.blit(bg,(center[0]-bg.get_width()//2,center[1]-bg.get_height()//2))
        x=x0
        for i,sf in enumerate(mats):
            sc=scales[i]
            h=int(sf.get_height()*sc)
            w=int(sf.get_width()*sc)
            imp=pg.transform.smoothscale(sf,(w,h))
            yo=int(6*math.sin(t*5+i*0.6))
            r=imp.get_rect()
            r.center=(x+w//2,y0+yo)
            glow=pg.transform.smoothscale(imp,(int(w*1.2),int(h*1.2)))
            glow.set_alpha(120)
            gr=glow.get_rect(center=r.center)
            self.screen.blit(glow,gr.topleft)
            base_outline=font.render(letters[i],True,S.COLOR_TEXT_OUTLINE)
            out=pg.transform.smoothscale(base_outline,(w,h))
            orc=out.get_rect(center=r.center)
            self.screen.blit(out,(orc.x-2,orc.y))
            self.screen.blit(out,(orc.x+2,orc.y))
            self.screen.blit(out,(orc.x,orc.y-2))
            self.screen.blit(out,(orc.x,orc.y+2))
            self.screen.blit(imp,r.topleft)
            x+=w
        return pg.Rect(x0,y0-20,total,40)

    def draw_tulip(self,x,y,scale=1.0):
        s=max(0.6,scale)
        stem_h=int(36*s)
        stem_w=int(6*s)
        petal_r=int(10*s)
        leaf_w=int(16*s)
        leaf_h=int(8*s)
        stem_rect=pg.Rect(x-stem_w//2,y,stem_w,stem_h)
        pg.draw.rect(self.screen,(40,160,80),stem_rect)
        pg.draw.polygon(self.screen,(40,160,80),[(x,y+stem_h//3),(x-leaf_w,y+stem_h//3+leaf_h),(x,y+stem_h//3+leaf_h//2)])
        pg.draw.polygon(self.screen,(40,160,80),[(x,y+stem_h//2),(x+leaf_w,y+stem_h//2+leaf_h),(x,y+stem_h//2+leaf_h//2)])
        pg.draw.circle(self.screen,(255,120,160),(x,y),petal_r)
        pg.draw.circle(self.screen,(255,160,190),(x-petal_r//2,y-petal_r//3),petal_r-2)
        pg.draw.circle(self.screen,(255,90,140),(x+petal_r//2,y-petal_r//3),petal_r-3)

    def spawn_particles(self,x,y,color,count=20,speed=200):
        import random
        for _ in range(count):
            ang=random.uniform(0,3.14159*2)
            vx=math.cos(ang)*speed
            vy=math.sin(ang)*speed
            self.particles.append(Particle(x,y,color,life=random.uniform(0.3,0.7),vx=vx,vy=vy,rad=random.randint(2,4)))
        if len(self.particles)>S.PARTICLE_LIMIT:
            self.particles=self.particles[-S.PARTICLE_LIMIT:]

    def update_particles(self,dt):
        for p in self.particles: p.update(dt)
        self.particles=[p for p in self.particles if p.life>0]
from .entities import Bullet, Turret, Drone, Crusher, PopSpike, FallingPlatform
