# -*- coding: utf-8 -*-
"""
EEG Processor Module

- Encapsulates EEG connection and data processing logic.
- Calculates a real-time focus score based on the Beta/Alpha wave power ratio.
- Can be run standalone for testing purposes.
"""

import time
import numpy as np
from scipy import signal
from scipy.integrate import simps
from neuracle_lib.dataServer import DataServerThread

class EEGProcessor:
    def __init__(self, srate=500, n_chan=9, t_buffer=15):
        """
        Initializes the EEG Processor.
        Args:
            srate (int): Sampling rate of the EEG device.
            n_chan (int): Total number of channels from the EEG device.
            t_buffer (int): Size of the data buffer in seconds.
        """
        print("[EEG] 初始化EEG处理器...")
        self.srate = srate
        self.n_chan = n_chan
        self.t_buffer = t_buffer
        
        #  Define the filter bank 
        self.bands = {'Alpha': (8.0, 13.0), 'Beta': (13.0, 30.0)}
        
        # Preset OZ-channel index 
        self.TARGET_CHANNEL_INDEX = 5  #(O1,O2,P3,P4,PZ,OZ,P7,P8)

        self.data_server = None
        self.is_connected = False

    def connect(self, ip="127.0.0.1", port=8712):
        """
        Connects to the EEG data server.
        Args:
            ip (str): IP address of the EEGRecorder software.
            port (int): Port of the EEGRecorder software.
        Returns:
            bool: True if connection is successful, False otherwise.
        """
        print(f"[EEG] 正在连接到 {ip}:{port}...")
        try:
            self.data_server = DataServerThread(device='Neuracle', n_chan=self.n_chan,
                                                srate=self.srate, t_buffer=self.t_buffer)
            if self.data_server.connect(hostname=ip, port=port):
                 raise ConnectionError("连接调用返回错误状态")
            
            self.data_server.start()
            self.is_connected = True
            print("[EEG] 连接成功并已启动！")
            return True
        except Exception as e:
            print(f"[EEG] 连接失败: {e}")
            self.is_connected = False
            return False

    def get_focus_score(self, window_sec=2):
        """
        Calculates the real-time focus score.
        This is the core method that encapsulates all signal processing.
        Args:
            window_sec (int): The duration of recent data (in seconds) to analyze.
        Returns:
            float: A normalized focus score between 0.0 and 1.0.
        """
        if not self.is_connected:
            return 0.5  # Return a neutral default value if not connected

        eeg_data = self.data_server.GetBufferData()
        
        # Ensure sufficient data for analysis
        required_samples = int(self.srate * window_sec)
        if eeg_data is None or eeg_data.shape[1] < required_samples:
            return 0.5  # Return default value if data is insufficient

        # 1. Data selection:choose the most recent window and target channel
        recent_data = eeg_data[self.TARGET_CHANNEL_INDEX, -required_samples:]

        # 2. Compute the power spectral density (PSD)
        win = signal.get_window('hann', self.srate) # Apply a Hann window
        freqs, psd = signal.welch(recent_data, self.srate, window=win)

        # 3. Calculate the absolute power within the specified frequency bands
        def get_band_power(band):
            low, high = self.bands[band]
            idx_band = np.logical_and(freqs >= low, freqs <= high)
            # Use Simpson's rule integration for more accurate band-power estimation
            power = simps(psd[idx_band], freqs[idx_band])
            return power

        alpha_power = get_band_power('Alpha')
        beta_power = get_band_power('Beta')
        
        # 4. Calculate the energy ratio
        if alpha_power < 1e-10: # Avoid division by zero
            alpha_power = 1e-10
        ratio = beta_power / alpha_power

        # 5. Normalization
        # Use tanh function to map the fluctuating ratio to a smooth 0-1 range
        # When ratio = 1,the focus level is neutral(0.5)
        # larger ratios yield higher focus
        normalized_score = (np.tanh(ratio - 1) + 1) / 2
        
        return normalized_score

    def stop(self):
        """Stops the data acquisition thread safely."""
        if self.data_server and self.is_connected:
            print("[EEG] 停止EEG处理器...")
            self.data_server.stop()
            self.is_connected = False



if __name__ == '__main__':
    
    
    AMP_IP = "127.0.0.1"
    AMP_PORT = 8712
    SAMPLING_RATE = 500
    NUM_EEG_CHANNELS = 8
    # 8 EEG + 1 event channel=9
    NUM_CHANNELS_TOTAL = NUM_EEG_CHANNELS + 1 
    
    processor = EEGProcessor(srate=SAMPLING_RATE, n_chan=NUM_CHANNELS_TOTAL)
    
    try:
        if processor.connect(ip=AMP_IP, port=AMP_PORT):
            print("\n--- 开始测试专注度算法 (将持续60秒) ---")
            print("请尝试放松或集中注意力，观察分数变化...")
            
            start_time = time.time()
            while time.time() - start_time < 60:
                # Acquire the focus score
                focus = processor.get_focus_score()
                
                # Visualize and print 
                bar_length = 50
                filled_length = int(bar_length * focus)
                bar = '█' * filled_length + '-' * (bar_length - filled_length)
                print(f'专注度: {focus:.2f} |{bar}|')
                
                time.sleep(0.5) # Update every half-second
    
    finally:
        processor.stop()
        print("\n--- 测试结束，程序已安全退出。 ---")