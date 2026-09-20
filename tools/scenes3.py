"""Сцены-воксельные декорации в стиле майнкрафт-анимаций."""
import numpy as np
from vox import *

def lab_hall():
    w=World(26,7,16)
    w.fill(0,25,0,0,0,15,CONC)                      # пол
    for x in range(0,26,2): w.set(x,0,7,CONCD); w.set(x,0,8,CONCD)  # тех-полоса
    w.fill(0,25,6,6,0,15,CONCD)                    # потолок
    for z in (2,5,8,11,14):                        # ряды ламп
        for x in range(3,21,4): w.fill(x,x+1,5,5,z,z,LAMP)
    w.fill(0,0,1,5,0,15,CONCD)                     # стены
    w.fill(25,25,1,5,0,15,CONCD)
    for z in range(1,15,3):                        # окна слева
        w.fill(0,0,2,4,z,z+1,GLASS)
    w.fill(1,1,1,1,0,15,METAL)                     # колонны
    w.fill(24,24,1,1,0,15,METAL)
    for z in (2,6,10,13):                          # столы с экранами справа
        w.fill(20,23,1,1,z,z+1,TABLE)
        w.fill(22,22,2,3,z,z,SCREEN)
        w.fill(20,23,2,2,z,z+1,METAL)
    w.fill(11,14,1,5,15,15,METAL)                  # торец-дверь
    w.fill(10,15,5,5,14,14,LAMP)
    w.fill(12,13,1,4,15,15,GLASS)
    w.fill(11,14,1,5,0,0,METAL)
    w.calc_light(sky_top=False)
    return w

def cell():
    w=World(8,6,8)
    w.fill(0,7,0,0,0,7,CONCD)
    w.fill(0,7,5,5,0,7,CONCD)
    w.fill(0,0,1,4,0,7,BRICK); w.fill(7,7,1,4,0,7,BRICK)
    w.fill(0,7,1,4,7,7,BRICK)
    w.fill(0,7,1,4,0,0,GLASS)                      # стеклянная стена к камере наблюдения
    w.fill(2,5,5,5,2,3,LAMP)
    w.fill(5,6,1,1,5,6,TABLE)                      # койка
    w.fill(5,6,2,2,6,6,PAPER)
    w.fill(1,1,1,1,6,6,OBSID)                      # обсидиан в углу
    w.fill(1,1,2,2,6,6,OBSID)
    w.calc_light(sky_top=False)
    return w

def corridor():
    w=World(6,5,22)
    w.fill(0,5,0,0,0,21,CONCD)
    w.fill(0,5,4,4,0,21,CONCD)
    w.fill(0,0,1,3,0,21,METAL); w.fill(5,5,1,3,0,21,METAL)
    for z in range(2,21,4): w.fill(2,3,4,4,z,z,REDL)
    w.fill(2,3,1,3,21,21,METAL)
    w.calc_light(sky_top=False)
    return w

def street():
    w=World(30,14,24)
    w.fill(0,29,0,0,0,23,ASPHALT)
    for x in range(0,30,3): w.fill(x,x,0,0,11,12,CONC)   # разметка
    # дома слева и справа
    for (x0,x1,h,c) in ((0,5,9,BRICK),(7,11,12,CONCD),(20,25,10,BRICK),(26,29,13,CONCD)):
        w.fill(x0,x1,1,h,0,6,c)
        for yy in range(2,h,3):
            for zz in range(1,6,2): w.fill(x0+1,x1-1,yy,yy,zz,zz,GLASS)
    w.fill(12,19,1,2,0,23,ASPHALT)
    # фонари
    for z in (4,12,20):
        w.fill(12,12,1,4,z,z,METAL); w.fill(12,12,5,5,z,z,LAMP)
    w.calc_light(sky_top=True,sky_level=9)   # сумерки
    return w

def square_fire():
    w=World(24,8,18)
    w.fill(0,23,0,0,0,17,ASPHALT)
    w.fill(10,13,1,1,8,10,WOOD)                    # костёр-бревна
    w.fill(11,12,2,3,9,9,FIRE)
    for (x0,x1,h) in ((0,4,7),(19,23,8)):
        w.fill(x0,x1,1,h,0,5,BRICK)
    w.calc_light(sky_top=True,sky_level=3)         # ночь
    return w

def desk_room():
    w=World(10,6,10)
    w.fill(0,9,0,0,0,9,WOOD)
    w.fill(0,9,5,5,0,9,CONCD)
    w.fill(0,0,1,4,0,9,BRICK); w.fill(9,9,1,4,0,9,BRICK); w.fill(0,9,1,4,9,9,BRICK)
    w.fill(3,6,1,1,4,6,TABLE)                      # стол
    w.fill(4,5,2,2,5,5,PAPER)                      # бумаги
    w.fill(2,2,2,3,5,5,LAMP)                       # настольная лампа
    w.fill(0,2,2,4,0,0,GLASS)                      # окно
    w.calc_light(sky_top=False)
    return w

def animal_room():
    w=World(16,6,12)
    w.fill(0,15,0,0,0,11,CONCD)
    w.fill(0,15,5,5,0,11,CONCD)
    w.fill(0,0,1,4,0,11,METAL); w.fill(15,15,1,4,0,11,METAL)
    w.fill(6,9,5,5,2,9,LAMP)
    for z in (2,5,8):                       # клетки слева и справа
        w.fill(2,5,1,2,z,z+1,CRATE)
        w.fill(2,5,3,3,z,z+1,GLASS)
        w.fill(10,13,1,2,z,z+1,CRATE)
        w.fill(10,13,3,3,z,z+1,GLASS)
        w.fill(3,3,2,2,z,z,SCREEN)          # глаза в клетке
        w.fill(11,11,2,2,z+1,z+1,SCREEN)
    w.fill(7,8,1,4,11,11,METAL)
    w.calc_light(sky_top=False)
    return w

def meeting_room():
    w=World(14,6,10)
    w.fill(0,13,0,0,0,9,WOOD)
    w.fill(0,13,5,5,0,9,CONCD)
    w.fill(0,0,1,4,0,9,BRICK); w.fill(13,13,1,4,0,9,BRICK); w.fill(0,13,1,4,9,9,BRICK)
    w.fill(3,10,1,1,4,5,TABLE)              # длинный стол
    w.fill(5,6,2,2,4,4,PAPER); w.fill(7,8,2,2,5,5,PAPER)
    w.fill(5,8,5,5,4,5,LAMP)
    w.fill(0,2,2,4,0,0,GLASS)
    w.calc_light(sky_top=False)
    return w
