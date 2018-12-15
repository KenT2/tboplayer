#!/usr/bin/python
#---------------------------------------
# vtt-to-srt.py
# (c) Jansen A. Simanullang
# 02.04.2016 13:39
# LAST CHANGE:
# 02.04.2016 16:56
# recursively visit subdirectories
#---------------------------------------
# usage: python vtt-to-srt.py
#
# example:
# python vtt-to-srt.py
#
# features:
# check a directory and all its subdirectories
# convert all vtt files to srt subtitle format
#
# real world needs:
# converting Coursera's vtt subtitle
# modified by Henio Tierra to provide funcionality to tboplayer

import os, re, sys, io
from stat import *


def convertContent(fileContents):

	replacement = re.sub(r'([\d]+)\.([\d]+)', r'\1,\2', fileContents)
	replacement = re.sub(r'WEBVTT\n\n', '', replacement)
	replacement = re.sub(r'^\d+\n', '', replacement)
	replacement = re.sub(r'\n\d+\n', '\n', replacement)

	return replacement
	


def fileCreate(strNamaFile, strData):
	#--------------------------------
	# fileCreate(strNamaFile, strData)
	# create a text file
	#
	try:
	
		f = open(strNamaFile, "w")
		f.writelines(str(strData))
		f.close()
	
	except IOError:
	
		strNamaFile = strNamaFile.split(os.sep)[-1]
		f = open(strNamaFile, "w")
		f.writelines(str(strData))
		f.close()
		
	print "file created: " + strNamaFile + "\n"
	
	
	
def readTextFile(strNamaFile):

	f = open(strNamaFile, mode='r')
	
	print "file being read: " + strNamaFile + "\n"
	
	return f.read().decode("utf8").encode('ascii', 'ignore')
	


def vtt_to_srt(strNamaFile):

	fileContents = readTextFile(strNamaFile)
	
	strData = ""
	
	strData = strData + convertContent(fileContents)
	
	strNamaFile = strNamaFile.replace(".vtt",".srt")
		
	print strNamaFile
		
	fileCreate(strNamaFile, strData)
	
	
	
def walktree(TopMostPath, callback):

    '''recursively descend the directory tree rooted at TopMostPath,
       calling the callback function for each regular file'''

    for f in os.listdir(TopMostPath):
	
        pathname = os.path.join(TopMostPath, f)
        mode = os.stat(pathname)[ST_MODE]
		
        if S_ISDIR(mode):
		
            # It's a directory, recurse into it
            walktree(pathname, callback)
			
        elif S_ISREG(mode):
		
            # It's a file, call the callback function
            callback(pathname)
			
        else:
		
            # Unknown file type, print a message
            print 'Skipping %s' % pathname

			

def convertVTTtoSRT(file):
	
	if '.vtt' in file:
	
		vtt_to_srt(file)
		
def vtt2srt(directory):
	
	#just edit the path below

	TopMostPath = directory

	walktree(TopMostPath, convertVTTtoSRT)
	
if __name__ == '__main__':
    vtt2srt(sys.argv[1])
