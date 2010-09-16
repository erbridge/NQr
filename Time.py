def _DoRough(time, big, bigname, little, littlename):
    b = int((time + little / 2) / little / big)
    l = int(((time + little / 2) / little) % big)
#    print "b =", b, "l =", l, "time =", time, "/", b * big * little + l * little
    t = str(b) + " " + bigname
    if b > 1:
        t += "s"
    if l != 0:
        t += " " + str(l) + " " + littlename
        if l > 1:
            t += "s"
    return t

# Return a string roughly describing the time difference handed in.
def RoughAge(time):
    if time < 60*60:
        return _DoRough(time, 60, "minute", 1, "second")
    if time < 24*60*60:
        return _DoRough(time, 60, "hour", 60, "minute")
    if time < 7*24*60*60:
        return _DoRough(time, 24, "day", 60*60, "hour")
    if time < 365*24*60*60:
        return _DoRough(time, 7, "week", 24*60*60, "day")
    # yes, this measure of a year is fairly crap :-)
    return _DoRough(time, 52, "year", 7*24*60*60, "week")
    return "I dunno"

if __name__ == '__main__':
    import random

    text = RoughAge(2400685)
    print text
    assert text == "4 weeks"
    r = random.SystemRandom()
    for x in range(100):
        y = r.randrange(100000000)
        print y, RoughAge(y)
            
