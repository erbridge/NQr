## Randomization Algorithm
## TODO: work out time factor if track has never been played: poss use time
##       since added to database?
## TODO: work out what weights should be (poss make sliders)
## TODO: getWeights from a text option (convert into python code) allowing
##       length of list etc.

from Errors import *
from Time import RoughAge
from Util import plural
import random
import time

## tracks with a score >= scoreThreshold get played
## by default, -10s are not played
class Randomizer:
    def __init__(self, db, trackFactory, loggerFactory, scoreThreshold=-9):
        self.db = db
        self.trackFactory = trackFactory
        self._logger = loggerFactory.getLogger("NQr.Randomizer", "debug")
        self.scoreThreshold = scoreThreshold

    def chooseTrack(self):
        track = self.chooseTracks(1)[0]
        return track

    def chooseTracks(self, number, exclude):
        self._logger.debug("Selecting "+str(number)+" track" + plural(number)
                           + ".")
        trackIDs = self.chooseTrackIDs(number, exclude)
        tracks = []
        for trackID in trackIDs:
            tracks.append(self.trackFactory.getTrackFromID(self.db, trackID))
        return tracks

## will throw exception if database is empty?
    def chooseTrackIDs(self, number, exclude):
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
                    trackIDs.append(trackID)
                    break
        return trackIDs

    def createLists(self, exclude):
        self._logger.debug("Creating weighted list of tracks.")
        oldest = self.db.getOldestLastPlayed()
        self._logger.info("Oldest is " + str(oldest) + " (" + RoughAge(oldest)
                          + ")")
        rawTrackIDList = self.db.getAllTrackIDs()
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
            time = self.db.getSecondsSinceLastPlayedFromID(trackID)
            score = self.db.getScoreValueFromID(trackID) + 11
            ## creates a positive score
            if time == None:
                time = oldest
            if score < self.scoreThreshold + 11:
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
##        rawTrackIDList = self.db.getAllTrackIDs()
##        if rawTrackIDList == None:
##            print "The database is empty."
##            return None
##        trackIDList = []
##        for (trackID, ) in rawTrackIDList:
##            trackIDList.append(trackID)
##        weightList = []
####        totalWeight = 0
##        for trackID in trackIDList:
##            time = self.db.getSecondsSinceLastPlayedFromID(trackID)
##            score = self.db.getScoreValueFromID(trackID) + 11 ## creates a positive score
##            if time == None:
##                time = 5 * (len(trackIDList) + 1)
##            if score < self.scoreThreshold + 11:
##                score = 0
##            weight = self.getWeight(score, time)
##            weightList.append(weight)
####            totalWeight += weight
##        return trackIDList, weightList##, totalWeight
