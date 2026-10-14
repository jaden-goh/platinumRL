"""Pygame display; game emulation runs independently of this window."""
import pygame
class Display:
    def __init__(self,scale=2):
        pygame.init()
        self.scale=scale
        self.screen=None
        self.clock=pygame.time.Clock()
    def show(self,frame,fps=60):
        if frame is not None:
            h,w,_=frame.shape
            size=(w*self.scale,h*self.scale)
            if self.screen is None or self.screen.get_size()!=size:
                self.screen=pygame.display.set_mode(size)
                pygame.display.set_caption('Platinum RL — scripted square movement | M manual/auto | ESC quit | F5 save | F8 load')
            surface=pygame.image.frombuffer(frame.tobytes(),(w,h),'RGB')
            self.screen.blit(pygame.transform.scale(surface,size),(0,0))
            pygame.display.flip()
        self.clock.tick(fps)
    def events(self):
        return pygame.event.get()
    def close(self):pygame.quit()
