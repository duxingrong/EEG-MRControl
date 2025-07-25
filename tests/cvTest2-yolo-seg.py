'''
yolo自动分割区域，用眼神点选
yolo numpy opencv之间 存在一些包的兼容性，安装时注意
不增加深度估计 效果也能接受的
'''
import cv2
import pyrealsense2 as rs
import numpy as np
import time
from ultralytics import YOLO

# 初始化 RealSense 管道
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)

pipeline.start(config)
align = rs.align(rs.stream.color)

# 初始化分割模型（YOLOv8-seg）
model = YOLO("assets/yolov8n-seg.pt")  # 请确保模型文件存在

# 状态变量
detected_masks = []
detected_boxes = []
highlight_mask = None
highlight_index = -1
roi_selected = False
tracker = None
frame = None
mouse_position = (-1, -1)
mouse_down_time = 0
HOVER_THRESHOLD = 1.0  # 鼠标停留时间阈值（秒）

cv2.namedWindow("RealSense Tracking")

# 鼠标事件：移动更新位置，点击切换追踪目标
def mouse_callback(event, x, y, flags, param):
    global mouse_position, mouse_down_time, tracker, roi_selected, highlight_mask
    if event == cv2.EVENT_MOUSEMOVE:
        if (x, y) != mouse_position:
            mouse_position = (x, y)
            mouse_down_time = time.time()
    elif event == cv2.EVENT_LBUTTONDOWN:
        if highlight_mask is not None:
            ys, xs = np.where(highlight_mask)
            if len(xs) > 0 and len(ys) > 0:
                x1, y1, x2, y2 = np.min(xs), np.min(ys), np.max(xs), np.max(ys)
                tracker = cv2.TrackerCSRT_create()
                tracker.init(frame, (x1, y1, x2 - x1, y2 - y1))
                roi_selected = True
                print(f"点击追踪目标：({x1},{y1}) -> ({x2},{y2})")

cv2.setMouseCallback("RealSense Tracking", mouse_callback)

print("鼠标停留在物体上 1 秒将高亮目标，点击后开始追踪，ESC 退出")

while True:
    frames = pipeline.wait_for_frames()
    aligned_frames = align.process(frames)
    color_frame = aligned_frames.get_color_frame()
    if not color_frame:
        continue

    frame = np.asanyarray(color_frame.get_data()).astype(np.uint8)

    # 分割识别
    results = model(frame, verbose=False)[0]
    detected_masks = []
    detected_boxes = []
    highlight_mask = None
    highlight_index = -1

    if results.masks is not None:
        masks = results.masks.data.cpu().numpy()  # shape: [N, H, W]
        boxes = results.boxes.xyxy.cpu().numpy()  # shape: [N, 4]

        for i in range(len(masks)):
            mask = masks[i] > 0.5
            detected_masks.append(mask)
            detected_boxes.append(boxes[i])

            # 绘制蓝色轮廓
            mask_uint8 = (mask * 255).astype(np.uint8)
            contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(frame, contours, -1, (255, 0, 0), 1)

            # 计算中心点并标记目标编号
            M = cv2.moments(mask_uint8)
            if M["m00"] > 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                cv2.putText(frame, f"#{i}", (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

    # 判断鼠标是否悬停在某个 mask 上超过阈值
    mx, my = mouse_position
    hover_duration = time.time() - mouse_down_time
    if 0 <= mx < frame.shape[1] and 0 <= my < frame.shape[0] and hover_duration > HOVER_THRESHOLD:
        for i, mask in enumerate(detected_masks):
            if mask[my, mx]:
                highlight_mask = mask
                highlight_index = i
                break

    # 高亮分割区域（绿色叠加 + 轮廓）
    if highlight_mask is not None:
        frame[highlight_mask] = frame[highlight_mask] * 0.5 + np.array([0, 255, 0]) * 0.5

        # 绘制绿色轮廓线加强视觉效果
        mask_uint8 = (highlight_mask * 255).astype(np.uint8)
        contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(frame, contours, -1, (0, 255, 0), 2)

    # 显示追踪框（黄色）
    if roi_selected and tracker is not None:
        success, bbox = tracker.update(frame)
        if success:
            x, y, w, h = [int(v) for v in bbox]
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 255), 2)
            cv2.putText(frame, "Tracking", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        else:
            cv2.putText(frame, "Lost", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

    # 显示图像
    cv2.imshow("RealSense Tracking", frame)
    key = cv2.waitKey(1)
    if key == 27:
        break

