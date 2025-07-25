// InteractionManager.cs

// Responsibilities:
// 1. Acts as a singleton to orchestrate the entire "pc-initiated ->Hololens interaction ->PC-execution" workflow
// 2. Controls the visibility of the main UI
// 3. Listens for key events from TCPManager (e.g OnStartSignalReceived, OnSelectionConfirmed)。
// 4. Responds to UI events(e.g  command button clicks) and starts/stops functional modules such as GazeDataManager
// 5. Provides the user with status prompts throughout the task flow

using UnityEngine;

public class InteractionManager : MonoBehaviour
{
    #region 单例模式 (Singleton Pattern)
    public static InteractionManager Instance { get; private set; }
    #endregion

    #region UI与模块引用 (UI & Module References)
    [Header("UI控制")]
    [Tooltip("包含所有UI元素的父级GameObject，通常就是Canvas本身")]
    public GameObject mainUIRoot;

    [Tooltip("指令按钮的父级容器，用于在发送指令后单独隐藏")]
    public GameObject commandButtonsPanel;

    // 对GazeDataManager的引用
    [Header("功能模块引用")]
    [Tooltip("负责发送眼神数据的管理器")]
    public GazeDataManager gazeManager;
    #endregion

    #region Unity生命周期方法 (Unity Lifecycle Methods)
    private void Awake()
    {
        if (Instance != null && Instance != this) Destroy(this.gameObject);
        else Instance = this;
    }

    private void Start()
    {
        // 1. At startup, ensure the UI is completely hidden and display a standby message
        HideFullUI();
        SingleLineConsoleManager.Instance.ShowMessage("待机中，等待PC发起任务...", Color.gray);

        // 2. Subscribe to TCPManager's events
        TCPManager.OnStartSignalReceived += HandleStartSignal;
        TCPManager.OnSubtitleReceived += HandleSubtitle;
        TCPManager.OnSelectionConfirmed += HandleSelectionConfirmed;
    }

    private void OnDestroy()
    {
        if (TCPManager.Instance != null)
        {
            TCPManager.OnStartSignalReceived -= HandleStartSignal;
            TCPManager.OnSubtitleReceived -= HandleSubtitle;
            TCPManager.OnSelectionConfirmed -= HandleSelectionConfirmed;
        }
    }
    #endregion

    #region 核心流程控制 (Core Flow Control)

    // Step 1 : Receive the start signal from the PC
    private void HandleStartSignal()
    {
        ShowFullUI();
        SingleLineConsoleManager.Instance.ShowMessage("系统已激活，请选择一个操作指令。", Color.cyan);
        TCPManager.Instance.SendAcknowledgement("start_signal_received");
    }

    // Step 1.5 : Continuously receive subtitle messages from the PC
    private void HandleSubtitle(string message)
    {
        SingleLineConsoleManager.Instance.ShowMessage(message, Color.white);
    }

    // Step 2 : (Called by the command button) Once the user selects and sends a command 
    public void NotifyCommandSent()
    {
        if (commandButtonsPanel != null)
        {
            commandButtonsPanel.SetActive(false); // Hide the command buttons to prevent duplicate actions
        }
        SingleLineConsoleManager.Instance.ShowMessage("指令已发送，请用视线选择目标...", Color.yellow);

        // Start Gaze-data transmission
        if (gazeManager != null)
        {
            gazeManager.SetSendingState(true);
        }
    }

    // Step 3: Receive the selection-confirmation signal from the PC
    private void HandleSelectionConfirmed()
    {
        SingleLineConsoleManager.Instance.ShowMessage("PC已确认目标选择，交互完成。", Color.green);

        //  Once the confirmation is received, immediately hide the UI and end this interaction.
        HideFullUI();
    }


    #endregion

    #region UI辅助方法 (UI Helper Methods)
    private void ShowFullUI()
    {
        if (mainUIRoot == null) return;
        mainUIRoot.SetActive(true);

        if (commandButtonsPanel != null)
        {
            commandButtonsPanel.SetActive(true);
        }
    }

    private void HideFullUI()
    {
        if (mainUIRoot == null) return;

        if (gazeManager != null)
        {
            gazeManager.SetSendingState(false);
        }

        mainUIRoot.SetActive(false);
    }
    #endregion
}