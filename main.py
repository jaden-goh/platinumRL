"""Application layer: wires emulator, policy, and visualization together."""
import argparse
from pathlib import Path
import pygame
from emulator.libretro import DSEmulator
from agents.circle import CircleAgent
from viewer.display import Display

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--core',default='cores/desmume_libretro.so')
    p.add_argument('--rom',default='roms/platinumusa.nds')
    p.add_argument('--state',default=None,help='Optional Libretro state file to load at launch')
    p.add_argument('--hold',type=int,default=18,help='Emulated frames per direction')
    p.add_argument('--fps',type=int,default=60,help='Window refresh cap')
    p.add_argument('--frames-per-tick',type=int,default=1)
    args=p.parse_args()
    agent=CircleAgent(args.hold)
    manual=True
    keymap={pygame.K_UP:"UP",pygame.K_DOWN:"DOWN",pygame.K_LEFT:"LEFT",pygame.K_RIGHT:"RIGHT",pygame.K_z:"A",pygame.K_x:"B",pygame.K_RETURN:"START",pygame.K_BACKSPACE:"SELECT",pygame.K_a:"X",pygame.K_s:"Y"}
    viewer=Display(scale=2)
    emulator=None
    try:
        emulator=DSEmulator(args.core,args.rom)
        print('Core loaded. FPS reported:',emulator.fps)
        if args.state:
            emulator.load_state(args.state)
        running=True
        while running:
            for event in viewer.events():
                if event.type==pygame.QUIT or (event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE):running=False
                elif event.type==pygame.KEYDOWN and event.key==pygame.K_m:
                    manual=not manual
                    print('Mode:', 'manual' if manual else 'automatic square')
                elif event.type==pygame.KEYDOWN and event.key==pygame.K_F5:
                    emulator.save_state('saves/quick.state');print('Saved saves/quick.state')
                elif event.type==pygame.KEYDOWN and event.key==pygame.K_F8:
                    emulator.load_state('saves/quick.state');print('Loaded saves/quick.state')
            if not running:break
            pressed=pygame.key.get_pressed()
            buttons=[button for key,button in keymap.items() if pressed[key]] if manual else agent.act()
            frame=emulator.step(buttons,frames=args.frames_per_tick)
            viewer.show(frame,fps=args.fps)
    finally:
        if emulator is not None:emulator.close()
        viewer.close()
if __name__=='__main__':main()
