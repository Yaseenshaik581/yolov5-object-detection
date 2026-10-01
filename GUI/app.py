import csv
import json
import pathlib

# ---------- Windows path fix for YOLOv5 ----------
import sys
from pathlib import Path

import cv2
import numpy as np
import torch
from flask import Flask, Response, jsonify, render_template

if sys.platform == "win32":
    pathlib.PosixPath = pathlib.WindowsPath

# ---------- YOLOv5 repo path setup ----------
FILE = Path(__file__).resolve()
ROOT = FILE.parents[1]  # go one level up to yolov5/
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from models.common import DetectMultiBackend
from utils.augmentations import letterbox
from utils.general import non_max_suppression
from utils.torch_utils import select_device

app = Flask(__name__)
camera = cv2.VideoCapture(0)

# ---------- Paths ----------
STATE_PATH = ROOT / "GUI" / "data" / "state.json"
CSV_PATH = ROOT / "GUI" / "data" / "data.csv"
WEIGHTS = ROOT / "best.pt"

# ---------- Mappings ----------
# Display material on the STATUS card
material_map = {
    "egg": "Fragile",
    "medical beaker": "Fragile",
    "apple": "Medium",
    "perfume": "Hard",
    "perfume glass bottle": "Hard",
}

# Fixed properties you wanted to show in the GUI/state.json
# (weights in grams, pressure in bar)
object_props = {
    "egg": {"weight_g": 62, "pressure_bar": 0.37},
    "apple": {"weight_g": 186, "pressure_bar": 0.69},
    "medical beaker": {"weight_g": 79, "pressure_bar": 0.47},
    "perfume": {"weight_g": 214, "pressure_bar": 0.76},
    "perfume glass bottle": {"weight_g": 214, "pressure_bar": 0.76},
}

# ---------- YOLO model ----------
device = select_device("cpu")
model = DetectMultiBackend(WEIGHTS, device=device, dnn=False)
stride, names, pt = model.stride, model.names, model.pt
imgsz = (416, 416)


# ---------- JSON/CSV helpers ----------
def load_state():
    """Load the current GUI state, ensuring expected keys always exist."""
    try:
        with open(STATE_PATH) as f:
            data = json.load(f)
    except Exception:
        data = {}
    data.setdefault("object", "None")
    data.setdefault("material", "Unknown")
    data.setdefault("confidence", 0.0)
    data.setdefault("weight_g", 0)
    data.setdefault("pressure_bar", 0.0)
    return data


def save_state(data):
    """Persist only the expected keys to state.json."""
    allowed = {"object", "material", "confidence", "weight_g", "pressure_bar"}
    to_write = {k: v for k, v in data.items() if k in allowed}
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(to_write, f, indent=4)


def read_csv_data():
    """Optional: live sensor CSV (unchanged from your original)."""
    try:
        with open(CSV_PATH, newline="") as f:
            reader = csv.DictReader(f)
            return next(reader)
    except Exception:
        return {"weight": "0", "pressure": "0", "flex_01": "OFF", "flex_02": "OFF", "flex_03": "OFF", "flex_04": "OFF"}


# ---------- Routes ----------
@app.route("/")
def index():
    state = load_state()
    return render_template("index.html", state=state)


@app.route("/state.json")
def state_json():
    return jsonify(load_state())


@app.route("/live_sensors")
def live_sensors():
    return jsonify(read_csv_data())


# ---------- Video + detection stream ----------
def gen_frames():
    while True:
        success, frame = camera.read()
        if not success:
            break

        # Preprocess for YOLO
        img = letterbox(frame, imgsz, stride=stride, auto=True)[0]
        img = img.transpose((2, 0, 1))[::-1]  # BGR->RGB, to shape [3,H,W]
        img = np.ascontiguousarray(img)
        img_tensor = torch.from_numpy(img).to(device).float() / 255.0
        if img_tensor.ndimension() == 3:
            img_tensor = img_tensor.unsqueeze(0)

        # Inference + NMS
        pred = model(img_tensor, augment=False, visualize=False)
        pred = non_max_suppression(pred, conf_thres=0.35, iou_thres=0.45)

        result_to_save = {}

        for det in pred:
            if len(det):
                for *xyxy, conf, cls in det:
                    class_name = names[int(cls)]
                    key = class_name.lower()

                    # Lookup material/props
                    material = material_map.get(key, "Unknown")
                    props = object_props.get(key, {"weight_g": 0, "pressure_bar": 0.0})

                    # Draw box + label
                    label = f"{class_name} {conf:.2f}"
                    x1, y1, x2, y2 = [int(x.item()) for x in xyxy]
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                    # What we'll write to state.json (this overwrites per frame with last detection)
                    result_to_save = {
                        "object": class_name,
                        "material": material,
                        "confidence": round(conf.item(), 2),
                        "weight_g": props["weight_g"],
                        "pressure_bar": props["pressure_bar"],
                    }

        # Persist detection result to JSON (only when we detected something)
        if result_to_save:
            save_state(result_to_save)

        # Stream frame
        _, buffer = cv2.imencode(".jpg", frame)
        frame_bytes = buffer.tobytes()
        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")


@app.route("/video_feed")
def video_feed():
    return Response(gen_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")


# ---------- Main ----------
if __name__ == "__main__":
    # Make sure data dir exists so /state.json has a place to save to
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Initialize file so template has keys before first detection
    if not STATE_PATH.exists():
        save_state(load_state())
    app.run(debug=True)
