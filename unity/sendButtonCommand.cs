using System.Collections;
using System.Collections.Generic;
using UnityEngine;


// Responsibilities:
// When a button is pressed , invoke the corresponding function to send the message to the PC

public class sendButtonCommand : MonoBehaviour
{
    public void Eat()
    {
        TCPManager.Instance.SendCommand("eat");
        SingleLineConsoleManager.Instance.ShowMessage("将为您执行eat命令！",Color.green);
        InteractionManager.Instance.NotifyCommandSent();
    }

    public void Grub()
    {
        TCPManager.Instance.SendCommand("grub");
        SingleLineConsoleManager.Instance.ShowMessage("将为您执行grub命令！", Color.green);
        InteractionManager.Instance.NotifyCommandSent();
    }

    public void Door()
    {
        TCPManager.Instance.SendCommand("door");
        SingleLineConsoleManager.Instance.ShowMessage("将为您执行door命令！", Color.green);
        InteractionManager.Instance.NotifyCommandSent();
    }

    public void Plate()
    {
        TCPManager.Instance.SendCommand("plate");
        SingleLineConsoleManager.Instance.ShowMessage("将为您执行plate命令！", Color.green);
        InteractionManager.Instance.NotifyCommandSent();
    }

}
