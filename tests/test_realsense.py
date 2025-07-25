import pyrealsense2 as rs
import numpy as np
import cv2

#################################################
# RealSense 相机示例
#################################################


# 创建一个 Pipeline 对象，这是管理相机流的主要接口
pipeline = rs.pipeline()

# 创建一个 Config 对象，用于配置你想要的流
config = rs.config()

# ---- 配置流的分辨率、格式和帧率 ----
# 注意：并非所有相机都支持所有分辨率组合。
# 您可以从 Intel RealSense Viewer 工具中查看您的相机支持哪些流。
width = 640
height = 480
fps = 30

# 请求深度数据流
# rs.format.z16 表示16位线性深度值，单位是毫米
config.enable_stream(rs.stream.depth, width, height, rs.format.z16, fps)

# 请求彩色(RGB)数据流
# rs.format.bgr8 是为了与 OpenCV 的默认颜色顺序兼容
config.enable_stream(rs.stream.color, width, height, rs.format.bgr8, fps)

# 创建一个伪彩色映射对象，用于将单通道的深度图转换为彩色的、更易于观察的图像
colorizer = rs.colorizer()

print("正在启动相机流...")
# 启动 Pipeline
profile = pipeline.start(config)
print("相机已启动。按 'ESC' 键退出。")

# 使用 try...finally... 结构确保在程序退出时能安全地停止 pipeline
try:
    while True:
        # 等待一对连贯的帧：深度帧和彩色帧
        # wait_for_frames() 会阻塞程序，直到下一组帧可用
        frames = pipeline.wait_for_frames()
        
        # 从帧集合中获取深度帧和彩色帧
        depth_frame = frames.get_depth_frame()
        color_frame = frames.get_color_frame()
        
        # 如果由于某种原因，某一帧没有捕获到，则跳过此次循环
        if not depth_frame or not color_frame:
            continue
            
        # --- 核心步骤：将 realsense 帧数据转换为 numpy 数组 ---
        # 这样 OpenCV 才能处理它们
        depth_image = np.asanyarray(depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())
        
        # --- 深度图可视化处理 ---
        # 原始深度数据是16位的（uint16），每个像素值代表距离（毫米）
        # 直接显示会是一片漆黑或纯白，需要转换为可视的8位彩色图像
        # 这里我们使用之前创建的 colorizer 对象
        depth_colormap = np.asanyarray(colorizer.colorize(depth_frame).get_data())
        
        # 如果需要将两张图并排显示，可以这样做：
        # np.hstack 是水平堆叠数组
        images = np.hstack((color_image, depth_colormap))

        # --- 使用 OpenCV 显示图像 ---
        # 单独显示两张图
        # cv2.imshow('RealSense Color', color_image)
        # cv2.imshow('RealSense Depth', depth_colormap)
        
        # 或者显示合并后的图像
        cv2.imshow('RealSense Combined', images)


        if cv2.waitKey(1) & 0xFF == 27:
            break

finally:
    # 循环结束后，停止 pipeline
    print("正在停止相机流...")
    pipeline.stop()
    cv2.destroyAllWindows()
    print("已退出。")