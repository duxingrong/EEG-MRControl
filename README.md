# EEG增强AR交互系统

## 项目概述

这是一个集成脑电图(EEG)信号处理的增强现实(AR)交互系统，通过分析用户的专注度来动态调整交互参数，实现更智能、更人性化的人机交互体验。系统结合了Intel RealSense深度相机、HoloLens 2头显、EEG脑电采集设备和YOLO目标检测算法。

## 核心特性

- **🧠 EEG专注度检测**: 实时分析Alpha/Beta波能量比，量化用户专注度
- **👁️ 眼动交互**: 基于HoloLens 2眼动追踪的目标选择
- **🎯 智能适应**: 根据专注度动态调整目标选择时间
- **🔍 实时目标检测**: 使用YOLOv8进行实时物体分割和识别
- **📡 多模态通信**: TCP/UDP双协议支持PC与HoloLens通信


## 交互流程详解

### 阶段1: 空闲等待
- 系统启动后进入空闲模式
- PC持续向HoloLens发送实时视频流
- **操作**: 按下空格键开始新任务，ESC键退出

### 阶段2: 握手与初始化
- PC发送`start_signal`激活HoloLens UI
- PC开始实时物体分割处理
- 等待HoloLens确认信号

### 阶段3: 指令接收
- HoloLens显示可选指令（如"eat", "drink"等）
- 用户通过眼动选择指令
- HoloLens发送选中指令给PC

### 阶段4: EEG增强交互
这是系统的核心阶段，展现了EEG增强的价值：

1. **实时专注度计算**
   ```python
   focus_score = eeg_processor.get_focus_score()
   dynamic_select_time = BASE_DWELL_TIME - (focus_score * MAX_REDUCTION)
   ```

2. **眼动目标检测**
   - 接收HoloLens眼动坐标
   - 与YOLO分割结果进行空间匹配
   - 实时高亮用户注视的物体

3. **自适应选择机制**
   - **专注度高** → 选择时间缩短 → 快速响应
   - **专注度低** → 选择时间延长 → 避免误操作

### 阶段5: 任务执行
- 使用CSRT跟踪器锁定选中目标
- 执行5秒钟的模拟任务
- 实时显示跟踪状态

## EEG信号处理原理

### 专注度算法

系统采用经典的Alpha/Beta波分析方法：

```python
def get_focus_score(self):
    # 1. 获取最近2秒的EEG数据
    recent_data = eeg_data[OZ_CHANNEL, -required_samples:]
    
    # 2. 计算功率谱密度
    freqs, psd = signal.welch(recent_data, self.srate, window='hann')
    
    # 3. 提取频带能量
    alpha_power = get_band_power('Alpha')  # 8-13Hz
    beta_power = get_band_power('Beta')    # 13-30Hz
    
    # 4. 计算专注度比值
    ratio = beta_power / alpha_power
    
    # 5. 归一化到0-1范围
    normalized_score = (np.tanh(ratio - 1) + 1) / 2
    
    return normalized_score
```

### 频段定义
- **Alpha波 (8-13Hz)**: 放松、安静状态
- **Beta波 (13-30Hz)**: 专注、活跃思维状态
- **专注度**: Beta/Alpha比值越高表示越专注

## 网络通信协议

### TCP控制协议
所有TCP消息采用JSON格式：
```json
{
    "type": "message_type",
    "payload": "message_content"
}
```

**消息类型**:
- `start_signal`: PC→HoloLens，启动信号
- `ack`: HoloLens→PC，确认信号
- `command`: HoloLens→PC，用户指令
- `gaze`: HoloLens→PC，眼动坐标
- `selection_confirmed`: PC→HoloLens，选择确认
- `subtitle`: PC→HoloLens，字幕显示

### UDP图像传输协议
采用分包传输机制：
- 包头：`0x01` + 总包数(2字节)
- 数据包：`0x00` + 包序号(2字节) + 数据
- 包尾：`0x02`

## 配置参数说明

### EEG参数
```python
# EEG设备配置
SAMPLING_RATE = 500        # 采样率500Hz
NUM_EEG_CHANNELS = 8       # 8个EEG通道
TARGET_CHANNEL_INDEX = 5   # OZ通道索引

# 专注度计算参数
BASE_DWELL_TIME = 2.5      # 基础停留时间(秒)
MAX_REDUCTION = 1.2        # 最大时间缩减(秒)
```

### 交互参数
```python
# 目标跟踪参数
IOU_THRESHOLD = 0.3        # IoU匹配阈值
TRACK_PATIENCE = 15        # 跟踪丢失容忍帧数
MIN_HITS = 3              # 最小稳定帧数

# 交互时间参数
HOVER_TO_HIGHLIGHT_TIME = 1.0  # 高亮显示时间
```


## 致谢

感谢以下开源项目的支持：
- [Ultralytics YOLO](https://github.com/ultralytics/ultralytics)
- [Intel RealSense SDK](https://github.com/IntelRealSense/librealsense)
- [OpenCV](https://opencv.org/)
- [SciPy](https://scipy.org/)

---

**注意**: 本系统仅用于研究和教育目的。在使用EEG设备时，请遵循相关的安全规范和伦理准则。