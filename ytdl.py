import json
import pexpect
import re
import string
import sys
import requests
import os

from hashlib import sha256
from threading import Thread
from time import sleep

# ***************************************
# YTDL CLASS
# ***************************************

class Ytdl:

    """
        interface for youtube-dl
    """
    
    _YTLOCATION = ''
    _YTLAUNCH_CMD = ''
    _YTLAUNCH_ARGS_FORMAT = ' -j -f %s --youtube-skip-dash-manifest "%s"'
    _YTLAUNCH_PLST_CMD = ''
    _YTLAUNCH_PLST_ARGS_FORMAT = ' -J -f mp4 --youtube-skip-dash-manifest "%s"'
    
    _FINISHED_STATUS = "\n"
    _WRN_STATUS = ".*WARNING:.*"
    _UPDATED_STATUS = ".*Restart youtube-dl to use the new version.*"
    _ERR_STATUS = ".*ERROR:.*"
    _SUDO_STATUS = "[sudo]"

    _SERVICES_REGEXPS = ()
    _ACCEPTED_LINK_REXP_FORMAT = "(http[s]{0,1}://(?:\w|\.{0,1})+%s\.(?:[a-z]{2,3})(?:\.[a-z]{2,3}){0,1}/)"
    
    _running_processes = {}
    finished_processes = {}
        
    MSGS = (0,1,2)
    
    start_signal = False
    end_signal = False
    updated_signal = False
    updating_signal = False
    update_failed_signal = False
    password_requested_signal = False
    has_password_signal = False

    _sudo_password = ''
    
    def __init__(self, options, yt_not_found_callback):
        self.set_options(options)
        self.yt_not_found_callback = yt_not_found_callback
        self.compile_regexps()

    def compile_regexps(self, updated=False):
        Thread(target=self._compile_regexps,args=[updated]).start()

    def _compile_regexps(self, updated=False):
        if not os.path.isfile(self._YTLOCATION): return
        self._SERVICES_REGEXPS = ()

        extractors_f = os.path.expanduser("~") + "/.tboplayer/ytdl_extractors"
        if not os.path.isfile(extractors_f) or updated:
            os.system(self._YTLOCATION + " --list-extractors > " + extractors_f)

        f = open(extractors_f, "r")
        extractors = f.read().split("\n")
        f.close()

        supported_service_re = re.compile("^[\w\d.]+$")
        supported_services = ()

        for e in extractors:
            if supported_service_re.match(e) != None:
                supported_services = supported_services + (e.lower(),)

        for s in list(sorted(supported_services, reverse=True)):
            if "." in s:
                self._SERVICES_REGEXPS = self._SERVICES_REGEXPS + (re.compile(s),)
            else:
                self._SERVICES_REGEXPS = self._SERVICES_REGEXPS + (re.compile(self._ACCEPTED_LINK_REXP_FORMAT % (s)),)
    
    def _response(self, url):
        process = self._running_processes[url][0]
        if self._terminate_sent_signal:
            r = (-2, '')
        else:
            data = process.before
            if self._WRN_STATUS in data:
                # warning message
                r = (0, self.MSGS[0])
            elif self._ERR_STATUS in data:
                # error message
                r = (-1, self.MSGS[1])
            else: 
                r = (1, data)
        self.finished_processes[url] = self._running_processes[url]
        self.finished_processes[url][1] = r
        del self._running_processes[url]

    def _get_link_media_format(self, url, f):
        return "m4a" if (f == "m4a" and "youtube." in url) else "mp4"

    def _background_process(self, url):
        process = self._running_processes[url][0]
        while self.is_running(url):
            try:
                index = process.expect([self._FINISHED_STATUS,
                                                pexpect.TIMEOUT,
                                                pexpect.EOF])
                if index == 1: continue
                elif index == 2:
                    del self._running_processes[url]
                    break
                else:
                    self._response(url)
                    break
            except Exception:
                del self._running_processes[url]
                break
            sleep(1)

    def _spawn_thread(self, url):
        self._terminate_sent_signal = False
        Thread(target=self._background_process, args=[url]).start()

    def retrieve_media_url(self, url, f):
        if self.is_running(url): return
        ytcmd = self._YTLAUNCH_CMD % (self._get_link_media_format(url, f), url)
        process = pexpect.spawn(ytcmd)
        self._running_processes[url] = [process, ''] # process, result
        self._spawn_thread(url)

    def retrieve_youtube_playlist(self, url):
        if self.is_running(url): return
        ytcmd = self._YTLAUNCH_PLST_CMD % (url)
        process = pexpect.spawn(ytcmd, timeout=180, maxread=50000, searchwindowsize=50000)
        self._running_processes[url] = [process, '']
        self._spawn_thread(url)
 
    def whether_to_use_youtube_dl(self, url): 
        to_use = url[:4] == "http" and any(regxp.match(url) for regxp in self._SERVICES_REGEXPS)
        if to_use and not os.path.isfile(self._YTLOCATION):
            self.yt_not_found_callback();
            return False
        return to_use

    def is_running(self, url = None):
        if url and not url in self._running_processes: 
            return False
        elif not url:
            return bool(len(self._running_processes))
        process = self._running_processes[url][0]
        return process is not None and process.isalive()

    def set_options(self, options):
        self._YTLOCATION=options.ytdl_location
        self._YTLAUNCH_CMD=self._YTLOCATION + self._YTLAUNCH_ARGS_FORMAT
        self._YTLAUNCH_PLST_CMD=self._YTLOCATION + self._YTLAUNCH_PLST_ARGS_FORMAT

    def set_password(self, password):
        self._sudo_password = password
        self.has_password_signal = True

    def quit(self):
        self._terminate_sent_signal = True
        for url in self._running_processes:
            self._running_processes[url][0].terminate(force=True)
    
    def check_for_update(self):
        if not os.path.isfile(self._YTLOCATION):
            return
        self.updating_signal = True
        Thread(target=self._check_for_update,args=[]).start()
        
    def _check_for_update(self):
        try:
            versionsurl = "http://rg3.github.io/youtube-dl/update/versions.json"
            versions = json.loads(requests.get(versionsurl).text)
        except Exception, e:
            print e
            self.updating_signal = False
            return

        current_version_hash = sha256(open(self._YTLOCATION, 'rb').read()).hexdigest()
        latest_version_hash = versions['versions'][versions['latest']]['bin'][1]

        if current_version_hash != latest_version_hash:
            self._update_process = pexpect.spawn("sudo %s -U" % self._YTLOCATION, timeout=60)
        
            while self.updating_signal:
                try:
                    index = self._update_process.expect([self._UPDATED_STATUS,
                                                    pexpect.TIMEOUT,
                                                    self._ERR_STATUS,
                                                    self._SUDO_STATUS])
                    if index in (1,2):
                        self.update_failed_signal = True
                        self.updating_signal = False
                        break
                    elif index == 3:
                        if self._sudo_password:                            
                            self.password_requested_signal = False
                            self._update_process.sendline(self._sudo_password)
                            self._sudo_password = ''
                        elif self._sudo_password == None:
                            self.password_requested_signal = False
                            self.updating_signal = False
                            self._sudo_password = ''
                            self._update_process.terminate(force=True)
                            break
                        elif not self.has_password_signal:
                            self.password_requested_signal = True
                    elif index == 0:
                        self.updating_signal = False
                        self.updated_signal = True
                        break
                except Exception, e:
                    print e
                    break
                sleep(5)
            if self.updated_signal:
                self.compile_regexps(updated=True)
            self.updating_signal = False

    def reset_processes(self):
        self._running_processes = {}
        self.finished_processes = {}

