# Burnt-Toast
   A gui tool for exploring windows toast notification spoofing as a post-exploitation research technique. built on top of brmk's original research
 
 # what this tool is
burnt-toast is a research gui for studying and testing the technique in a lab environment. it lets you:

  - compose toast xml payloads across multiple notification templates (basic, image override, protocol actions)
  
  - enumerate AUMIDs registered on the test machine via registry + Start Menu query
  
  - preview what the notification will look like before firing it
  
  - test locally against your own machine to verify payloads
  
  - the generated scripts are standalone powershell with no external dependencies — useful for studying what minimal toast delivery actually looks like at the script level.


burnt-toast is the front-end layer for composing and inspecting payloads. for actual C2 integration, brmk's BOF is the right tool.

[toast my way](https://brmk.me/posts/toast-my-way/) — abusing windows toast notifications for fun and user manipulation brmk, March 2026


# The technique
windows toast notifications are delivered through the WinRT API. every notification is associated with an AUMID (Application User Model ID) — the identifier windows uses to tie a notification to a specific app, its icon, its name, its place in the action center.

the interesting detail brmk documented: you don't need to own the AUMID you're calling. any process running in an interactive user session can invoke ToastNotificationManager::CreateToastNotifier() with any registered AUMID on the system. windows doesn't verify the caller. the notification renders as if the owning application sent it.

the underlying powershell is straightforward:

    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    $null = [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime]
    $null = [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType=WindowsRuntime]

    $xml = @" ... "@   # ToastGeneric XML payload

    $doc = New-Object Windows.Data.Xml.Dom.XmlDocument
    $doc.LoadXml($xml)
    $toast    = [Windows.UI.Notifications.ToastNotification]::new($doc)
    $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("MSEdge")
    $notifier.Show($toast)

the xml schema supports titles, body text, image overrides, protocol-linked buttons, progress bars, reply inputs — the full notification format you'd see from Teams or Outlook.


# known limitations:

- requires an interactive user session — session 0 silently drops the notification
- NoToastApplicationNotification group policy will suppress delivery
- detection is non-trivial: dispatch goes through WpnService so ETW events are attributed there, not to the calling process. EDRs with WinRT COM interface hooks will catch it. see the iPurple Team writeup below for Sigma rules and MDE queries


# install
    
    git clone https://github.com/X0CBAN/Burnt-Toast.git
    cd Burnt-Toast
    pip install -r requirements.txt
    python burnt_toast.py
    
requires python 3.9+. tkinter ships with the standard windows python installer. the live AUMID fetch and local fire features require powershell

related work and credit
all credit for the underlying research goes to the original authors:

# project	author	notes

[toastnotify-bof](https://github.com/brmkit/toastnotify-bof)	brmk	BOF implementation for C2 use — getaumid, sendtoast, custom subcommands

[ToastNotify](https://ipurple.team/2026/03/25/toast-notifications/)	iPurple Team	C# port with detection engineering section, Sigma rules, MDE queries


-----------------------------------------------------------------------------------------------------------------------------------------------------------------------

for authorized security research only. only use against systems you own or have explicit written permission to test.
