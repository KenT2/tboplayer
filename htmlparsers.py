from HTMLParser import HTMLParser

class YtsearchParser(HTMLParser):

    def __init__(self):
        self.result = []
        HTMLParser.__init__(self)

    def handle_starttag(self, tag, attrs):
        if tag == 'div' : 
            for t in attrs:
                if "yt-lockup-dismissable" in t[1]: 
                    self.result.append(['',''])
                    break
        elif tag == 'a' : 
            if not len(self.result): return
            for t in attrs:
                if t[0] == "class" and "yt-uix-tile-link" in t[1]: 
                    self.result[len(self.result) - 1][0] = attrs[0][1]
                    for y in attrs:
                        if y[0] == "title":
                            self.result[len(self.result) - 1][1] = y[1]
                            break
                    break


class LyricWikiParser(HTMLParser):

    result = ""
    grab = False

    def __init__(self):
        HTMLParser.__init__(self)

    def handle_starttag(self, tag, attrs):
        if tag == "div" : 
            for t in attrs:
                if "lyricbox" in t[1]: 
                    self.grab = True
                    break
                    
    def handle_startendtag(self, tag, attrs):
        if self.grab and tag == "br":
            self.result += "\n"

    def handle_endtag(self, tag):
        if self.grab and tag == "div":
            self.grab = False

    def handle_charref(self, name):
        if self.grab:
            if name.startswith('x'):
                c = unichr(int(name[1:], 16))
            else:
                c = unichr(int(name))
            self.result += c

