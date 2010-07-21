#
# winamp.py
#
# Winamp control interface
#
# Version 1.0.1 (20-05-2008)
#
# Copyright (c) 2008, Arkadiusz Wahlig
#
# Permission is hereby granted, free of charge, to any
# person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the
# Software without restriction, including without 
# limitation the rights to use, copy, modify, merge, 
# publish, distribute, sublicense, and/or sell copies of 
# the Software, and to permit persons to whom the Software 
# is furnished to do so, subject to the following 
# conditions:
#
# The above copyright notice and this permission notice 
# shall be included in all copies or substantial portions 
# of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY 
# KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO 
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A 
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL 
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, 
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
# CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN 
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS 
# IN THE SOFTWARE.
# 

import os
from ctypes import *

WM_COMMAND = 0x111
WM_USER = 0x400
WM_WA_IPC = WM_USER
WM_COPYDATA = 0x4A

SW_MINIMIZE = 6
SW_RESTORE = 9

class COPYDATASTRUCT(Structure):
    _fields_ = [('dwData', c_ulong),
                ('cbData', c_uint),
                ('lpData', c_char_p)]

IPC_GETVERSION = 0
# int version = SendMessage(hwnd_winamp,WM_WA_IPC,0,IPC_GETVERSION);
#
# Version will be 0x20yx for winamp 2.yx. versions previous to Winamp 2.0
# typically (but not always) use 0x1zyx for 1.zx versions. Weird, I know.

IPC_GETREGISTEREDVERSION = 770

IPC_PLAYFILE = 100 # dont be fooled, this is really the same as enqueufile
IPC_ENQUEUEFILE = 100 
# sent as a WM_COPYDATA, with IPC_PLAYFILE as the dwData, and the string to play
# as the lpData. Just enqueues, does not clear the playlist or change the playback
# state.

IPC_DELETE = 101
IPC_DELETE_INT = 1101 # don't use this, it's used internally by winamp when 
                      # dealing with some lame explorer issues.
# SendMessage(hwnd_winamp,WM_WA_IPC,0,IPC_DELETE);
# Use IPC_DELETE to clear Winamp's internal playlist.

IPC_STARTPLAY = 102      # starts playback. almost like hitting play in Winamp.
IPC_STARTPLAY_INT = 1102 # used internally, don't bother using it (won't be any fun)

IPC_CHDIR = 103
# sent as a WM_COPYDATA, with IPC_CHDIR as the dwData, and the directory to change to
# as the lpData. 

IPC_ISPLAYING = 104
# int res = SendMessage(hwnd_winamp,WM_WA_IPC,0,IPC_ISPLAYING);
# If it returns 1, it is playing. if it returns 3, it is paused, 
# if it returns 0, it is not playing.

IPC_GETOUTPUTTIME = 105
# int res = SendMessage(hwnd_winamp,WM_WA_IPC,mode,IPC_GETOUTPUTTIME);
# returns the position in milliseconds of the current track (mode = 0), 
# or the track length, in seconds (mode = 1). Returns -1 if not playing or error.

IPC_JUMPTOTIME = 106
# (requires Winamp 1.60+)
# SendMessage(hwnd_winamp,WM_WA_IPC,ms,IPC_JUMPTOTIME);
# IPC_JUMPTOTIME sets the position in milliseconds of the 
# current song (approximately).
# Returns -1 if not playing, 1 on eof, or 0 if successful

IPC_GETMODULENAME = 109
IPC_EX_ISRIGHTEXE = 666
# usually shouldnt bother using these, but here goes:
# send a WM_COPYDATA with IPC_GETMODULENAME, and an internal
# flag gets set, which if you send a normal WM_WA_IPC message with
# IPC_EX_ISRIGHTEXE, it returns whether or not that filename
# matches. lame, I know.

IPC_WRITEPLAYLIST = 120
# (requires Winamp 1.666+)
# SendMessage(hwnd_winamp,WM_WA_IPC,0,IPC_WRITEPLAYLIST);
#
# IPC_WRITEPLAYLIST writes the current playlist to <winampdir>\\Winamp.m3u,
# and returns the current playlist position.
# Kinda obsoleted by some of the 2.x new stuff, but still good for when
# using a front-end (instead of a plug-in)

