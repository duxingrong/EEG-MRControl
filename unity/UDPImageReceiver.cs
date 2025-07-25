// UDPImageReceiver.cs

// Responsibilities:
// Receive image data from PC UDP server

using UnityEngine;
using UnityEngine.UI;
using System;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using System.Collections.Generic;
using TMPro;

public class UDPImageReceiver : MonoBehaviour
{
    [Tooltip("要监听的UDP端口")]
    public int port = 9999;

    [Tooltip("用于显示接收到的图像的UI组件")]
    public RawImage displayImage;


    [Tooltip("用于显示帧率的UI Text组件")]
    public TextMeshProUGUI fpsText; // 用于显示FPS的文本组件


    // 后台接收线程
    private Thread receiveThread;
    // UDP客户端
    private UdpClient client;

    // 用于存储接收到的数据包，使用字典来处理可能乱序到达的数据包
    private Dictionary<int, byte[]> frameChunks;

    // 完整的图像数据
    private byte[] fullFrameData;
    // 线程安全标志，表示是否有新的完整帧数据准备好了
    private volatile bool isFrameReady = false;

    // 预期的总包数
    private int expectedPackets = 0;

    // 用于计算FPS的变量
    private int frameCount = 0;
    private float timer = 0f;

    void Start()
    {
        if (displayImage == null)
        {
            Debug.LogError("请将场景中的RawImage组件拖拽到此脚本的'Display Image'字段上！");
            return;
        }


        if (fpsText == null)
        {
            Debug.LogWarning("FPS Text组件未关联，将无法显示帧率。");
        }


        frameChunks = new Dictionary<int, byte[]>();

        SingleLineConsoleManager.Instance.ShowMessage("开始接收相机实时画面.",Color.yellow);
        receiveThread = new Thread(new ThreadStart(ReceiveData));
        receiveThread.IsBackground = true;
        receiveThread.Start();

        Debug.Log($"开始在端口 {port} 上监听UDP数据...");
    }

    private void ReceiveData()
    {
        client = new UdpClient(port);
        IPEndPoint anyIP = new IPEndPoint(IPAddress.Any, 0);

        while (true)
        {
            try
            {
                byte[] data = client.Receive(ref anyIP);

                if (data == null || data.Length <= 0)
                {
                    continue;
                }

                // 用第一个字节作为类型分发器
                byte packetType = data[0];

                if (packetType == 0x01) // --- 开始信号 ---
                {
                    if (data.Length == 3)
                    {
                        frameChunks.Clear();
                        expectedPackets = (data[1] << 8) | data[2];
                        isFrameReady = false;
                    }
                }
                else if (packetType == 0x02) // --- 结束信号 ---
                {
                    if (data.Length == 1)
                    {
                        if (frameChunks.Count == expectedPackets && expectedPackets > 0)
                        {
                            List<byte> fullDataList = new List<byte>();
                            for (int i = 0; i < expectedPackets; i++)
                            {
                                if (frameChunks.ContainsKey(i)) // 检查键在不在字典中
                                {
                                    fullDataList.AddRange(frameChunks[i]);
                                }
                                else
                                {
                                    Debug.LogWarning($"丢包，帧不完整: 缺少包 #{i}");
                                    fullDataList.Clear();
                                    break;
                                }
                            }

                            if (fullDataList.Count > 0)
                            {
                                fullFrameData = fullDataList.ToArray(); // 可变的list 变成不可变的数组
                                isFrameReady = true;
                            }
                        }
                        frameChunks.Clear();
                        expectedPackets = 0;
                    }
                }
                else if (packetType == 0x00) // --- 数据包 ---
                {
                    if (data.Length > 3) // 1字节类型 + 2字节序号
                    {
                        // 包序号从第2个字节开始
                        int packetIndex = (data[1] << 8) | data[2];

                        // 纯数据从第4个字节开始
                        byte[] chunkData = new byte[data.Length - 3];
                        Array.Copy(data, 3, chunkData, 0, chunkData.Length);

                        frameChunks[packetIndex] = chunkData;
                    }
                }
            }
            catch (Exception e)
            {
                Debug.LogError($"接收数据时发生错误: {e.Message}");
            }
        }
    }

    void Update()
    {
        // 只在主线程中操作Unity的UI和纹理
        // 检查后台线程是否已经准备好了一帧完整的数据
        if (isFrameReady)
        {
            // 重置标志，防止重复进行
            isFrameReady = false;
            if (fullFrameData != null && fullFrameData.Length > 0)
            {
                // 创建一个新的纹理
                Texture2D texture = new Texture2D(2, 2);
                //(2, 2) 在这里只是一个无所谓的占位符，
                //因为 LoadImage() 会立即根据 fullFrameData 的内容重置纹理的真实尺寸。
                //最终图像的像素分辨率（清晰度）是由 fullFrameData 决定的。
                //该图像在屏幕上的最终显示大小（看起来多大）是由 displayImage(RawImage) 的 RectTransform 决定的。
                
                if (texture.LoadImage(fullFrameData))
                {
                    // 将新纹理应用到UI上
                    displayImage.texture = texture;
                    // 成功显示一帧，计数器加1
                    frameCount++;
                }
            }
        }

        timer += Time.deltaTime;
        if (timer >= 1.0f) // 每隔1秒更新一次FPS显示
        {
            if (fpsText != null)
            {
                fpsText.text = "FPS: " + Mathf.RoundToInt(frameCount / timer);
            }
            // 重置计时器和计数器
            timer = 0f;
            frameCount = 0;
        }
    }

    void OnApplicationQuit()
    {
        // 关闭线程和客户端
        if (receiveThread != null && receiveThread.IsAlive)
        {
            receiveThread.Abort();
        }
        if (client != null)
        {
            client.Close();
        }
    }
}