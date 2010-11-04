def plural(count):
    if count == 1:
        return ''
    return 's'

class RedirectText:
    def __init__(self, textCtrl):
        self._out = textCtrl

    def write(self, string):
        self._out.WriteText(string)
