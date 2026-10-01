import pathlib
import sys
import json
import cv2
import torch
import numpy as np
from pathlib import Path

# ✅ Fix PosixPath issue for Windows
if sys.platform == "win32":
    pathlib.PosixPath = pathlib.WindowsPath

# ✅ YOLOv5 path setup
FILE = Path(__file__).resolve()
ROOT = FILE.parents[0]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from models.common import DetectMultiBackend
from utils.general import non_max_suppression
from utils.torch_utils import select_device
from utils.augmentations import letterbox

# ✅ Case-insensitive Material mapping (all lowercase keys)
material_map = {
    'egg': 'Fragile',
    'medical beaker': 'Fragile',
    'apple': 'Medium',
    'perfume': 'Hard'
}

# ✅ Load model
weights = 'best.pt'
device = select_device('cpu')
model = DetectMultiBackend(weights, device=device, dnn=False)
stride, names, pt = model.stride, model.names, model.pt

# ✅ Lower image size for better performance
imgsz = (416, 416)

# ✅ Open webcam with set resolution
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# ✅ JSON file path
state_path = ROOT / 'GUI' / 'data' / 'state.json'

while True:
    ret, frame = cap.read()
    if not ret:
        break

    img = letterbox(frame, imgsz, stride=stride, auto=True)[0]
    img = img.transpose((2, 0, 1))[::-1]  # BGR to RGB, HWC to CHW
    img = np.ascontiguousarray(img)

    img_tensor = torch.from_numpy(img).to(device)
    img_tensor = img_tensor.float() / 255.0
    if img_tensor.ndimension() == 3:
        img_tensor = img_tensor.unsqueeze(0)

    # 🔍 Inference
    pred = model(img_tensor, augment=False, visualize=False)
    pred = non_max_suppression(pred, conf_thres=0.35, iou_thres=0.45)

    result_to_save = {}

    for det in pred:
        if len(det):
            for *xyxy, conf, cls in det:
                class_name = names[int(cls)]
                class_key = class_name.lower()
                material = material_map.get(class_key, "Unknown")
                label = f"{class_name} {conf:.2f}"  # ❌ No material on display

                xyxy = [int(x.item()) for x in xyxy]
                cv2.rectangle(frame, (xyxy[0], xyxy[1]), (xyxy[2], xyxy[3]), (0, 255, 0), 2)
                cv2.putText(frame, label, (xyxy[0], xyxy[1] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                # ✅ Save detected object info to JSON
                result_to_save = {
                    "object": class_name,
                    "material": material,
                    "confidence": round(conf.item(), 2)
                }

    # ✅ Update state.json if detection exists
    if result_to_save:
        try:
            with open(state_path, 'w') as f:
                json.dump(result_to_save, f, indent=4)
        except Exception as e:
            print(f"[WARNING] Couldn't write to JSON: {e}")

    # 📷 Show live detection
    cv2.imshow('Live Detection - Press Q to Quit', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# ✅ Clean up
cap.release()
cv2.destroyAllWindows()
