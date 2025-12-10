import subprocess
import threading
import queue
import json
import os
from flask import Flask, request, jsonify, send_from_directory

# --- Configuration ---
BACKEND_SCRIPT = "diffusionbee_backend.py"
MODELS_DIR = os.path.join(os.path.expanduser("~"), ".diffusionbee", "images")

app = Flask(__name__)

# --- Global variables for backend process management ---
backend_process = None
output_queue = queue.Queue()
input_queue = queue.Queue()

def enqueue_output(out, q):
    """Thread function to read stdout from the backend process."""
    for line in iter(out.readline, ''):
        q.put(line)
    out.close()

def start_backend():
    """Starts the diffusionbee_backend.py script as a subprocess."""
    global backend_process
    print("Starting backend process...")

    # We need to run this from the script's directory
    script_dir = os.path.dirname(os.path.realpath(__file__))

    backend_process = subprocess.Popen(
        ["python", "-u", BACKEND_SCRIPT], # -u for unbuffered output
        cwd=script_dir,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # Thread to read stdout without blocking
    t = threading.Thread(target=enqueue_output, args=(backend_process.stdout, output_queue))
    t.daemon = True
    t.start()
    print("Backend process started.")

def send_command_to_backend(command):
    """Sends a command to the backend's stdin and waits for the result."""
    print(f"Sending command: {command.strip()}")
    backend_process.stdin.write(command + '\\n')
    backend_process.stdin.flush()

    while True:
        try:
            line = output_queue.get(timeout=120)  # 2-minute timeout
            print(f"Backend output: {line.strip()}")
            if line.startswith("sdbk nwim"):
                result_json = line.replace("sdbk nwim", "").strip()
                return json.loads(result_json)
            elif line.startswith("sdbk errr"):
                raise Exception(f"Backend error: {line.strip()}")
            elif line.startswith("sdbk inrd"): # "input ready"
                continue # Backend is ready for next input, but we are waiting for our result
        except queue.Empty:
            raise TimeoutError("Timeout waiting for response from the backend process.")


@app.route('/api/inpainting', methods=['POST'])
def inpainting_endpoint():
    data = request.json

    # --- Basic validation ---
    if not all(k in data for k in ["image_b64", "mask_b64", "prompt"]):
        return jsonify({"error": "Missing required fields: image_b64, mask_b64, prompt"}), 400

    # --- Construct the parameter object for the backend ---
    params = {
        "prompt": data["prompt"],
        "is_inpaint": True,
        "input_image_b64": data["image_b64"],
        "mask_image_b64": data["mask_b64"],
        "num_imgs": 1,
        "ddim_steps": data.get("steps", 50),
        "guidance_scale": data.get("guidance", 7.5),
        "img_width": data.get("width", 512),
        "img_height": data.get("height", 512),
        "seed": data.get("seed", -1), # Use -1 for random seed
    }

    try:
        command = "b2py t2im " + json.dumps(params)
        result = send_command_to_backend(command)

        # Add a URL to retrieve the image
        result['generated_img_url'] = f"/images/{os.path.basename(result['generated_img_path'])}"

        return jsonify(result)

    except (Exception, TimeoutError) as e:
        return jsonify({"error": str(e)}), 500

@app.route('/images/<path:filename>')
def serve_image(filename):
    """Serves the generated images."""
    return send_from_directory(MODELS_DIR, filename)


if __name__ == '__main__':
    start_backend()
    # To make it accessible from Xcode on the same network, host on 0.0.0.0
    app.run(host='0.0.0.0', port=5001)
