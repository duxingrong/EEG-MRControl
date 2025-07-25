// SingleLineConsoleManager.cs

using UnityEngine;
using TMPro; 

// Responsibilities:
// Display the subtitle in the subtitle box
public class SingleLineConsoleManager : MonoBehaviour
{
    
    private static SingleLineConsoleManager _instance;

    // 提供一个全局静态访问点
    public static SingleLineConsoleManager Instance
    {
        get
        {
            // 如果实例不存在，就在场景中查找
            if (_instance == null)
            {
                _instance = FindObjectOfType<SingleLineConsoleManager>();
            }
            // 如果场景中也找不到，就创建一个新的
            if (_instance == null)
            {
                GameObject obj = new GameObject("SingleLineConsoleManager");
                _instance = obj.AddComponent<SingleLineConsoleManager>();
            }
            return _instance;
        }
    }
    


    [Header("UI 组件")]
    [Tooltip("用于显示单行日志的TextMeshPro组件")]
    public TextMeshProUGUI consoleText; 

    
    void Awake()
    {
        // 如果场景中已经存在一个实例，但不是我自己，那么销毁我自己，保证唯一性
        if (_instance != null && _instance != this)
        {
            Destroy(this.gameObject);
            return;
        }
        _instance = this;
    }
    

    /// <summary>
    /// Display a new message with the specified color on the UI 。
    /// </summary>
    /// <param name="message">要显示的字符串内容。</param>
    /// <param name="color">文本的颜色。</param>
    public void ShowMessage(string message, Color color)
    {
        if (consoleText != null)
        {
            // 将Unity的Color转换为TextMeshPro富文本支持的HTML颜色代码（如#FF0000）
            string colorHex = ColorUtility.ToHtmlStringRGB(color);
            // 使用富文本标签来设置颜色
            consoleText.text = $"<color=#{colorHex}>{message}</color>";
        }
        else
        {
            Debug.LogError("SingleLineConsoleManager: consoleText组件未设置!");
        }
    }
}