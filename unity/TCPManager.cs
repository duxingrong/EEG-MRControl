// TCPManager.cs 

// Responsibilities:
// 1. Provide a global,singleton TCP communication interface
// 2. Act as a TCP server: listen for and maintain the connection from the PC client
// 3. Receive PC messages (e.g start_singal,selection_confirmed,subtitle) and broadcast them via events
// 4. Expose clear public methods so other scripts can send messages (e.g ack,command,gaze)to the PC

using UnityEngine;
using System;
using System.Net; 
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Collections.Concurrent;




public class TCPManager : MonoBehaviour
{
    #region 事件定义 
    public static event Action OnStartSignalReceived;
    public static event Action<string> OnSubtitleReceived;
    public static event Action OnSelectionConfirmed;
    #endregion

    #region 内部数据结构 
    [System.Serializable]
    private class MessageEnvelope
    {
        public string type;
        public string payload;
    }

    [System.Serializable]
    private class GazePayload
    {
        public int x;
        public int y;
    }
    #endregion

    #region 单例模式
    private static TCPManager _instance;
    public static TCPManager Instance
    {
        get
        {
            if (_instance == null)
            {
                GameObject obj = new GameObject("TCPManager");
                _instance = obj.AddComponent<TCPManager>();
            }
            return _instance;
        }
    }
    #endregion

    #region 网络配置与变量 
    [Header("服务器网络设置")]
    public int serverPort = 9998; 

    private TcpListener _listener;
    private TcpClient _client; 
    private NetworkStream _stream;
    private Thread _listenThread;
    private bool _isClientConnected = false;
    private readonly ConcurrentQueue<string> _receivedMessages = new ConcurrentQueue<string>();
    private bool _isAppQuitting = false;
    #endregion

    #region Unity生命周期方法 
    private void Awake()
    {
        if (_instance != null && _instance != this)
        {
            Destroy(this.gameObject);
        }
        else
        {
            _instance = this;
            DontDestroyOnLoad(this.gameObject);
        }
    }

    private void Start()
    {
        
        StartServer();
    }

    void Update()
    {
        // 在主线程处理消息队列 
        while (_receivedMessages.TryDequeue(out string message))
        {
            ProcessMessage(message);
        }
    }

    private void OnApplicationQuit()
    {
        _isAppQuitting = true;
        Cleanup();
    }

    private void OnDestroy()
    {
        Cleanup();
    }
    #endregion

    #region 公共发送接口
    public void SendAcknowledgement(string payload) { Send("ack", payload); }
    public void SendCommand(string command) { Send("command", command); }
    public void SendGazePosition(Vector2Int coords)
    {
        GazePayload payload = new GazePayload { x = coords.x, y = coords.y };
        string payloadJson = JsonUtility.ToJson(payload);
        Send("gaze", payloadJson);
    }
    #endregion

    #region 核心网络逻辑 
    private void StartServer()
    {
        if (_listenThread != null && _listenThread.IsAlive) return;

        _listenThread = new Thread(() =>
        {
            try
            {
                _listener = new TcpListener(IPAddress.Any, serverPort);
                _listener.Start();
                _isAppQuitting = false;
                Debug.Log($"[TCP] 服务器已在端口 {serverPort} 启动。正在等待客户端连接...");

                while (!_isAppQuitting)
                {
                    // AcceptTcpClient() is a blocking method that waits here for a client to connect
                    _client = _listener.AcceptTcpClient();

                    // Once a client connects
                    _stream = _client.GetStream();
                    _isClientConnected = true;
                    var clientEndpoint = _client.Client.RemoteEndPoint.ToString();
                    Debug.Log($"[TCP] <color=green>客户端已连接！来自: {clientEndpoint}</color>");

                    // Start the receive loop for this client
                    ReceiveLoop();

                    // 如果 ReceiveLoop 退出 (通常因为断线), 则清理并准备接受下一个连接
                    _isClientConnected = false;
                    Debug.LogWarning($"[TCP] 客户端 {clientEndpoint} 已断开。正在等待新的连接...");
                }
            }
            catch (SocketException ex) when (ex.SocketErrorCode == SocketError.Interrupted)
            {
                // 当我们调用 _listener.Stop() 时，会触发此异常，属于正常关闭流程
                Debug.Log("[TCP] 监听器已正常停止。");
            }
            catch (Exception e)
            {
                Debug.LogError($"[TCP] 服务器线程出错: {e.Message}");
            }
        });
        _listenThread.IsBackground = true;
        _listenThread.Start();
    }

