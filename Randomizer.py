## Randomization Algorithm
## TODO: work out time factor if track has never been played: poss use time
##       since added to database?
## TODO: add score threshold functionality

##from Database import Database
import random
import time

## tracks with a score >= scoreThreshold get played
## by default, -10s are not played
class Randomizer:
    def __init__(self, db, scoreThreshold=-9):
        self.db = db
        self.scoreThreshold = scoreThreshold

## will throw exception if databse is empty?
    def chooseTrackID(self):
##        print time.time()
        (trackWeightList, totalWeight) = self.createLists()
        selector = random.random() * totalWeight
        for [trackID, weight] in trackWeightList:
            selector -= weight
            if selector < 0:
##                print time.time()
                return trackID

    def createLists(self):
        rawTrackIDList = self.db.getAllTrackIDs()
        if rawTrackIDList == None:
            print "The database is empty."
            return None
        trackWeightList = []
        totalWeight = 0
        for (trackID, ) in rawTrackIDList:
            time = self.db.getSecondsSinceLastPlayedFromID(trackID)
            score = self.db.getScoreValueFromID(trackID) + 11 ## creates a positive score
            if time == None:
                time = 5 * (len(trackWeightList) + 1)
            if score < self.scoreThreshold + 11:
                score = 0
            weight = self.getWeight(score, time)
            trackWeightList.append([trackID, weight])
            totalWeight += weight
        return trackWeightList, totalWeight

#### poss "reverse(sorted(" makes operation slower, not faster
##    def chooseTrackID(self):
####        print time.time()
##        (trackIDList, weightList) = self.createLists()
##        selector = random.random() * sum(weightList)
##        for weight, trackID in reversed(sorted(zip(weightList, trackIDList))): ## make array of arrays instead
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

    def getWeight(self, score, time):
        weight = score * time
        return weight

##r = Randomizer()
##r.chooseTrackID()
