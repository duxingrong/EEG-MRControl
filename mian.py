# -*- coding: utf-8 -*-

import pyrealsense2 as rs
import numpy as np
import cv2
import time
import json
import threading
from ultralytics import YOLO

import ar_system.Img_sender as Img_sender
from ar_system.tcp_manager import TCPClient
from ar_system.eeg_processor import EEGProcessor  

# please check the file path correctly


USE_EEG = False # use EEG singal
handshake_event = threading.Event()  
hololens_command_received = None  
gaze_position = (-1, -1)



def calculate_iou(box1, box2):
    """Calculate the IoU of two rectangles for target tracking"""
    x1, y1, x2, y2 = box1
    x3, y3, x4, y4 = box2
    
    xi1 = max(x1, x3)
    yi1 = max(y1, y3)
    xi2 = min(x2, x4)
    yi2 = min(y2, y4)
    
    inter_area = max(0, xi2 - xi1) * max(0, yi2 - yi1)
    
    box1_area = (x2 - x1) * (y2 - y1)
    box2_area = (x4 - x3) * (y4 - y3)
    
    union_area = box1_area + box2_area - inter_area
    
    iou = inter_area / union_area if union_area > 0 else 0
    return iou

def handle_hololens_acknowledgment(payload):
    """Handle confirmation messages from Hololens2"""
    if payload == "start_signal_received":
        print("[CALLBACK] HoloLens 已确认，UI准备就绪。")
        handshake_event.set()

def handle_hololens_command(payload):
    """Process incomming command messages from Hololens2"""
    global hololens_command_received
    print(f"[CALLBACK] 收到HoloLens指令: '{payload}'")
    hololens_command_received = payload

def handle_gaze_position(payload):
    """Process gaze coordinate messages from Hololens2"""
    global gaze_position
    try:
        pos_data = json.loads(payload)
        gaze_position = (pos_data['x'], pos_data['y'])
    except (json.JSONDecodeError, KeyError):
        pass



