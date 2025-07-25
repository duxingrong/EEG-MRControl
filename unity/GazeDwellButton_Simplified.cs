// GazeDwellButton_Simplified.cs

using UnityEngine;
using UnityEngine.Events;
using Microsoft.MixedReality.Toolkit; 

// Responsibilities:
// Scripts attached to buttons to detect eye-gaze ray enter and exit events


public class GazeDwellButton_Simplified : MonoBehaviour
{
    [Header("UI 组件")]
    [Tooltip("用于显示填充进度的Image组件，可以为null")]
    public UnityEngine.UI.Image fillImage;

    [Header("注视参数")]
    [Tooltip("需要注视多久才能触发按钮（秒）")]
    public float dwellTime = 2.0f;

    
    [Header("射线检测参数")]
    [Tooltip("指定射线只与哪些层进行交互")]
    public LayerMask targetLayers;
    

    [Header("触发事件")]
    [Tooltip("当注视完成后要触发的事件")]
    public UnityEvent OnDwellComplete = new UnityEvent();

    private float _currentDwellTime = 0f;
    private bool _isGazing = false;
    private bool _actionTriggered = false;

    
    public void TriggerAction()
    {
        Debug.Log($"通过手动或外部调用触发了事件: {gameObject.name}");
        OnDwellComplete?.Invoke();

        if (fillImage != null)
        {
            fillImage.fillAmount = 1f;
        }
        _actionTriggered = true;
    }

    void Update()
    {
        var eyeGazeProvider = CoreServices.InputSystem?.EyeGazeProvider;
        if (eyeGazeProvider == null || !eyeGazeProvider.IsEyeTrackingEnabled)
        {
            if (_isGazing) ResetAll();
            return;
        }

        bool isHittingMe = false;
        Ray ray = new Ray(eyeGazeProvider.GazeOrigin, eyeGazeProvider.GazeDirection);

        
        
        if (Physics.Raycast(ray, out RaycastHit hit, 20f, targetLayers))
        {
            if (hit.collider.gameObject == this.gameObject)
            {
                isHittingMe = true;
            }
        }
        
        if (isHittingMe)
        {
            if (!_isGazing)
            {
                _isGazing = true;
                _actionTriggered = false;
                _currentDwellTime = 0f;
                Debug.Log($"视线进入: {gameObject.name}");
            }

            if (_isGazing && !_actionTriggered)
            {
                _currentDwellTime += Time.deltaTime;
                if (fillImage != null)
                {
                    fillImage.fillAmount = _currentDwellTime / dwellTime;
                }

                if (_currentDwellTime >= dwellTime)
                {
                    TriggerAction();
                    Debug.Log("事件已通过注视触发，本次注视不再重复。");
                }
            }
        }
        else
        {
            if (_isGazing)
            {
                ResetAll();
            }
        }
    }

    private void ResetAll()
    {
        if (_isGazing) Debug.Log($"视线离开: {gameObject.name}");
        _isGazing = false;
        _actionTriggered = false;
        _currentDwellTime = 0f;
        if (fillImage != null)
        {
            fillImage.fillAmount = 0f;
        }
    }
}