IPC_SETPLAYLISTPOS = 121
# (requires Winamp 2.0+)
# SendMessage(hwnd_winamp,WM_WA_IPC,position,IPC_SETPLAYLISTPOS)
# IPC_SETPLAYLISTPOS sets the playlist position to 'position'. It
# does not change playback or anything, it just sets position, and
# updates the view if necessary

IPC_SETVOLUME = 122
# (requires Winamp 2.0+)
# SendMessage(hwnd_winamp,WM_WA_IPC,volume,IPC_SETVOLUME);
# IPC_SETVOLUME sets the volume of Winamp (from 0-255).

IPC_SETPANNING = 123
# (requires Winamp 2.0+)
# SendMessage(hwnd_winamp,WM_WA_IPC,panning,IPC_SETPANNING);
# IPC_SETPANNING sets the panning of Winamp (from 0 (left) to 255 (right)).

IPC_GETLISTLENGTH = 124
# (requires Winamp 2.0+)
# int length = SendMessage(hwnd_winamp,WM_WA_IPC,0,IPC_GETLISTLENGTH);
# IPC_GETLISTLENGTH returns the length of the current playlist, in
# tracks.

IPC_GETLISTPOS = 125
# (requires Winamp 2.05+)
# int pos=SendMessage(hwnd_winamp,WM_WA_IPC,0,IPC_GETLISTPOS);
# IPC_GETLISTPOS returns the playlist position. A lot like IPC_WRITEPLAYLIST
# only faster since it doesn't have to write out the list. Heh, silly me.

IPC_GETINFO = 126
# (requires Winamp 2.05+)
# int inf=SendMessage(hwnd_winamp,WM_WA_IPC,mode,IPC_GETINFO);
# IPC_GETINFO returns info about the current playing song. The value
# it returns depends on the value of 'mode'.
# Mode      Meaning
# ------------------
# 0         Samplerate (i.e. 44100)
# 1         Bitrate  (i.e. 128)
# 2         Channels (i.e. 2)
# 3 (5+)    Video LOWORD=w HIWORD=h
# 4 (5+)    > 65536, string (video description)

IPC_GETEQDATA = 127
# (requires Winamp 2.05+)
# int data=SendMessage(hwnd_winamp,WM_WA_IPC,pos,IPC_GETEQDATA);
# IPC_GETEQDATA queries the status of the EQ. 
# The value returned depends on what 'pos' is set to:
# Value      Meaning
# ------------------
# 0-9        The 10 bands of EQ data. 0-63 (+20db - -20db)
# 10         The preamp value. 0-63 (+20db - -20db)
# 11         Enabled. zero if disabled, nonzero if enabled.
# 12         Autoload. zero if disabled, nonzero if enabled.

IPC_SETEQDATA = 128
# (requires Winamp 2.05+)
# SendMessage(hwnd_winamp,WM_WA_IPC,pos,IPC_GETEQDATA);
# SendMessage(hwnd_winamp,WM_WA_IPC,value,IPC_SETEQDATA);
# IPC_SETEQDATA sets the value of the last position retrieved
# by IPC_GETEQDATA. This is pretty lame, and we should provide
# an extended version that lets you do a MAKELPARAM(pos,value).
# someday...
#
# new (2.92+): 
#   if the high byte is set to 0xDB, then the third byte specifies
#   which band, and the bottom word specifies the value.

IPC_ADDBOOKMARK = 129
# (requires Winamp 2.4+)
# Sent as a WM_COPYDATA, using IPC_ADDBOOKMARK, adds the specified
# file/url to the Winamp bookmark list.
#
# In winamp 5+, we use this as a normal WM_WA_IPC and the string:
#
#  "filename\0title\0"
#
#  to notify the library/bookmark editor that a bookmark
# was added. Note that using this message in this context does not
# actually add the bookmark.
# do not use :)

