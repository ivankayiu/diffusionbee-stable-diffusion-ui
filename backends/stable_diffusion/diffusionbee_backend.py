print("starting backend")
import numpy as np
import argparse
from PIL import Image
import json
import random
import requests
import base64
import multiprocessing
import sys
import copy
import math
import time
import traceback
import os
import subprocess
import sys
from pathlib import Path


# b2py t2im {"prompt": "sun glasses" , "img_width":640 , "img_height" : 640 , "num_imgs" : 10 , "input_image":"/Users/divamgupta/Downloads/inn.png" , "mask_image" : "/Users/divamgupta/Downloads/maa.png" , "is_inpaint":true  }

if not ( getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')):
    print("Adding sys paths")
    dir_path = os.path.dirname(os.path.realpath(__file__))
    sys.path.append(os.path.join(dir_path , "../model_converter"))

    model_interface_path = os.environ.get('MODEL_INTERFACE_PATH') or "../stable_diffusion_tf_models"
    sys.path.append( os.path.join(dir_path , model_interface_path) )
else:
    print("not adding sys paths")


from convert_model import convert_model
from stable_diffusion.stable_diffusion import StableDiffusion , ModelContainer
from stable_diffusion.utils.utils import get_sd_run_from_dict

from applets.applets import register_applet , run_applet
from applets.frame_interpolator import FrameInterpolator
# get the model interface form the environ
USE_DUMMY_INTERFACE = False
if  USE_DUMMY_INTERFACE :
    from fake_interface import ModelInterface
else:
    from interface import ModelInterface

model_container = ModelContainer()



home_path = Path.home()

projects_root_path = os.path.join(home_path, ".diffusionbee")

if not os.path.isdir(projects_root_path):
    os.mkdir(projects_root_path)




if 'DEBUG' in os.environ and str(os.environ['DEBUG']) == '1':
    debug_output_path = os.path.join(projects_root_path, "debug_outs")
    if not os.path.isdir(debug_output_path):
        os.mkdir(debug_output_path)
    print("Debug outputs stored at : " , debug_output_path )
else:
    debug_output_path = None




defualt_data_root = os.path.join(projects_root_path, "images")


if not os.path.isdir(defualt_data_root):
    os.mkdir(defualt_data_root)



class Unbuffered(object):
    def __init__(self, stream):
        self.stream = stream

    def write(self, data):
        self.stream.write(data)
        self.stream.flush()

    def writelines(self, datas):
        self.stream.writelines(datas)
        self.stream.flush()

    def __getattr__(self, attr):
        return getattr(self.stream, attr)


sys.stdout = Unbuffered(sys.stdout)





def process_opt(d, generator):

    batch_size = 1# int(d['batch_size'])
    n_imgs = math.ceil(d['num_imgs'] / batch_size)
    sd_run = get_sd_run_from_dict(d)

    for i in range(n_imgs):
        
        sd_run.img_id = i

        # --- Handle Base64 image inputs for Inpainting ---
        if d.get("is_inpaint"):
            if d.get("input_image_b64"):
                b64_str = d["input_image_b64"].split(",")[1]
                img_data = base64.b64decode(b64_str)
                fpath = os.path.join(defualt_data_root, f"inp_{random.randint(0, 100000000)}.png")
                with open(fpath, 'wb') as f:
                    f.write(img_data)
                sd_run.input_image = fpath

            if d.get("mask_image_b64"):
                b64_str = d["mask_image_b64"].split(",")[1]
                img_data = base64.b64decode(b64_str)
                fpath = os.path.join(defualt_data_root, f"mask_{random.randint(0, 100000000)}.png")
                with open(fpath, 'wb') as f:
                    f.write(img_data)
                sd_run.mask_image = fpath
        # --- End of Base64 handling ---


        print("got" , d )

        outs  = generator.generate(sd_run)

        if outs is None:
            return

        img = outs['img']

        if img is None:
            return
        
        for i in range(len(img)):
            s = ''.join(filter(str.isalnum, str(d['prompt'])[:30] ))
            fpath = os.path.join(defualt_data_root , "%s_%d.png"%(s ,  random.randint(0 ,100000000)) )

            Image.fromarray(img[i]).save(fpath)
            ret_dict = {"generated_img_path" : fpath}

            if 'aux_img' in outs:
                ret_dict['aux_output_image_path'] = outs['aux_img']

            print("sdbk nwim %s"%(json.dumps(ret_dict)) )



def process_ai_command(d):
    task = d.get("task")
    if task == "search_image":
        query = d.get("query", "random")
        print(f"Searching for image with query: {query}")

        try:
            # Use a simple, key-less API for demonstration
            url = f"https://source.unsplash.com/random/1024x768/?{requests.utils.quote(query)}"
            response = requests.get(url, timeout=15)
            response.raise_for_status() # Raise an exception for bad status codes

            # Generate a safe filename
            s = ''.join(filter(str.isalnum, str(query)[:30]))
            fpath = os.path.join(defualt_data_root, f"search_{s}_{random.randint(0, 100000000)}.png")

            # Save the image
            with open(fpath, 'wb') as f:
                f.write(response.content)

            # Send the path back to the frontend using the existing format
            # IMPORTANT: We reuse the "nwim" (new image) code so the frontend can understand it
            ret_dict = {"generated_img_path": fpath}
            print(f"sdbk nwim {json.dumps(ret_dict)}")

        except Exception as e:
            traceback.print_exc()
            print(f"sdbk errr Image search failed: {str(e)}")

    else:
        print(f"sdbk errr Unknown AI command: {task}")


def diffusion_bee_main():

    # Start the WebSocket server as a background process
    try:
        websocket_server_path = os.path.join(os.path.dirname(__file__), 'websocket_server.py')
        # Use sys.executable to ensure we use the same python interpreter
        subprocess.Popen([sys.executable, websocket_server_path])
        print("WebSocket server started in the background.")
    except Exception as e:
        print(f"Failed to start WebSocket server: {e}")

    time.sleep(2)
    register_applet(model_container , FrameInterpolator)

    print("sdbk mltl Loading Model")

    def callback(state="" , progress=-1):
        print("sdbk dnpr "+str(progress) )
        if state != "Generating":
            print("sdbk gnms " + state)

        if is_avail():
            if "__stop__" in get_input():
                return "stop"

    generator = StableDiffusion( model_container , ModelInterface , None , model_name=None, callback=callback, debug_output_path=debug_output_path )    


    print("sdbk mdld")

    while True:
        print("sdbk inrd") # input ready

        inp_str = get_input()

        print("got" , inp_str)

        if inp_str.strip() == "":
            continue

        if  ((not "b2py t2im" in inp_str ) and (not "b2py rapp" in inp_str) and (not "b2py aicmd" in inp_str) ) or "__stop__" in inp_str:
            continue

        if "b2py t2im" in inp_str:
            inp_str = inp_str.replace("b2py t2im" , "").strip()
            try:
                d = json.loads(inp_str)
                print("sdbk inwk") # working on the input
        
                process_opt(d, generator)
                
            except Exception as e:
                traceback.print_exc()
                print("sdbk errr %s"%(str(e)))
                print("py2b eror " + str(e))

        elif "b2py aicmd" in inp_str:
            inp_str = inp_str.replace("b2py aicmd", "").strip()
            try:
                d = json.loads(inp_str)
                print("sdbk inwk") # working on the input
                process_ai_command(d)
            except Exception as e:
                traceback.print_exc()
                print(f"sdbk errr {str(e)}")
        elif "b2py rapp" in inp_str:
            inp_str = inp_str.replace("b2py rapp" , "").strip()
            applet_name = inp_str.split(" ")[0]
            inp_str = inp_str.replace(applet_name , "").strip()

            try:
                d = json.loads(inp_str)
                print("sdbk inwk") # working on the input
                run_applet(applet_name , d )
            except Exception as e:
                traceback.print_exc()
                print("sdbk errr %s"%(str(e)))


from  stable_diffusion.utils.stdin_input import is_avail, get_input


if __name__ == "__main__":
    multiprocessing.freeze_support()  # for pyinstaller

    if len(sys.argv) > 1 and sys.argv[1] == 'convert_model':
        checkpoint_filename = sys.argv[2]
        out_filename = sys.argv[3]
        convert_model(checkpoint_filename, out_filename )
        print("model converted ")
    else:
        diffusion_bee_main()

