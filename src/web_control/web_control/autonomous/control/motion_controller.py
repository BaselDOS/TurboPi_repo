import time

class MotionController:

    def __init__(self):

        self.forward_speed = 0.38
        self.slow_speed = 0.25
        self.turn_speed = 1.9
        self.strafe_speed = 0.30
        self.reverse_speed = -0.28

        self.slow_dist = 70
        self.turn_dist = 50
        self.stop_dist = 35

        self.action_lock_until = 0
        self.escape_until = 0

        self.last_cmd = (0,0,0)

        self.flow_stuck_counter = 0
        self.flow_threshold = 0.15
        self.flow_frames = 6


    def decide(self,left,center,right,flow,distance):

        now = time.time()

        if flow < self.flow_threshold and self.last_cmd[0] > 0:
            self.flow_stuck_counter += 1
        else:
            self.flow_stuck_counter = 0

        if self.flow_stuck_counter > self.flow_frames:

            self.escape_until = now + 0.8
            self.flow_stuck_counter = 0
            return (-0.3,0,2.0)

        if now < self.escape_until:
            return (-0.28,0,1.9)

        if now < self.action_lock_until:
            return self.last_cmd

        lin_x=0
        lin_y=0
        ang_z=0

        if distance < self.stop_dist:

            self.escape_until = now + 0.6
            return (-0.28,0,1.9)

        elif distance < self.turn_dist:

            ang_z = self.turn_speed

        elif center:

            ang_z = self.turn_speed

        elif left:

            lin_x = self.slow_speed
            lin_y = -self.strafe_speed

        elif right:

            lin_x = self.slow_speed
            lin_y = self.strafe_speed

        elif distance < self.slow_dist:

            lin_x = self.slow_speed

        else:

            lin_x = self.forward_speed

        self.last_cmd = (lin_x,lin_y,ang_z)
        self.action_lock_until = now + 0.35

        return lin_x,lin_y,ang_z