IPC_INSTALLPLUGIN = 130
# not implemented, but if it was you could do a WM_COPYDATA with 
# a path to a .wpz, and it would install it.

IPC_RESTARTWINAMP = 135
# (requires Winamp 2.2+)
# SendMessage(hwnd_winamp,WM_WA_IPC,0,IPC_RESTARTWINAMP);
# IPC_RESTARTWINAMP will restart Winamp (isn't that obvious ? :)

IPC_ISFULLSTOP = 400
# (requires winamp 2.7+ I think)
# ret=SendMessage(hwnd_winamp,WM_WA_IPC,0,IPC_ISFULLSTOP);
# useful for when you're an output plugin, and you want to see
# if the stop/close is a full stop, or just between tracks.
# returns nonzero if it's full, zero if it's just a new track.

IPC_INETAVAILABLE = 242
# (requires Winamp 2.05+)
# val=SendMessage(hwnd_winamp,WM_WA_IPC,0,IPC_INETAVAILABLE);
# IPC_INETAVAILABLE will return 1 if the Internet connection is available for Winamp.

IPC_UPDTITLE = 243
# (requires Winamp 2.2+)
# SendMessage(hwnd_winamp,WM_WA_IPC,0,IPC_UPDTITLE);
# IPC_UPDTITLE will ask Winamp to update the informations about the current title.

IPC_REFRESHPLCACHE = 247
# (requires Winamp 2.2+)
# SendMessage(hwnd_winamp,WM_WA_IPC,0,IPC_REFRESHPLCACHE);
# IPC_REFRESHPLCACHE will flush the playlist cache buffer.
# (send this if you want it to go refetch titles for tracks)

IPC_GET_SHUFFLE = 250
# (requires Winamp 2.4+)
# val=SendMessage(hwnd_winamp,WM_WA_IPC,0,IPC_GET_SHUFFLE);
#
# IPC_GET_SHUFFLE returns the status of the Shuffle option (1 if set)

IPC_GET_REPEAT = 251
# (requires Winamp 2.4+)
# val=SendMessage(hwnd_winamp,WM_WA_IPC,0,IPC_GET_REPEAT);
#
# IPC_GET_REPEAT returns the status of the Repeat option (1 if set)

IPC_SET_SHUFFLE = 252
# (requires Winamp 2.4+)
# SendMessage(hwnd_winamp,WM_WA_IPC,value,IPC_SET_SHUFFLE);
#
# IPC_SET_SHUFFLE sets the status of the Shuffle option (1 to turn it on)

IPC_SET_REPEAT = 253
# (requires Winamp 2.4+)
# SendMessage(hwnd_winamp,WM_WA_IPC,value,IPC_SET_REPEAT);
#
# IPC_SET_REPEAT sets the status of the Repeat option (1 to turn it on)

IPC_ENABLEDISABLE_ALL_WINDOWS = 259 # 0xdeadbeef to disable
# (requires Winamp 2.9+)
# SendMessage(hwnd_winamp,WM_WA_IPC,enable?0:0xdeadbeef,IPC_MBOPENREAL);
# sending with 0xdeadbeef as the param disables all winamp windows, 
# any other values will enable all winamp windows.

IPC_GETWND = 260
# (requires Winamp 2.9+)
# HWND h=SendMessage(hwnd_winamp,WM_WA_IPC,IPC_GETWND_xxx,IPC_GETWND);
# returns the HWND of the window specified.
#
IPC_GETWND_EQ = 0 # use one of these for the param
IPC_GETWND_PE = 1
IPC_GETWND_MB = 2
IPC_GETWND_VIDEO = 3
IPC_ISWNDVISIBLE = 261 # same param as IPC_GETWND

# WM_COMMAND messages that you can use to send Winamp misc commands.
WINAMP_OPTIONS_EQ               = 40036 # toggles the EQ window
WINAMP_OPTIONS_PLEDIT           = 40040 # toggles the playlist window
WINAMP_VOLUMEUP                 = 40058 # turns the volume up a little
WINAMP_VOLUMEDOWN               = 40059 # turns the volume down a little
WINAMP_FFWD5S                   = 40060 # fast forwards 5 seconds
WINAMP_REW5S                    = 40061 # rewinds 5 seconds

