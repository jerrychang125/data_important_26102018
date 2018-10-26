
from __future__ import print_function
import time
import argparse
import numpy as np
import picamera
from openflexure_stage import OpenFlexureStage
from openflexure_microscope import load_microscope
from openflexure_microscope.microscope import picamera_supports_lens_shading
import scipy
from scipy import ndimage, signal
from contextlib import contextmanager, closing
import data_file
import cv2
from camera_stuff import find_template

def measure_txy(ms, start_t, templ8):
    txy = np.zeros((1, 3))
    txy[0, 0] = time.time() - start_t
    frame = ms.rgb_image().astype(np.float32)
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    txy[0, 1:], corr = find_template(templ8, frame - np.mean(frame), return_corr = True, fraction=0.5)
    camera.stop_preview()
    cv2.imshow("corr", corr * 255.0 / np.max(corr))
    cv2.waitKey(1000)
    camera.start_preview()
    return txy, frame

def raster_standard(ms, area, step, start_t, templ8, backlash, experiment_group):
    stage.backlash = backlash
    standard_group = df.new_group("standard_raster", "standard_grid_scan", parent = experiment_group)
    standard_group.attrs['area'] = area
    standard_group.attrs['step'] = step
    stage.move_rel([-area[0]/2, 0, -area[1]/2])
    for i in range(0, area[1], step):
        for j in range(0, area[0], step):
            data_group = df.new_group("data", "from standard_grid_scan", parent = standard_group)
            data_group['stage_position'] = stage.position
            txy, frame = measure_txy(ms, start_t, templ8)
            data_group['cam_position'] = txy
            stage.move_rel([step, 0, 0])
            time.sleep(0.1)
        imgfile_location = "/home/pi/summer/drift/raster/standard_raster_%s.jpg" % time.strftime("%02Y.%02m.%02d_%02H:%02M:%02S")
        cv2.imwrite(imgfile_location, frame)
        data_group = df.new_group("data", "from standard_grid_scan", parent = standard_group)
        data_group['stage_position'] = stage.position
        txy, frame = measure_txy(ms, start_t, templ8)
        data_group['cam_position'] = txy
        stage.move_rel([-area[0], 0, step])
        time.sleep(0.1)
    imgfile_location = "/home/pi/summer/drift/raster/standard_raster_%s.jpg" % time.strftime("%02Y.%02m.%02d_%02H:%02M:%02S")
    cv2.imwrite(imgfile_location, frame)
    stage.move_abs(initial_stage_position)

def raster_snake(ms, area, step, start_t, templ8, backlash, expeiment_group):
    if backlash == 0:
        stage.backlash = False
    else:
        stage.backlash = backlash
    snake_group = df.new_group("snake_raster", "snake_grid_scan", parent = experiment_group)
    snake_group.attrs['area'] = area
    snake_group.attrs['step'] = step
    stage.move_rel([-area[0]/2, 0, -area[1]/2])
    for i in range(0, area[1], step):
        for j in range(0, area[0], step):
            data_group = df.new_group("data", "from snake_grid_scan", parent = snake_group)
            data_group['stage_position'] = stage.position
            txy, frame = measure_txy(ms, start_t, templ8)
            data_group['cam_position'] = txy
            stage.move_rel([step, 0, 0])
            time.sleep(0.1)
        imgfile_location = "/home/pi/summer/drift/raster/snake_raster_%s.jpg" % time.strftime("%02Y.%02m.%02d_%02H:%02M:%02S")
        cv2.imwrite(imgfile_location, frame)
        data_group = df.new_group("data", "from snake_grid_scan", parent = snake_group)
        data_group['stage_position'] = stage.position
        txy, frame = measure_txy(ms, start_t, templ8)
        data_group['cam_position'] = txy
        stage.move_rel([0, 0, step])
        time.sleep(0.1)
        imgfile_location = "/home/pi/summer/drift/raster/snake_raster_%s.jpg" % time.strftime("%02Y.%02m.%02d_%02H:%02M:%02S")
        cv2.imwrite(imgfile_location, frame)
        for j in range(0, area[0], step):
            data_group = df.new_group("data", "from snake_grid_scan", parent = snake_group)
            data_group['stage_position'] = stage.position
            txy, frame = measure_txy(ms, start_t, templ8)
            data_group['cam_position'] = txy
            stage.move_rel([-step, 0, 0])
            time.sleep(0.1)
        imgfile_location = "/home/pi/summer/drift/raster/snake_raster_%s.jpg" % time.strftime("%02Y.%02m.%02d_%02H:%02M:%02S")
        cv2.imwrite(imgfile_location, frame)
        stage.move_rel([0, 0, step])
        time.sleep(0.1)
        imgfile_location = "/home/pi/summer/drift/raster/snake_raster_%s.jpg" % time.strftime("%02Y.%02m.%02d_%02H:%02M:%02S")
        cv2.imwrite(imgfile_location, frame)
    stage.move_abs(initial_stage_position)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Grid scan")
    parser.add_argument("area", type=int, nargs = 2, help="Area of scan measured in steps")
    parser.add_argument("step", type=int, help="Displacement between measurments measured in steps")
    parser.add_argument("--backlash", type=int, default = 500, help="Backlash correction on or off")
    args = parser.parse_args()

    with load_microscope("microscope_settings.npz", dummy_stage = False) as ms, \
         closing(data_file.Datafile(filename = "raster.hdf5")) as df:

        assert picamera_supports_lens_shading(), "You need the updated picamera module with lens shading!"

        camera = ms.camera
        stage = ms.stage

        area = args.area
        step = args.step
        backlash = args.backlash

        camera.resolution = (640, 480)
        camera.start_preview(resolution=(640,480))

        initial_stage_position = stage.position

        stage.move_rel([-backlash, -backlash, -backlash])
        stage.move_rel([backlash, backlash, backlash])

        experiment_group = df.new_group("raster", "performes grid scan")

        image = ms.rgb_image().astype(np.float32)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        mean = np.mean(image)
        templ8 = (image - mean)[150:-150, 150:-150]
        experiment_group['template_image'] = templ8
        experiment_group['sample_image'] = image
        imgfile_location = "/home/pi/summer/drift/calibration/raster_templ8.jpg"
        cv2.imwrite(imgfile_location, templ8)
        imgfile_location = "/home/pi/summer/drift/calibration/raster_image.jpg"
        cv2.imwrite(imgfile_location, image)

        start_t = time.time()

        raster_standard(ms, area, step, start_t, templ8, backlash, experiment_group)
        raster_snake(ms, area, step, start_t, templ8, backlash, experiment_group)

        camera.stop_preview()
        print("Done")