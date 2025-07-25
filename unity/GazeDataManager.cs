// GazeDataManager.cs 
using Microsoft.MixedReality.Toolkit;
using UnityEngine;
using UnityEngine.UI;

// Responsibilities:
// 
public class GazeDataManager : MonoBehaviour
{
    [Header("组件引用")]
    [Tooltip("PC视频流显示的RawImage组件")]
    public RawImage videoDisplayImage;

    private bool _isSendingData = false;
    private Camera mainCamera;

    void Start()
    {
        // Cache the main camera for better performance
        mainCamera = Camera.main;
    }

    void Update()
    {
        // Take no action if data transmission is disabled
        if (!_isSendingData) return;

        // --- 诊断关卡 1: 检查MRTK眼动服务 ---
        var eyeGazeProvider = CoreServices.InputSystem?.EyeGazeProvider;
        if (eyeGazeProvider == null)
        {
            Debug.LogError("[GazeDataManager] 失败: EyeGazeProvider 为 NULL。MRTK核心系统可能未初始化。");
            return;
        }
        if (!eyeGazeProvider.IsEyeTrackingEnabled)
        {
            Debug.LogWarning("[GazeDataManager] 等待: IsEyeTrackingEnabled 为 FALSE。(在编辑器中，请确保按住对应按键激活了眼动模拟器)");
            return;
        }

        // --- 诊断关卡 2: 尝试发射射线 ---
        Debug.Log("[GazeDataManager] 尝试发射射线 (Physics.Raycast)...");
        Ray ray = new Ray(eyeGazeProvider.GazeOrigin, eyeGazeProvider.GazeDirection);

        
        if (Physics.Raycast(ray, out RaycastHit hit, 20f, LayerMask.GetMask("InteractableUI")))
        {
            // --- 诊断关卡 3: 射线击中了物体 ---
            Debug.Log($"[GazeDataManager] 成功: 射线击中了名为 '{hit.collider.name}' 的物体。正在检查它是否为目标RawImage...");

            if (hit.collider.gameObject == videoDisplayImage.gameObject)
            {
                // --- 诊断关卡 4: 确认击中目标，并发送数据 ---
                Debug.Log($"[GazeDataManager] 确认: 击中目标 RawImage！准备发送坐标...");

                // 将3D世界中的碰撞点转换为RawImage的本地2D坐标
                Vector2 localPoint;
                // 注意：需要将3D世界坐标系的碰撞点(hit.point)转换到屏幕坐标系，才能被RectTransformUtility使用
                Vector2 screenPoint = mainCamera.WorldToScreenPoint(hit.point);

                RectTransformUtility.ScreenPointToLocalPointInRectangle(
                    videoDisplayImage.rectTransform,
                    screenPoint,
                    mainCamera,
                    out localPoint
                );

                Vector2Int pixelCoords = ConvertLocalToPixelCoords(localPoint);
                Debug.Log($"[GazeDataManager] >> 正在发送坐标: ({pixelCoords.x}, {pixelCoords.y})");
                TCPManager.Instance.SendGazePosition(pixelCoords);
            }
            else
            {
                Debug.LogWarning($"[GazeDataManager] 忽略: 射线击中了 '{hit.collider.name}'，但它不是我们想要的 RawImage。");
            }
        }
        else
        {
            Debug.Log("[GazeDataManager] 未命中: 射线没有击中'InteractableUI'图层上的任何物体。");
        }
    }

    private Vector2Int ConvertLocalToPixelCoords(Vector2 localPoint)
    {
        Rect rect = videoDisplayImage.rectTransform.rect;
        float normalizedX = (localPoint.x + rect.width / 2) / rect.width;
        float normalizedY = (localPoint.y + rect.height / 2) / rect.height;
        int pixelX = Mathf.RoundToInt(normalizedX * 640f);
        int pixelY = Mathf.RoundToInt((1 - normalizedY) * 480f);
        return new Vector2Int(pixelX, pixelY);
    }

    public void SetSendingState(bool shouldSend)
    {
        _isSendingData = shouldSend;
        if (shouldSend)
        {
            Debug.Log("[GazeDataManager] 状态更新: 已被激活，开始发送眼动数据。");
        }
        else
        {
            Debug.Log("[GazeDataManager] 状态更新: 已被禁用，停止发送眼动数据。");
        }
    }
}