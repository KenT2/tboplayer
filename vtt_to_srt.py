#!/usr/bin/python
#---------------------------------------
# vtt_to_srt.py
# (c) Jansen A. Simanullang
#---------------------------------------
# Usage: 
#
#	python vtt_to_srt.py pathname [-r]
#	
#	pathname - a file or directory with files to be converted'
#
#	-r       - walk path recursively
#
# example:
# python vtt_to_srt.py
#
# features:
# convert file individually
# check a directory and all its subdirectories
# convert all vtt files to srt subtitle format
#
# real world cases:
# convert vtt web subtitles

import os, re, sys, io
from stat import *


def convertContent(fileContents):

	replacement = re.sub(r'(\d\d:\d\d:\d\d).(\d\d\d) --> (\d\d:\d\d:\d\d).(\d\d\d)(?:[ \-\w]+:[\w\%\d:]+)*\n', r'\1,\2 --> \3,\4\n', fileContents)
	replacement = re.sub(r'(\d\d:\d\d).(\d\d\d) --> (\d\d:\d\d).(\d\d\d)(?:[ \-\w]+:[\w\%\d:]+)*\n', r'\1,\2 --> \3,\4\n', replacement)
	replacement = re.sub(r'(\d\d).(\d\d\d) --> (\d\d).(\d\d\d)(?:[ \-\w]+:[\w\%\d:]+)*\n', r'\1,\2 --> \3,\4\n', replacement)
	replacement = re.sub(r'WEBVTT\n', '', replacement)
	replacement = re.sub(r'Kind:[ \-\w]+\n', '', replacement)
	replacement = re.sub(r'Language:[ \-\w]+\n', '', replacement)
	#replacement = re.sub(r'^\d+\n', '', replacement)
	#replacement = re.sub(r'\n\d+\n', '\n', replacement)
	replacement = re.sub(r'<c[.\w\d]*>', '', replacement)
	replacement = re.sub(r'</c>', '', replacement)
	replacement = re.sub(r'<\d\d:\d\d:\d\d.\d\d\d>', '', replacement)
	replacement = re.sub(r'::[\-\w]+\([\-.\w\d]+\)[ ]*{[.,:;\(\) \-\w\d]+\n }\n', '', replacement)
	replacement = re.sub(r'Style:\n##\n', '', replacement)
	
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
            callback(pathname, rec)
			
        else:
		
            # Unknown file type, print a message
            print 'Skipping %s' % pathname


def walkdir(TopMostPath, callback):

	for f in os.listdir(TopMostPath):
		pathname = os.path.join(TopMostPath, f)
		
		if not os.path.isdir(pathname):
			
			# It's a file, call the callback function
			callback(pathname)


def convertVTTtoSRT(f):
	
	if '.vtt' in f:
	
		vtt_to_srt(f)

		
def vtts_to_srt(directory, rec = False):
	
	TopMostPath = directory

	if rec:

		walktree(TopMostPath, convertVTTtoSRT)

	else:

		walkdir(TopMostPath, convertVTTtoSRT)


def print_usage():

	print '\nUsage:\tpython vtt_to_srt.py pathname [-r]\n'
	
	print '\tpathname\t- a file or directory with files to be converted'

	print '\t-r\t\t- walk path recursively\n'

	
if __name__ == '__main__':


	if len(sys.argv) < 2 or sys.argv[1] == '--help' or not os.path.exists(sys.argv[1]):

		print_usage()

		exit()

	path = sys.argv[1]

	rec = True if len(sys.argv) > 2 and sys.argv[2] == '-r' else False

	if os.path.isdir(path):

		vtts_to_srt(path, rec)

	else:

		vtt_to_srt(path)