if __name__ == "__main__":

    HOLOLENS_IP = "127.0.0.1"
    UDP_PORT = 9999
    TCP_PORT = 9998
    WIDTH, HEIGHT, FPS = 640, 480, 30

    
    eeg_processor = None
    if USE_EEG:
        print("[INFO] 正在尝试启用EEG增强模式...")
        eeg_processor = EEGProcessor(srate=500, n_chan=9) 
        if not eeg_processor.connect(ip="127.0.0.1", port=8712):
            print("[警告] EEG模块连接失败，系统将以无脑电模式运行。")
            eeg_processor = None
    else:
        print("[INFO] EEG功能已禁用，系统将以纯视觉模式运行。")


    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.color, WIDTH, HEIGHT, rs.format.bgr8, FPS)
    pipeline.start(config)
    
    tcp_server = TCPClient(HOLOLENS_IP, TCP_PORT)
    tcp_server.register_callback("ack", handle_hololens_acknowledgment)
    tcp_server.register_callback("command", handle_hololens_command)
    tcp_server.register_callback("gaze", handle_gaze_position)
    tcp_server.start()

    print("[INFO] 系统初始化完成。等待HoloLens连接...")
    while not tcp_server.is_client_connected():
        time.sleep(1)
    print("[INFO] HoloLens 已成功连接！")

    try:
        while True:
            # =================================================
            # Phase 1: Idle and Waiting 
            # =================================================
            print("\n----------------------------------------------------")
            print("[STATE] 空闲模式: 按下【空格键】开始新一轮任务，按【ESC】退出。")
            while True:
                frames = pipeline.wait_for_frames()
                color_frame = frames.get_color_frame()
                if not color_frame: continue
                idle_image = np.asanyarray(color_frame.get_data())
                Img_sender.send_image(idle_image, HOLOLENS_IP, UDP_PORT)
                cv2.putText(idle_image, "IDLE: Press SPACE to Start", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                cv2.imshow("PC Main Control", idle_image)
                key = cv2.waitKey(1) & 0xFF
                if key == 27: raise KeyboardInterrupt
                if key == 32: break
            
            # =================================================
            # Phase 2&3: Handshake and Await Commands
            # =================================================
            print("\n[STATE] 任务启动: 正在与HoloLens进行握手...")
            hololens_command_received = None
            handshake_event.clear()
            tcp_server.send("start_signal", "")
            if not handshake_event.wait(timeout=5.0):
                print("[ERROR] 握手超时，返回空闲模式。")
                continue
            
            print("[STATE] 握手成功: 等待用户指令...")
            while hololens_command_received is None:
                frames = pipeline.wait_for_frames()
                color_frame = frames.get_color_frame()
                if not color_frame: continue
                wait_image = np.asanyarray(color_frame.get_data())
                Img_sender.send_image(wait_image, HOLOLENS_IP, UDP_PORT)
                cv2.putText(wait_image, "WAITING FOR COMMAND...", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
                cv2.imshow("PC Main Control", wait_image)
                if cv2.waitKey(1) & 0xFF == 27: raise KeyboardInterrupt

            # =================================================
            # Phase 4: Real-time EEG-integrated Interaction
            # =================================================
            print(f"[STATE] 收到指令'{hololens_command_received}': 进入【EEG增强】实时交互模式...")
            tcp_server.send("subtitle", "请用您的视线选择一个目标。")

            is_object_selected = False
            final_selected_tracker = None
            tracked_objects = {}
            next_track_id = 0
            
            gaze_hover_start_time = 0
            highlighted_track_id = -1
            HOVER_TO_HIGHLIGHT_TIME = 1.0
            
            
            BASE_DWELL_TIME = 2.5       # Default selection time 
            MAX_REDUCTION = 1.2         # Reduced duration when attention is maximal
            
            try:
                seg_model = YOLO("assets/yolov8n-seg.pt")
                print("[INFO] 分割模型yolov8n-seg.pt加载成功！")
            except Exception as e:
                print(f"[ERROR] 加载分割模型失败: {e}。")
                continue

            while not is_object_selected:
                frames = pipeline.wait_for_frames()
                color_frame = frames.get_color_frame()
                if not color_frame: continue
                frame = np.asanyarray(color_frame.get_data())

                # --- Phase 4.1: Fetch the detection results for the current frame ---
                results = seg_model(frame, verbose=False)[0]
                current_detections = []
                if results.masks is not None:
                    for i in range(len(results.masks.data)):
                        current_detections.append({
                            "box": results.boxes.xyxy[i].cpu().numpy().flatten(),
                            "mask": results.masks.data[i].cpu().numpy() > 0.5
                        })

                # --- Phase 4.2: Update the Object-tracking list  ---
                unmatched_detections = list(range(len(current_detections)))
                
                # Update the coordinates of existing objects 
                for track_id, tobj in list(tracked_objects.items()):
                    tobj["last_seen"] += 1
                    best_match_iou = 0.3
                    best_match_idx = -1
                    for det_idx in unmatched_detections:
                        iou = calculate_iou(tobj["box"], current_detections[det_idx]["box"])
                        if iou > best_match_iou:
                            best_match_iou = iou
                            best_match_idx = det_idx
                    if best_match_idx != -1:
                        tracked_objects[track_id].update({
                            "box": current_detections[best_match_idx]["box"],
                            "mask": current_detections[best_match_idx]["mask"],
                            "last_seen": 0, "hits": tobj["hits"] + 1
                        })
                        unmatched_detections.remove(best_match_idx)
                
                # Delete old objects
                for track_id, tobj in list(tracked_objects.items()):
                    if tobj["last_seen"] > 15: # patience is 15
                        del tracked_objects[track_id]
                
                # Add new objects
                for det_idx in unmatched_detections:
                    tracked_objects[next_track_id] = {
                        "box": current_detections[det_idx]["box"],
                        "mask": current_detections[det_idx]["mask"],
                        "last_seen": 0, "hits": 1
                    }
                    next_track_id += 1

                # --- Phase 4.3: Render EEG-enhanced interactions ---
                is_gazing_at_object = False
                
                # --- At the start of the interaction loop,get the focus score ---
                focus_score = 0.5 # A safe default value 
                if eeg_processor: 
                    focus_score = eeg_processor.get_focus_score()
                
                # --- Calculate the current frame's dynamic selection time based on focus level ---
                dynamic_select_time = BASE_DWELL_TIME - (focus_score * MAX_REDUCTION)

                for track_id, tobj in tracked_objects.items():
                    # interact only with objects that have appeared stably for at least three consecutive frames
                    if tobj["hits"] < 3: continue 

                    mask = tobj["mask"]
                    mask_uint8 = (mask * 255).astype(np.uint8)
                    contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    cv2.drawContours(frame, contours, -1, (255, 0, 0), 2) # blue contour

                    mx, my = gaze_position
                    if 0 <= my < frame.shape[0] and 0 <= mx < frame.shape[1] and mask[my, mx]:
                        is_gazing_at_object = True
                        if highlighted_track_id != track_id:
                            highlighted_track_id = track_id
                            gaze_hover_start_time = time.time()
                        
                        hover_duration = time.time() - gaze_hover_start_time
                        
                        # Calculate the progress bar using dynamic timing
                        progress = min(hover_duration / dynamic_select_time, 1.0)
                        bar_width = 100; bar_height = 10
                        bar_x = mx + 20; bar_y = my - 20
                        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (100, 100, 100), -1)
                        fill_color = (0, 255, 0) if hover_duration > HOVER_TO_HIGHLIGHT_TIME else (255, 255, 255) 
                        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + int(bar_width * progress), bar_y + bar_height), fill_color, -1)
                        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (255, 255, 255), 1)
                        
                        # Use dynamic time for judgment
                        if hover_duration > dynamic_select_time:
                            print(f"此时专注度为{focus_score}")
                            is_object_selected = True
                            ys, xs = np.where(mask)
                            x1, y1, x2, y2 = np.min(xs), np.min(ys), np.max(xs), np.max(ys)
                            final_selected_tracker = cv2.TrackerCSRT_create()
                            final_selected_tracker.init(frame, (x1, y1, x2 - x1, y2 - y1))
                            tcp_server.send("selection_confirmed", "")
                            tcp_server.send("subtitle", f"已锁定目标，准备执行任务。")
                            break
                        elif hover_duration > HOVER_TO_HIGHLIGHT_TIME:
                            # highlight object 
                            frame[mask] = frame[mask] * 0.5 + np.array([0, 255, 0]) * 0.5
                
                if not is_gazing_at_object:
                    highlighted_track_id = -1
                if is_object_selected: break
                
                Img_sender.send_image(frame, HOLOLENS_IP, UDP_PORT)
                cv2.imshow("PC Main Control", frame)
                if cv2.waitKey(1) & 0xFF == 27: raise KeyboardInterrupt

            # =================================================
            # Phase 5: Execute the final task 
            # =================================================
            if final_selected_tracker:
                print(f"\n[ACTION] 任务执行: 实时追踪已锁定的目标...")
                task_duration = 5.0 
                task_start_time = time.time()
                
                while time.time() - task_start_time < task_duration:
                    frames = pipeline.wait_for_frames()
                    color_frame = frames.get_color_frame()
                    if not color_frame: continue
                    frame = np.asanyarray(color_frame.get_data())

                    # Update the tracker
                    success, bbox = final_selected_tracker.update(frame)

                    # Render the tracking results
                    if success:
                        x, y, w, h = [int(v) for v in bbox]
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 255), 3) # yellow rectangles
                        cv2.putText(frame, "EXECUTING TASK", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                    else:
                        cv2.putText(frame, "TRACKING LOST", (100, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

                    # Keep the display updated
                    Img_sender.send_image(frame, HOLOLENS_IP, UDP_PORT)
                    cv2.imshow("PC Main Control", frame)
                    if cv2.waitKey(1) & 0xFF == 27: raise KeyboardInterrupt
                
                print("[SUCCESS] 任务执行完毕。")
                tcp_server.send("subtitle", "任务已完成。")
                time.sleep(2) 
            else:
                print("[WARNING] 未选择任何物体或目标丢失，任务中止。")

    except KeyboardInterrupt:
        print("\n[INFO] 用户请求退出程序。")
    finally:
        # =================================================
        # Safely Clean up all modules
        # =================================================
        print("[INFO] 正在关闭所有服务...")
        pipeline.stop()
        tcp_server.stop()
        if eeg_processor: 
            eeg_processor.stop()
        cv2.destroyAllWindows()
        print("[INFO] 程序已安全退出。")