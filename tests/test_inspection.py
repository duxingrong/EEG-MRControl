import cv2
import pyrealsense2 as rs
import numpy as np
from ultralytics import YOLO




# --- 1. 初始化模型 ---
# 加载一个官方预训练好的YOLO11n模型。
try:
    model = YOLO('yolo11n.pt')
except Exception as e:
    print(f"加载YOLO模型失败，请检查网络连接或文件路径。错误: {e}")
    exit()

# --- 2. 初始化 RealSense 相机 ---
pipeline = rs.pipeline()
config = rs.config()
# 为机启用彩色图像流
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

try:
    # 启动相机流
    pipeline.start(config)
    print("RealSense相机已启动，按 'ESC' 键退出。")

    while True:
        # --- 3. 获取相机图像 ---
        # 等待并获取一帧数据（包含彩色图）
        frames = pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()
        if not color_frame:
            continue

        # 将图像数据转换为Numpy数组，这是OpenCV和YOLO可以处理的格式
        # RealSense输出的已经是BGR格式，正好是YOLO和OpenCV习惯的格式
        frame = np.asanyarray(color_frame.get_data())

        # --- 4. 使用YOLO进行物体检测 ---
        # 直接将图像帧传入模型进行预测
        results = model(frame)

        """ 
        # --- 5. 绘制结果并显示 ---
        # results[0].plot() 自动在原始图像上画出所有的边界框、类别名称和置信度。
        # annotated_frame = results[0].plot()
        """


        # --- 5. 解析结果，获取坐标并手动绘图 ---
        # 遍历检测到的每一个物体
        for box in results[0].boxes:
            # --- 5.1 提取边界框坐标 ---
            # box.xyxy[0] 返回一个包含[x1, y1, x2, y2]的张量
            x1, y1, x2, y2 = map(int, box.xyxy[0])

            # --- 5.2 计算中心点坐标 ---
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2

            # --- 5.3 获取类别和置信度 ---
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])
            class_name = model.names[class_id]
            
            # --- 5.4 打印你需要的信息 ---
            # 这是满足你需求的核心部分：在控制台打印中心坐标
            print(f"检测到物体: {class_name}, 置信度: {confidence:.2f}, 中心坐标: ({center_x}, {center_y})")

            # --- 5.5 手动在图像上绘制 ---
            # 绘制边界框
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            # 绘制中心点（画一个红色的小圆）
            cv2.circle(frame, (center_x, center_y), 3, (0, 0, 255), -1)
            # 准备标签文本
            label = f"{class_name} {confidence:.2f}"
            # 在边界框上方绘制标签背景
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        
        cv2.imshow('RealSense + YOLO11n 物体检测', frame)

        # 检测按键
        if cv2.waitKey(1) & 0xFF == 27:
            print("正在关闭...")
            break
        
finally:
    # --- 6. 清理和收尾 ---
    # 停止相机流
    pipeline.stop()
    # 关闭所有OpenCV创建的窗口
    cv2.destroyAllWindows()
    print("程序已关闭。")