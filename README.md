**yt-dlp_gui**
A user-friendly desktop application for Windows that provides a graphical interface for downloading YouTube videos &amp; playlists as either MP3 audio or MP4 video. This application acts as a visual wrapper for the powerful `yt-dlp` command-line tool, making it easy for users to manage their downloads without needing to use the terminal.

**Installation:** using single terminal/powershell line
...in cmd line run 'python -m PyInstaller yt-dlp_gui.spec'...
Step One:
simply download the files in the list above place them inside Your profiles documents in a folder named yt-dlp "%USERPROFILE%\Documents\yt-dlp"
Step Two:
open terminal & navigate to that yt-dlp dir
Step Three: run line 'python -m PyInstaller yt-dlp_gui.spec'
if it required pyinstaller, first run 'pip install pyinstaller' then the cmd line above.
Step Four:
Navigate to the new dist folder in the yt-dlp folder, then the exe is in the yt-dlp_gui folder.
placed "%USERPROFILE%\Documents\yt-dlp\dist\yt-dlp_gui"
enjoy yt-dlp_gui.exe

**OR** download latest release zip file. Only available for windows x64 OS currently. When figure how to offer for mobile macOS and x32bit OS those may become available. Until then:

You get the installation file after extracting => you simply place dir and open the executable inside "..\yt-dlp_gui\"