# the following are the five main control buttons, with optionally shift 
# or control pressed
WINAMP_BUTTON1                  = 40044
WINAMP_BUTTON2                  = 40045
WINAMP_BUTTON3                  = 40046
WINAMP_BUTTON4                  = 40047
WINAMP_BUTTON5                  = 40048
WINAMP_BUTTON1_SHIFT            = 40144
WINAMP_BUTTON2_SHIFT            = 40145
WINAMP_BUTTON3_SHIFT            = 40146
WINAMP_BUTTON4_SHIFT            = 40147
WINAMP_BUTTON5_SHIFT            = 40148
WINAMP_BUTTON1_CTRL             = 40154
WINAMP_BUTTON2_CTRL             = 40155
WINAMP_BUTTON3_CTRL             = 40156
WINAMP_BUTTON4_CTRL             = 40157
WINAMP_BUTTON5_CTRL             = 40158

WINAMP_FILE_PLAY                = 40029 # pops up the load file(s) box
WINAMP_FILE_DIR                 = 40187 # pops up the load directory box
WINAMP_OPTIONS_PREFS            = 40012 # pops up the preferences
WINAMP_OPTIONS_AOT              = 40019 # toggles always on top
WINAMP_HELP_ABOUT               = 40041 # pops up the about box :)

ID_MAIN_PLAY_AUDIOCD1           = 40323 # starts playing the audio CD in the first CD reader
ID_MAIN_PLAY_AUDIOCD2           = 40323 # plays the 2nd
ID_MAIN_PLAY_AUDIOCD3           = 40323 # plays the 3nd
ID_MAIN_PLAY_AUDIOCD4           = 40323 # plays the 4nd

# more commands and some better names
WINAMP_PREV = 40044        # Previous track button
WINAMP_NEXT = 40048        # Next track button
WINAMP_PLAY = 40045        # Play button
WINAMP_PAUSE = 40046       # Pause/Unpause button
WINAMP_STOP = 40047        # Stop button
WINAMP_FADESTOP = 40147    # Fadeout and stop
WINAMP_STOPTRACK = 40157   # Stop after current track
WINAMP_FFW = 40148         # Fast-forward 5 seconds
WINAMP_FRW = 40144         # Fast-rewind 5 seconds
WINAMP_PLSTART = 40154     # Start of playlist
WINAMP_PLEND = 40158       # Go to end of playlist
WINAMP_OPENFILE = 40029    # Open file dialog
WINAMP_OPENURL = 40155     # Open URL dialog
WINAMP_INFOBOX = 40188     # Open file info box
WINAMP_TIMEELAPSED = 40037 # Set time display mode to elapsed
WINAMP_TIMEREMAIN = 40038  # Set time display mode to remaining
WINAMP_TOGGLEPREF = 40012  # Toggle preferences screen
WINAMP_OPENVISUAL = 40190  # Open visualization options
WINAMP_OPENVIPLUG = 40191  # Open visualization plug-in options
WINAMP_EXECVISUAL = 40192  # Execute current visualization plug-in
WINAMP_TOGGLEABOUT = 40041 # Toggle about box
WINAMP_AUTOSCROLL = 40189  # Toggle title Autoscrolling
WINAMP_TOGGLEONTOP = 40019 # Toggle always on top
WINAMP_WNDSHADE = 40064    # Toggle Windowshade
WINAMP_PLSWNDSHADE = 40266 # Toggle Playlist Windowshade
WINAMP_DBLSIZE = 40165     # Toggle doublesize mode
WINAMP_TOGGLEEQ = 40036    # Toggle EQ
WINAMP_TOGGLEPL = 40040    # Toggle playlist editor
WINAMP_TOGGLEMW = 40258    # Toggle main window visible
WINAMP_MINIBROWSE = 40298  # Toggle minibrowser
WINAMP_EASYMOVE = 40186    # Toggle easymove
WINAMP_VOLINCR = 40058     # Raise volume by 1%
WINAMP_VOLDECR = 40059     # Lower volume by 1%
WINAMP_SHUFFLE = 40023     # Toggle Shuffle
WINAMP_REPEAT = 40022      # Toggle Repeat
WINAMP_JMPTIME = 40193     # Open jump to time dialog
WINAMP_JMPFILE = 40194     # Open jump to file dialog
WINAMP_SKINSELEC = 40219   # Open skin selector
WINAMP_CONFVISUAL = 40221  # Configure current visualization plug-in
WINAMP_RELOADSKIN = 40291  # Reload the current skin
WINAMP_CLOSE = 40001       # Close Winamp
WINAMP_TENTRKBACK = 40197  # Moves back 10 tracks in playlist
WINAMP_EDBOOKMRK = 40320   # Show the edit bookmarks
WINAMP_BOOKMRKTRK = 40321  # Adds current track as a bookmark
WINAMP_AUDIOCD = 40323     # Play audio CD
WINAMP_LOADEQ = 40253      # Load a preset from EQ
WINAMP_SAVEEQ = 40254      # Save a preset to EQF
WINAMP_LOADPRESETS = 40172 # Opens load presets dialog
WINAMP_AUTOLDPRSTS = 40173 # Opens auto-load presets dialog
WINAMP_LOADDEFPRST = 40174 # Load default preset
WINAMP_SAVEPRESET = 40175  # Opens save preset dialog
WINAMP_AUTOLDSAVE = 40176  # Opens auto-load save preset
WINAMP_DELPRESET = 40178   # Opens delete preset dialog
WINAMP_DELAUTOLD = 40180   # Opens delete an auto load preset dialog

