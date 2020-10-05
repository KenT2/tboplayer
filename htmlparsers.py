from HTMLParser import HTMLParser

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

