"""Deterministic scripted policy: trace a square, no learning involved."""
class CircleAgent:
    def __init__(self,frames_per_direction=18):
        self.directions=('RIGHT','DOWN','LEFT','UP')
        self.frames_per_direction=frames_per_direction
        self.tick=0
    def act(self):
        direction=self.directions[(self.tick//self.frames_per_direction)%4]
        self.tick+=1
        return (direction,)
