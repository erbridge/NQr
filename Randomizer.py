## Randomization Algorithm
## TODO: work out time factor if track has never been played: poss use time
##       since added to database?
## TODO: work out what weights should be (poss make sliders)
## TODO: getWeights from a text option (convert into python code) allowing
##       length of list etc.

import ConfigParser
from Errors import *
from Time import RoughAge
from Util import plural
import random
import time

import wxversion
wxversion.select([x for x in wxversion.getInstalled()
                  if x.find('unicode') != -1])
import wx

## tracks with a score >= scoreThreshold get played
## by default, -10s are not played
class Randomizer:
    def __init__(self, db, trackFactory, loggerFactory, configParser,
                 scoreThreshold=-9):
        self._db = db
        self._trackFactory = trackFactory
        self._logger = loggerFactory.getLogger("NQr.Randomizer", "debug")
        self._configParser = configParser
        self.loadSettings()
        self._scoreThreshold = scoreThreshold

    def getPrefsPage(self, parent, logger):
        return PrefsPage(parent, self._configParser, logger), "Randomizer"

    def loadSettings(self):
        pass

    def chooseTrack(self):
        track = self.chooseTracks(1)[0]
        return track

    def chooseTracks(self, number, exclude):
        self._logger.debug("Selecting "+str(number)+" track" + plural(number)
                           + ".")
        trackIDs = self._chooseTrackIDs(number, exclude)
        tracks = []
        for [trackID, weight] in trackIDs:
            track = self._trackFactory.getTrackFromID(self._db, trackID)
            track.setWeight(weight)
            tracks.append(track)
        return tracks

## will throw exception if database is empty?
    def _chooseTrackIDs(self, number, exclude):
##        print time.time()
        (trackWeightList, totalWeight) = self.createLists(exclude)
        trackIDs = []
        for n in range(number):
##            poss should be here so tracks enqueued have times reset each time.
##            would be much slower though.
##            (trackWeightList, totalWeight) = self.createLists()
            selector = random.random() * totalWeight
            for [trackID, weight] in trackWeightList:
                selector -= weight
                if selector < 0:
##                    print time.time()
                    norm = float(weight) * len(trackWeightList) / totalWeight
                    self._logger.info("Selected " + str(trackID) + " weight " \
                                      + str(weight) + " total " \
                                      + str(totalWeight) + " norm " + str(norm))
                    trackIDs.append([trackID, norm])
                    break
        return trackIDs

    def createLists(self, exclude):
        self._logger.debug("Creating weighted list of tracks.")
        oldest = self._db.getOldestLastPlayed()
        self._logger.info("Oldest is " + str(oldest) + " (" + RoughAge(oldest)
                          + ")")
        rawTrackIDList = self._db.getAllTrackIDs()
        if rawTrackIDList == []:
            self._logger.error("No tracks in database.")
            raise EmptyDatabaseError
        trackWeightList = []
        totalWeight = 0
        for (trackID, ) in rawTrackIDList:
            # |exclude| is probably the list of currently enqueued but
            # unplayed tracks.
            if trackID in exclude:
                continue
            time = self._db.getSecondsSinceLastPlayedFromID(trackID)
            score = self._db.getScoreValueFromID(trackID) + 11
            ## creates a positive score
            if time == None:
                time = oldest
            if score < self._scoreThreshold + 11:
                score = 0
            weight = self.getWeight(score, time)
            trackWeightList.append([trackID, weight])
            totalWeight += weight
        return trackWeightList, totalWeight

    def getWeight(self, score, time):
##        weight = time ** (score/50.)
        weight = score**2 * time**2
##        weight = score * time
        return weight

#### poss "reverse(sorted(" makes operation slower, not faster
##    def chooseTrackID(self):
####        print time.time()
##        (trackIDList, weightList) = self.createLists()
##        selector = random.random() * sum(weightList)
##        for weight, trackID in reversed(sorted(zip(weightList, trackIDList))):
##            selector -= weight
##            if selector < 0:
####                print time.time()
##                return trackID
##
##    def createLists(self):
##        rawTrackIDList = self._db.getAllTrackIDs()
##        if rawTrackIDList == None:
##            print "The database is empty."
##            return None
##        trackIDList = []
##        for (trackID, ) in rawTrackIDList:
##            trackIDList.append(trackID)
##        weightList = []
####        totalWeight = 0
##        for trackID in trackIDList:
##            time = self._db.getSecondsSinceLastPlayedFromID(trackID)
##            score = self._db.getScoreValueFromID(trackID) + 11 ## creates a positive score
##            if time == None:
##                time = 5 * (len(trackIDList) + 1)
##            if score < self._scoreThreshold + 11:
##                score = 0
##            weight = self.getWeight(score, time)
##            weightList.append(weight)
####            totalWeight += weight
##        return trackIDList, weightList##, totalWeight

class PrefsPage(wx.Panel):
    def __init__(self, parent, configParser, logger):
        wx.Panel.__init__(self, parent)
        self._logger = logger
        self._settings = {}
        self._configParser = configParser
        try:
            self._configParser.add_section("Randomizer")
        except ConfigParser.DuplicateSectionError:
            pass
        self._loadSettings()

    def savePrefs(self):
        self._logger.debug("Saving randomizer preferences.")
        for (name, value) in self._settings.items():
            self.setSetting(name, value)

    def setSetting(self, name, value):
        self._configParser.set("Randomizer", name, value)

    def _loadSettings(self):
        pass
##        try:
##            self._defaultScore = self._configParser.getint("Database",
##                                                           "defaultScore")
##        except ConfigParser.NoOptionError:
##            self._defaultScore = "10"
