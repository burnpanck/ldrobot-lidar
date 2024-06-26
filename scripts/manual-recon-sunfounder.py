import time
from pathlib import Path
import argparse

import trio
import trio_serial
import cbor2

import sunfounder_controller


speed_values = [0,10,20,40,80]

control_history = []
lidar_history = []
async def lidar_reader(port:Path|None, read_interval=0.05):
    sample_rate = 5000
    data_rate = sample_rate*3 + sample_rate/12*20
    max_bytes = int(round(data_rate*read_interval*4))
    if port is not None:
        async with trio_serial.SerialStream(port=str(port),baudrate=230400) as ser:
            next_recv = trio.current_time()
            while True:
                data = await ser.receive_some(max_bytes=max_bytes)
                next_recv = max(trio.current_time() + read_interval/4, next_recv + read_interval)
                now = time.monotonic()
                lidar_history.append((now, data))
                await trio.sleep_until(next_recv)
                

async def file_writer(output:Path):
    global lidar_history, control_history
    async with await trio.open_file(output.with_suffix(".cbor"), "wb") as fh:
        while True:
            await trio.sleep(5)
            lidar = lidar_history
            lidar_history = []
            control = control_history
            control_history = []
            data = await trio.to_thread.run_sync(cbor2.dumps,dict(lidar=lidar,control=control))
            await fh.write(data)


async def main_control_loop(real_picar:bool=True):
    if real_picar:
        import picarx
        px = picarx.Picarx()

    sc = sunfounder_controller.SunFounderController()
    sc.set_name("Explorer")
    sc.set_type("PiCar-X")
    sc.start()
    try:

        cur_speed = 0
        cur_dir = 0
        prev_speed = cur_speed
        prev_dir = cur_dir
        running = True
        while running:
            k_val = sc.get('K')
            q_val = sc.get('Q')
            if k_val is not None and q_val is not None:
                _,y = k_val
                x,_ = q_val
                dx = (sc.get("H",50)-50)//5
                cur_dir = 15*int(round(2.6*x/100)) + dx
                cur_speed = int((-1 if y<0 else 1)*speed_values[int(round(abs(y)*(len(speed_values)-1)/100))])

            if real_picar:
                grayscale_data = px.get_grayscale_data()
                sc.set("D", grayscale_data )

            if real_picar:
                distance = px.get_distance()
                sc.set("L", [0,distance])
                sc.set("F", distance)
                if 0<distance<40:
                    cur_speed = min(max(-100,cur_speed),10)

            sc.set("A", cur_speed)

            changed = False
            t0 = time.monotonic()
            if cur_speed != prev_speed:
                s = cur_speed
                if s < 0:
                    if real_picar:
                        px.backward(abs(s))
                    else:
                        print(f"Backward {abs(s)}")
                elif s > 0:
                    if real_picar:
                        px.forward(s)
                    else:
                        print(f"Forward {s}")
                else:
                    if real_picar:
                        px.forward(0)
                    else:
                        print("Stop")
                prev_speed = cur_speed
                changed = True

            if cur_dir != prev_dir:
                if real_picar:
                    px.set_dir_servo_angle(cur_dir)
                else:
                    print(f"Steer {cur_dir}")
                prev_dir = cur_dir
                changed = True
            t1 = time.monotonic()

            if changed:
                control_history.append((t0,t1,cur_speed,cur_dir))

            await trio.sleep(0.02)
    finally:
        sc.close()

async def main(args):
    async with trio.open_nursery() as nursery:
        nursery.start_soon(main_control_loop, not args.mock)
        nursery.start_soon(lidar_reader, args.port)
        nursery.start_soon(file_writer, args.output)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="recon")
    parser.add_argument("-p","--port",type=Path,default=None)
    parser.add_argument("-o","--output",type=Path,default=Path("out"))
    parser.add_argument("-m","--mock",default=False,action="store_true")

    args = parser.parse_args()

    trio.run(main, args)

