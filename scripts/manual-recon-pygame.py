import time
import threading

import trio
import trio_serial
import pygame


speed_values = [-20,-10,-5,0,10,20,30,50,80]

async def lidar_reader():
    pass

async def file_writer():
    pass


def main_control_loop(history:list):
    pygame.init()
    screen = pygame.display.set_mode((600, 400))

    lkey = False
    rkey = False
    cur_speed_idx = speed_values.index(0)
    cur_speed = 0
    prev_dir = 0
    prev_speed_idx = cur_speed_idx
    running = True
    while running:
        events = pygame.event.get()
        if not events:
            events = [pygame.event.wait()]
        changed = False
        for event in events:
            if event.type == pygame.QUIT:
                running = False
                break
            if event.type not in {pygame.KEYDOWN,pygame.KEYUP}:
                continue
            down = event.type == pygame.KEYDOWN
            match (event.key, down):
                case pygame.K_LEFT,_:
                    lkey = down
                case pygame.K_RIGHT,_:
                    rkey = down
                case pygame.K_UP,True:
                    cur_speed_idx += 1
                case pygame.K_DOWN,True:
                    cur_speed_idx -= 1
                case pygame.K_SPACE,True:
                    cur_speed_idx = speed_values.index(0)
                case pygame.K_ESCAPE,True:
                    running = False
                    break
        cur_speed_idx = min(max(0,cur_speed_idx),len(speed_values)-1)
        cur_dir = (30 if rkey else 0) - (30 if lkey else 0)

        t0 = time.monotonic()
        if cur_speed_idx != prev_speed_idx:
            s = speed_values[cur_speed_idx]
            if s < 0:
                print(f"Backward {abs(s)}")
                #px.backward(abs(s))
            elif s > 0:
                print(f"Forward {s}")
                #px.forward(s)
            else:
                print("Stop")
                #px.forward(0)
            cur_speed = s
            prev_speed_idx = cur_speed_idx
            changed = True

        if cur_dir != prev_dir:
            print(f"Steer {cur_dir}")
            #px.set_dir_servo_angle(cur_dir)
            prev_dir = cur_dir
            changed = True
        t1 = time.monotonic()

        if changed:
            history.append((t0,t1,cur_speed,cur_dir))


if __name__ == "__main__":
    pygame.K_SPACE
    pygame.K_ESCAPE
    main_control_loop([])