    private void ReceiveLoop()
    {
        try
        {
            byte[] lengthPrefix = new byte[4];
            while (_isClientConnected && !_isAppQuitting && (_stream?.CanRead ?? false))
            {
                int bytesRead = _stream.Read(lengthPrefix, 0, 4);
                if (bytesRead < 4) break; 

                if (BitConverter.IsLittleEndian)
                {
                    Array.Reverse(lengthPrefix);
                }
                int messageLength = BitConverter.ToInt32(lengthPrefix, 0);

                if (messageLength <= 0) continue;

                byte[] messageBytes = new byte[messageLength];
                int totalBytesRead = 0;
                while (totalBytesRead < messageLength)
                {
                    bytesRead = _stream.Read(messageBytes, totalBytesRead, messageLength - totalBytesRead);
                    if (bytesRead == 0) break;
                    totalBytesRead += bytesRead;
                }

                if (totalBytesRead == messageLength)
                {
                    string message = Encoding.UTF8.GetString(messageBytes);
                    _receivedMessages.Enqueue(message);
                }
            }
        }
        catch (Exception e)
        {
            if (!_isAppQuitting)
            {
                Debug.LogError($"[TCP] 接收数据时出错: {e.Message}");
            }
        }
        finally
        {
            _isClientConnected = false;
            _client?.Close();
            _stream?.Close();
        }
    }

    private void ProcessMessage(string message) // (无变化)
    {
        try
        {
            MessageEnvelope envelope = JsonUtility.FromJson<MessageEnvelope>(message);
            switch (envelope.type)
            {
                case "start_signal":
                    Debug.Log("[TCP] 收到消息: 'start_signal'");
                    OnStartSignalReceived?.Invoke();
                    break;
                case "subtitle":
                    Debug.Log($"[TCP] 收到消息: 'subtitle'，内容: {envelope.payload}");
                    OnSubtitleReceived?.Invoke(envelope.payload);
                    break;
                case "selection_confirmed":
                    Debug.Log("[TCP] <color=cyan>收到来自PC的选择确认信号！</color>");
                    OnSelectionConfirmed?.Invoke();
                    break;
                default:
                    Debug.LogWarning($"[TCP] 收到未定义的消息类型: '{envelope.type}'");
                    break;
            }
        }
        catch (Exception e)
        {
            Debug.LogError($"[TCP] 处理消息时发生错误: {e.Message}. \n原始消息: {message}");
        }
    }

    private void Send(string msgType, string payload) 
    {
        
        if (!_isClientConnected || _stream == null || !_stream.CanWrite)
        {
            Debug.LogError("[TCP] 没有客户端连接，无法发送消息。");
            return;
        }

        try
        {
            MessageEnvelope envelope = new MessageEnvelope { type = msgType, payload = payload };
            string messageJson = JsonUtility.ToJson(envelope);
            byte[] messageBytes = Encoding.UTF8.GetBytes(messageJson);
            byte[] lengthPrefix = BitConverter.GetBytes(messageBytes.Length);
            if (BitConverter.IsLittleEndian)
            {
                Array.Reverse(lengthPrefix);
            }
            _stream.Write(lengthPrefix, 0, 4);
            _stream.Write(messageBytes, 0, messageBytes.Length);
        }
        catch (Exception e)
        {
            Debug.LogError($"[TCP] 发送消息 '{msgType}' 时发生错误: {e.Message}");
            _isClientConnected = false; // Assume the connection is lost if sending fails
        }
    }

    private void Cleanup()
    {
        Debug.Log("[TCP] 正在清理网络资源...");
        _isAppQuitting = true;

        _stream?.Close();
        _stream = null;

        _client?.Close();
        _client = null;

        if (_listenThread != null && _listenThread.IsAlive)
        {
            _listener?.Stop(); 
            _listenThread.Join(); 
        }
        _listener = null;

        _isClientConnected = false;
    }
    #endregion
}