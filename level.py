import random
import pygame as pg
from .entities import Platform, Spike, Pendulum, Bomb, PowerUp, Saw, LaserGate, Slope, WindZone, GravityZone, Wall, Turret, Bullet, Drone, Crusher, PopSpike, FallingPlatform, Crate, Springboard, GravityWell, LiquidZone
from . import settings as S

class Level:
    def __init__(self):
        self.platforms=[]
        self.spikes=[]
        self.pendulums=[]
        self.bombs=[]
        self.powerups=[]
        self.saws=[]
        self.lasers=[]
        self.slopes=[]
        self.winds=[]
        self.gravzones=[]
        self.walls=[]
        self.crates=[]
        self.springs=[]
        self.wells=[]
        self.liquids=[]
        self.scroll_x=0
        self.spawn_x=S.WIDTH
        self.t=0
        self.theme_name='Desert'
        self.pattern_weights=self.make_theme_weights('Desert')
        self.reset()

    def reset(self):
        self.platforms.clear()
        self.spikes.clear()
        self.pendulums.clear()
        self.bombs.clear()
        self.powerups.clear()
        self.saws.clear()
        self.lasers.clear()
        self.slopes.clear()
        self.winds.clear()
        self.gravzones.clear()
        self.walls.clear()
        self.crates.clear()
        self.springs.clear()
        self.wells.clear()
        self.liquids.clear()
        self.scroll_x=0
        self.spawn_x=S.WIDTH
        for i in range(10):
            y=S.HEIGHT-60
            self.platforms.append(Platform(i*160,y,160,30,ice=False))
            self.platforms.append(Platform(i*160,30,160,30,ice=False))
        self.spikes.append(Spike(0,S.HEIGHT-30,S.WIDTH,30,top=True))
        self.spikes.append(Spike(0,0,S.WIDTH,30,top=False))

    def update(self,dt):
        self.t+=dt
        sx=int(S.SCROLL_SPEED*dt)
        self.scroll_x+=sx
        for coll in [self.platforms,self.spikes,self.pendulums,self.bombs,self.powerups,self.saws,self.lasers,self.slopes,self.winds,self.gravzones,self.walls,self.crates,self.springs,self.wells,self.liquids]:
            for obj in coll:
                if hasattr(obj,'rect'): obj.rect.x-=sx
                if hasattr(obj,'update'): obj.update(dt)
        for t in getattr(self,'turrets',[]):
            t.rect.x-=sx
            t.update(dt)
        for d in getattr(self,'drones',[]):
            d.rect.x-=sx
            d.update(dt)
        for c in getattr(self,'crushers',[]):
            c.rect.x-=sx
            c.update(dt)
        for fp in getattr(self,'falls',[]):
            fp.rect.x-=sx
            fp.update(dt)
        for b in getattr(self,'bullets',[]):
            b.rect.x-=sx
            b.update(dt)
        self.cleanup()
        difficulty=min(1.0,self.t/60.0)
        while self.spawn_x<self.scroll_x+S.WIDTH+900:
            self.spawn_chunk(self.spawn_x,difficulty)
            self.spawn_x+=random.randint(160,260)

    def cleanup(self):
        def still_needed(r):
            return r.right>=-300
        self.platforms=[p for p in self.platforms if still_needed(p.rect)]
        self.spikes=[s for s in self.spikes if still_needed(s.rect)]
        self.pendulums=[p for p in self.pendulums if still_needed(p.rect)]
        self.bombs=[b for b in self.bombs if still_needed(b.rect)]
        self.powerups=[p for p in self.powerups if still_needed(p.rect) and getattr(p,'alive',True)]
        self.saws=[s for s in self.saws if still_needed(s.rect)]
        self.lasers=[l for l in self.lasers if still_needed(l.rect)]
        self.slopes=[s for s in self.slopes if still_needed(s.rect)]
        self.winds=[w for w in self.winds if still_needed(w.rect)]
        self.gravzones=[g for g in self.gravzones if still_needed(g.rect)]
        self.walls=[w for w in self.walls if still_needed(w.rect)]
        self.turrets=[t for t in getattr(self,'turrets',[]) if still_needed(t.rect)]
        self.drones=[d for d in getattr(self,'drones',[]) if still_needed(d.rect)]
        self.crushers=[c for c in getattr(self,'crushers',[]) if still_needed(c.rect)]
        self.falls=[f for f in getattr(self,'falls',[]) if still_needed(f.rect)]
        self.bullets=[b for b in getattr(self,'bullets',[]) if still_needed(b.rect) and b.alive]
        self.crates=[c for c in self.crates if still_needed(c.rect)]
        self.springs=[s for s in self.springs if still_needed(s.rect)]
        self.wells=[w for w in self.wells if still_needed(w.rect)]
        self.liquids=[l for l in self.liquids if still_needed(l.rect)]

    def spawn_chunk(self,x,difficulty=0.0):
        pats=list(self.pattern_weights.keys())
        weights=list(self.pattern_weights.values())
        pat=random.choices(pats,weights,k=1)[0]
        if pat=='flat':
            self.platforms.append(Platform(x,S.HEIGHT-60,160,28))
            self.platforms.append(Platform(x,30,160,28))
            if random.random()<0.25+difficulty*0.2:
                self.pendulums.append(Pendulum(x+80,30,rad=16,spd=random.uniform(0.8,1.2)))
        if pat=='gap':
            self.platforms.append(Platform(x,S.HEIGHT-60,120,28))
            if random.random()<0.5:
                self.platforms.append(Platform(x+180,30,140,28))
        if pat=='stairs':
            yb=S.HEIGHT-60
            self.platforms.append(Platform(x,yb,120,28))
            self.platforms.append(Platform(x+140,yb-40,120,28,move={'axis':'y','amp':30,'spd':1.2}))
        if pat=='ice':
            self.platforms.append(Platform(x,S.HEIGHT-60,200,26,ice=True))
            self.platforms.append(Platform(x,30,200,26,ice=True))
        if pat=='bounce':
            self.platforms.append(Platform(x,S.HEIGHT-70,160,20,bounce=True))
        if pat=='conveyor':
            self.platforms.append(Platform(x,S.HEIGHT-60,200,26,conveyor_vx=random.choice([-120,120])))
        if pat=='saw':
            self.saws.append(Saw(x+100,S.HEIGHT-120,rad=18,spd=220))
        if pat=='laser':
            self.lasers.append(LaserGate(x+140,80,h=S.HEIGHT-160,period=2.0))
        if pat=='bomb_rain':
            for i in range(random.randint(2,4)):
                self.bombs.append(Bomb(x+random.randint(20,140),-40-random.randint(0,120)))
        if pat=='pend_gate':
            self.pendulums.append(Pendulum(x+80,30,rad=18,spd=1.0))
            self.pendulums.append(Pendulum(x+160,30,rad=18,spd=1.2))
        if pat=='slope':
            x2=x+200
            y1=S.HEIGHT-60; y2=y1-random.choice([60,80,100])
            self.slopes.append(Slope(x,y1,x2,y2,thickness=12))
        if pat=='wind':
            self.winds.append(WindZone(x+40,120,200,S.HEIGHT-240,wind_vx=random.choice([160,-160])))
        if pat=='grav':
            self.gravzones.append(GravityZone(x+60,140,160,S.HEIGHT-280,scale=random.choice([0.6,0.8,1.2,1.4])))
        if pat=='walls':
            self.walls.append(Wall(x+140,160,S.HEIGHT-320,width=22))
        if pat=='turret':
            if not hasattr(self,'turrets'): self.turrets=[]
            if not hasattr(self,'bullets'): self.bullets=[]
            t=Turret(x+160, S.HEIGHT//2)
            self.turrets.append(t)
        if pat=='drone':
            if not hasattr(self,'drones'): self.drones=[]
            self.drones.append(Drone(x+200, random.choice([120,S.HEIGHT-120])))
        if pat=='crusher':
            if not hasattr(self,'crushers'): self.crushers=[]
            self.crushers.append(Crusher(x+160, top=random.choice([True,False])))
        if pat=='popspike':
            if not hasattr(self,'popspikes'): self.popspikes=[]
            self.popspikes.append(PopSpike(x+80, S.HEIGHT-56, up=True))
            self.popspikes.append(PopSpike(x+80, 30, up=False))
        if pat=='falling':
            if not hasattr(self,'falls'): self.falls=[]
            self.falls.append(FallingPlatform(x+120, S.HEIGHT-100, 120, 24))
        if pat=='crate':
            self.crates.append(Crate(x+120,S.HEIGHT-140))
        if pat=='spring':
            self.springs.append(Springboard(x+120,S.HEIGHT-78))
        if pat=='well':
            self.wells.append(GravityWell(x+180,S.HEIGHT//2,r=120,sign=random.choice([1,-1])))
        if pat=='liquid':
            self.liquids.append(LiquidZone(x+40,160,200,S.HEIGHT-320))
        if random.random()<0.20+difficulty*0.15:
            self.bombs.append(Bomb(x+random.randint(40,120),-40))
        if random.random()<0.18:
            kind=random.choice(['shield','slow','bounce','dflip','turbo'])
            self.powerups.append(PowerUp(x+random.randint(20,120),random.choice([S.HEIGHT-120,80]),kind))

    def draw(self,screen):
        for p in self.platforms: p.draw(screen)
        for s in self.spikes: s.draw(screen)
        for p in self.pendulums: p.draw(screen)
        for b in self.bombs: b.draw(screen)
        for p in self.powerups: p.draw(screen)
        for s in self.saws: s.draw(screen)
        for l in self.lasers: l.draw(screen)
        for s in self.slopes: s.draw(screen)
        for w in self.winds: w.draw(screen)
        for g in self.gravzones: g.draw(screen)
        for w in self.walls: w.draw(screen)
        for t in getattr(self,'turrets',[]): t.draw(screen)
        for d in getattr(self,'drones',[]): d.draw(screen)
        for c in getattr(self,'crushers',[]): c.draw(screen)
        for ps in getattr(self,'popspikes',[]): ps.draw(screen)
        for f in getattr(self,'falls',[]): f.draw(screen)
        for b in getattr(self,'bullets',[]): b.draw(screen)
        for c in self.crates: c.draw(screen)
        for s in self.springs: s.draw(screen)
        for w in self.wells: w.draw(screen)
        for l in self.liquids: l.draw(screen)

    def make_theme_weights(self,name):
        if name=='Desert':
            return {
                'flat':10,'gap':8,'stairs':7,'ice':3,'bounce':6,'conveyor':5,
                'saw':5,'laser':4,'bomb_rain':6,'pend_gate':5,'slope':10,'wind':7,'grav':4,'walls':4,
                'turret':4,'drone':4,'crusher':4,'popspike':7,'falling':7,'crate':9,'spring':9,'well':4,'liquid':3
            }
        if name=='Factory':
            return {
                'flat':7,'gap':8,'stairs':6,'ice':2,'bounce':3,'conveyor':10,
                'saw':8,'laser':10,'bomb_rain':7,'pend_gate':6,'slope':4,'wind':3,'grav':6,'walls':8,
                'turret':10,'drone':7,'crusher':8,'popspike':7,'falling':5,'crate':6,'spring':4,'well':3,'liquid':2
            }
        if name=='Ocean':
            return {
                'flat':8,'gap':7,'stairs':6,'ice':1,'bounce':4,'conveyor':3,
                'saw':4,'laser':5,'bomb_rain':7,'pend_gate':7,'slope':7,'wind':10,'grav':8,'walls':4,
                'turret':4,'drone':5,'crusher':4,'popspike':6,'falling':6,'crate':5,'spring':6,'well':8,'liquid':10
            }
        return self.make_theme_weights('Desert')

    def set_theme(self,name):
        self.theme_name=name
        self.pattern_weights=self.make_theme_weights(name)
