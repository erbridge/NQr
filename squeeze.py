# Squeezebox interface

import telnetlib
import urllib

import mediaplayer

class Player:
    def __init__(self, name, server):
        self.__name = name
        self.__server = server

    def __ask(self, cmd):
        return self.__server.ask([self.__name] + cmd)

    def __tell(self, cmd):
        self.__server.tell([self.__name] + cmd)

    def askPlaylist(self, *cmd):
        return self.__ask(['playlist'] + list(cmd))

    def tellPlaylist(self, *cmd):
        self.__tell(['playlist'] + list(cmd))

    def getShuffle(self):
        ret = self.askPlaylist('shuffle')
        return int(ret)

    def setShuffle(self, shuffle):
        self.tellPlaylist('shuffle', str(shuffle))

    def getPlaylistIndex(self):
        return int(self.askPlaylist('index'))

    def getPlaylistTracks(self):
        return int(self.askPlaylist('tracks'))

    def getPlaylistPath(self, index):
        return  self.askPlaylist('path', str(index))

class SQDriver:
    def __init__(self):
        self.__telnet = telnetlib.Telnet('localhost', 9090)

    def __send(self, cmd):
        quoted = ' '.join([urllib.quote(part) for part in cmd])
        print "send:", quoted
        self.__telnet.write(quoted + "\n")
        
        ret = self.__telnet.read_until("\n")
        print "recv:", ret[:-1]

        return [urllib.unquote(part) for part in ret[:-1].split(' ')]

    def ask(self, cmd):
        cmd.append('?')
        ret = self.__send(cmd)
        print "ret=", ret
        assert ret[:-1] == cmd[:-1]
        assert ret[-1] != '?'
        return ret[-1]

    def tell(self, cmd):
        ret = self.__send(cmd)
        print "ret=", ret
        assert ret == cmd

    def askPlayer(self, *cmd):
        return self.ask(['player'] + list(cmd))

    def playerCount(self):
        return int(self.askPlayer('count'))

    def playerName(self, n):
        return self.askPlayer('name', str(n));

    def playerNames(self):
        return [self.playerName(n) for n in range(0, self.playerCount())]

    def playerId(self, n):
        return self.askPlayer('id', str(n));

    def choose(self, player):
        names = self.playerNames()
        assert player in names
        id = self.playerId([n for n in range(0, len(names))
                            if names[n] == player][0])
        self.__player = Player(id, self)

    def getShuffle(self):
        return self.__player.getShuffle()

    def setShuffle(self, shuffle):
        return self.__player.setShuffle(shuffle)

    def getPlaylistIndex(self):
        return self.__player.getPlaylistIndex()

    def getPlaylistTracks(self):
        return self.__player.getPlaylistTracks()

    def getPlaylistPath(self, index):
        ret = self.__player.getPlaylistPath(index)
        return ret
        

class Squeezebox(mediaplayer.MediaPlayer):
    def __init__(self, loggerFactory, noQueue, configParser, defaultPlayer,
                 safePlayers, trackFactory):
        mediaplayer.MediaPlayer.__init__(self, loggerFactory, "NQr.Squeezebox",
                                         noQueue, configParser, defaultPlayer,
                                         safePlayers, trackFactory)
        self.__driver = SQDriver()
        self.__driver.choose('Squeezeslave')

    def getShuffle(self):
        return self.__driver.getShuffle()

    def setShuffle(self, shuffle):
        # this is a bit rum: the rest of the code thinks shuffle is on or off
        # but squeezebox thinks it is 0, 1 or 2.
        if shuffle is False:
            shuffle = 0
        elif shuffle is True:
            shuffle = 1
        self.__driver.setShuffle(shuffle)

    def getCurrentTrackPos(self, traceCallback=None):
        return self.__driver.getPlaylistIndex()
        
    def getPlaylistLength(self):
        return self.__driver.getPlaylistTracks()

    def _getTrackPathAtPos(self, index, traceCallback=None,
                           logging=True):
        path = self.__driver.getPlaylistPath(index)
        assert path.startswith('file://')
        path = urllib.unquote(path[7:])
        print 'path:', path
        return path
    
if __name__ == '__main__':
    box = SQDriver()
    players = box.playerNames()
    print players
    box.choose('Squeezeslave')
    print "shuffle:", box.getShuffle()
    box.setShuffle(0)
    print "index:", box.getPlaylistIndex()
    print "tracks:", box.getPlaylistTracks()
    print "track 0:", box.getPlaylistPath(0)