class WinampError(Exception):
    pass

class Winamp(object):
    def getWinamp(self):
        if hasattr(self, 'hwnd') and self.hwnd and \
            windll.user32.IsWindow(self.hwnd):
                return
        self.hwnd = windll.user32.FindWindowA('Winamp v1.x', None)
        if not self.hwnd:
            raise WinampError('Winamp is not running')

    def doCommand(self, cmd):
        self.getWinamp()
        windll.user32.SendMessageA(self.hwnd, WM_COMMAND, cmd, 0)
        
    def doIpcCommand(self, cmd, data=None):
        self.getWinamp()
        return windll.user32.SendMessageA(self.hwnd, WM_WA_IPC, data, cmd)
        
    def open(self):
        self.restore()
        self.focus()

    def minimize(self):
        self.getWinamp()
        windll.user32.ShowWindow(self.hwnd, SW_MINIMIZE)

    def restore(self):
        self.getWinamp()
        windll.user32.ShowWindow(self.hwnd, SW_RESTORE)

    def focus(self):
        self.getWinamp()
        windll.user32.SetForegroundWindow(self.hwnd)

    def getRunning(self):
        try:
            self.getWinamp()
            return True
        except WinampError:
            return False
            
    running = property(getRunning)
        
    def start(self):
        path = os.path.expandvars('${PROGRAMFILES}\\Winamp\\winamp.exe')    
        windll.kernel32.WinExec(path, 0)
    
    def getVersion(self):
        v = self.doIpcCommand(IPC_GETVERSION)
        major = v >> 8
        if major < 0x20:
            minor = ((major & 0xf) << 8) | (v & 0xf)
            major = 1
        else:
            minor = v & 0xff
            major = major >> 4
        return float('%x' % major) + float('%x' % minor) / 100
        
    version = property(getVersion)
    
    def enqueue(self, filename):
        self.getWinamp()
        copy = COPYDATASTRUCT(IPC_ENQUEUEFILE, len(filename)+1, filename)
        windll.user32.SendMessageA(self.hwnd, WM_COPYDATA, None, byref(copy))

    def clearPlaylist(self):
        self.doIpcCommand(IPC_DELETE)

    def getStatus(self):
        v = self.doIpcCommand(IPC_ISPLAYING)
        if v == 0:
            if self.doIpcCommand(IPC_ISFULLSTOP):
                return wsFullyStopped
        return {0: wsStopped,
                1: wsPlaying,
                3: wsPaused}[v]

    status = property(getStatus)
    
    def getCurrentTrackLength(self):
        return float(self.doIpcCommand(IPC_GETOUTPUTTIME, 1))

    currentTrackLength = property(getCurrentTrackLength)

    def getCurrentTrackPos(self):
        v = self.doIpcCommand(IPC_GETOUTPUTTIME, 0)
        if v >= 0:
            return float(v) / 1000

    def setCurrentTrackPos(self, pos):
        self.doIpcCommand(IPC_JUMPTOTIME, int(pos * 1000))

    currentTrackPos = property(getCurrentTrackPos, setCurrentTrackPos)

    def getCurrentTrack(self):
        return self.doIpcCommand(IPC_GETLISTPOS)
    
    def setCurrentTrack(self, pos):
        if not (0 <= pos < self.playlistLength):
            raise ValueError('Current track must be in range(playlistLength)')
        self.doIpcCommand(IPC_SETPLAYLISTPOS, pos)

    currentTrack = property(getCurrentTrack, setCurrentTrack)

    def getCurrentTrackName(self):
        self.doIpcCommand(IPC_UPDTITLE)
        b = create_string_buffer(512)
        windll.user32.GetWindowTextA(self.hwnd, b, 512)
        name = b.value
        i = name.find('. ')
        if i >= 0:
            name = name[i+2:]
        if name.endswith(']'):
            name = name[:name.rfind(' [')]
        if name.endswith(' - Winamp'):
            name = name[:-9]
        else:
            name = ''
        return name
    
    currentTrackName = property(getCurrentTrackName)

    def getVolume(self):
        return self.doIpcCommand(IPC_SETVOLUME, -666)

    def setVolume(self, volume):
        if not (0 <= volume <= 255):
            raise ValueError('Volume must be in range(256)')
        self.doIpcCommand(IPC_SETVOLUME, volume)
        
    volume = property(getVolume, setVolume)

    def getPanning(self):
        return self.doIpcCommand(IPC_SETPANNING, -666)

    def setPanning(self, panning):
        if not (-127 <= panning <= 127):
            raise ValueError('Panning must be in range(-127, 128)')
        self.doIpcCommand(IPC_SETPANNING, panning)
        
    panning = property(getPanning, setPanning)

    def getPlaylistLength(self):
        return self.doIpcCommand(IPC_GETLISTLENGTH)
        
    playlistLength = property(getPlaylistLength)

    def getSampleRate(self):
        return self.doIpcCommand(IPC_GETINFO, 0)

    sampleRate = property(getSampleRate)

    def getBitrate(self):
        return self.doIpcCommand(IPC_GETINFO, 1)

    bitrate = property(getBitrate)

    def getChannels(self):
        return self.doIpcCommand(IPC_GETINFO, 2)

    channels = property(getChannels)

    def writePlaylist(self):
        self.doIpcCommand(IPC_WRITEPLAYLIST)

    def playPlaylist(self):
        self.doIpcCommand(IPC_STARTPLAY)

    def getEqEnabled(self):
        return bool(self.doIpcCommand(IPC_GETEQDATA, 11))
        
    def setEqEnabled(self, enabled):
        self.doIpcCommand(IPC_GETEQDATA, 11)
        self.doIpcCommand(IPC_SETEQDATA, enabled)

    eqEnabled = property(getEqEnabled, setEqEnabled)

    def getEqAutoload(self):
        return bool(self.doIpcCommand(IPC_GETEQDATA, 12))
        
    def setEqAutoload(self, enabled):
        self.doIpcCommand(IPC_GETEQDATA, 12)
        self.doIpcCommand(IPC_SETEQDATA, enabled)

    eqAutoload = property(getEqAutoload, setEqAutoload)

    def getEqPreamp(self):
        return 31-self.doIpcCommand(IPC_GETEQDATA, 10)
        
    def setEqPreamp(self, value):
        if not (-32 <= value <= 31):
            raise ValueError('Preamp must be in range(-32, 32)')
        self.doIpcCommand(IPC_GETEQDATA, 10)
        self.doIpcCommand(IPC_SETEQDATA, 31-value)

    eqPreamp = property(getEqPreamp, setEqPreamp)

    def getEqBand(self, band):
        if not (0 <= band <= 9):
            raise ValueError('Band must be in range(10)')
        return 31-self.doIpcCommand(IPC_GETEQDATA, band)
        
    def setEqBand(self, band, value):
        if not (0 <= band <= 9):
            raise ValueError('Band must be in range(10)')
        if not (-32 <= value <= 31):
            raise ValueError('Value must be in range(-32, 32)')
        self.doIpcCommand(IPC_GETEQDATA, 10)
        self.doIpcCommand(IPC_SETEQDATA, 31-value)

    def addBookmark(self, filename):
        self.getWinamp()
        copy = COPYDATASTRUCT(IPC_ADDBOOKMARK, len(filename)+1, filename)
        windll.user32.SendMessageA(self.hwnd, WM_COPYDATA, None, byref(copy))

    def installPlugin(self, filename):
        self.getWinamp()
        copy = COPYDATASTRUCT(IPC_INSTALLPLUGIN, len(filename)+1, filename)
        windll.user32.SendMessageA(self.hwnd, WM_COPYDATA, None, byref(copy))

    def restartWinamp(self):
        self.doIpcCommand(IPC_RESTARTWINAMP)
    
    def getInetAvailable(self):
        return bool(self.doIpcCommand(IPC_INETAVAILABLE))
        
    inetAvailable = property(getInetAvailable)
    
    def getShuffle(self):
        return bool(self.doIpcCommand(IPC_GET_SHUFFLE))
        
    def setShuffle(self, enabled):
        self.doIpcCommand(IPC_SET_SHUFFLE, enabled)
        
    shuffle = property(getShuffle, setShuffle)
    
    def getRepeat(self):
        return bool(self.doIpcCommand(IPC_GET_REPEAT))
        
    def setRepeat(self, enabled):
        self.doIpcCommand(IPC_SET_REPEAT, enabled)
        
    repeat = property(getRepeat, setRepeat)

    def lockInterface(self, lock):
        if lock:
            lock = 0xdeadbeef
        else:
            lock = 0
        self.doIpcCommand(IPC_ENABLEDISABLE_ALL_WINDOWS, lock)

    def refreshPlaylistCache(self):
        self.doIpcCommand(IPC_REFRESHPLCACHE)

    commands = {
        'previous': WINAMP_PREV,
        'play': WINAMP_PLAY,
        'pause': WINAMP_PAUSE,
        'stop': WINAMP_STOP,
        'fadeStop': WINAMP_FADESTOP,
        'stopAfterTrack': WINAMP_STOPTRACK,
        'next': WINAMP_NEXT,
        'forward': WINAMP_FFW,
        'rewind': WINAMP_FRW,
        'volumeUp': WINAMP_VOLUMEUP,
        'volumeDown': WINAMP_VOLUMEDOWN,
        'close': WINAMP_CLOSE,
        'topOfPlaylist': WINAMP_PLSTART,
        'bottomOfPlaylist': WINAMP_PLEND,
        'openFileDialog': WINAMP_OPENFILE,
        'openUrlDialog': WINAMP_OPENURL,
        'openFileInfoDialog': WINAMP_INFOBOX,
        'openJumpTimeDialog': WINAMP_JMPTIME,
        'openJumpTrackDialog': WINAMP_JMPFILE,
    }
    
    for name, cmd in commands.items():
        exec '%s = lambda self: self.doCommand(%s)' % (name, cmd)
    del commands

# status
wsFullyStopped = 'fullyStopped'
wsStopped = 'stopped'
wsPlaying = 'playing'
wsPaused = 'paused'
