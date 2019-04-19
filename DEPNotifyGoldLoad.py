#!/usr/bin/python

################################################################################
# DEPNotifyGoldLoad.py                                                         #
# Created by Arya (596322)                                                     #
#    02/26/2019                                                                #
#                                                                              #
# This script is used to launch the DEPNotify application during the Gold Load #
# process as well as performing checks to help ensure the gold load's success. #
################################################################################

import subprocess
import os
from subprocess import Popen
import sys
import time
import datetime
import urllib2

# sets locations of log files to be used for the Gold Load and DEPNotify
GL_LOG = "/var/log/newGoldLoad.log"
DN_LOG = "/var/tmp/depnotify.log"

# path to icons used
BAH_ICON = "/Library/Application Support/JAMF/temp/icons/boozallenbadge.jpg"
FAIL_ICON = "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/AlertStopIcon.icns"

# URL for video used in the initial connection test
VIDEO_URL = "https://www.youtube.com/watch?v=ay7zwM6TLhE"

# path to JAMF
jamf = "/usr/local/bin/jamf"

#location of Dep Notify App
DN_APP = "/Applications/Utilities/DEPNotify.app"

# build command lists for Popen processes used in methods
CHECK_FINDER = ["pgrep", "-x", "Finder"]
CHECK_DOCK = ["pgrep", "-x", "Dock"]
checkJSS = ["%s" % jamf, "checkJSSConnection"]
TEST_POLICY = ["%s" % jamf, "policy", "-trigger", "iscasperup"]
GOLD_LOAD_TRIGGER = ["%s" % jamf, "policy", "-trigger", "depnotifyGoldLoad"]

# Obtain logged in user and user ID to launch DEPNotify
def checkForLoggedInUser():
    LoggedInUser = subprocess.check_output(["stat", "-f%Su", "/dev/console"]).strip()
    userID = subprocess.check_output(["id", "-u", LoggedInUser]).strip()

    while LoggedInUser == "root" or LoggedInUser == "_mbsetupuser":
        LoggedInUser = subprocess.check_output(["stat", "-f%Su", "/dev/console"]).strip()
        userID = subprocess.check_output(["id", "-u", LoggedInUser]).strip()

    return LoggedInUser, userID

# Checks if Finder has loaded
def checkFinderRunning():
    finderCheck = Popen(CHECK_FINDER, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    finderCheck.communicate()[0]
    finderReturnCode = finderCheck.returncode

    if finderReturnCode is 0:
        print "Finder is active"

    return finderReturnCode

# Checks if the Dock has loaded
def checkDockRunning():
    dockCheck = Popen(CHECK_FINDER, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    dockCheck.communicate()[0]
    dockReturnCode = dockCheck.returncode

    if dockReturnCode is 0:
        print "Dock is active"

    return dockReturnCode

# Check to see if Finder and the Dock are present before attempting to launch the DEPNotify application
def appLaunchPreCheck():
    writeToLog(GL_LOG, "Checking for Finder")
    while checkFinderRunning() is not 0:
        continue
    
    writeToLog(GL_LOG, "Finder active! Checking for Dock")

    while checkDockRunning() is not 0:
        continue

    writeToLog(GL_LOG, "Dock active! Opening DEPNotify App..")

def writeToLog(currentLog, message):
    with open(currentLog, "a+") as log:
        if currentLog is GL_LOG:
            timeStamp = datetime.datetime.now().strftime("%m-%d-%y %H:%M:%S")
            log.write(timeStamp + ': ' + message + '\n')
        else:
            log.write(message + '\n')

# Launch DEPNotify application
def launchDEPNotify(userID, DN_APP):
    DEP_NOTIFY_LAUNCH = ["launchctl", "asuser", "%s" % userID, "open", "%s" % DN_APP, "--args", "-fullScreen"]
    subprocess.Popen(DEP_NOTIFY_LAUNCH)

# Apply icon, initial message and look of the DEP Notify window
def depNotifySetup():
    writeToLog(DN_LOG, "Command: WindowStyle: ActivateOnStep")
    writeToLog(DN_LOG, "Status: Welcome to your Booz Allen Mac!")
    writeToLog(DN_LOG, "Command: Image: %s" % BAH_ICON)
    # Check to see if there is an active internet connection to access the initial video
    # Returns a message indicating the internet connection is not active
    try:
        urllib2.urlopen(VIDEO_URL)
        writeToLog(DN_LOG, "Command: YouTube: ay7zwM6TLhE")
        time.sleep(10)
        writeToLog(DN_LOG, "Status: Please wait while we configure your machine..")
    except urllib2.HTTPError, e:
        print(e.code)
        writeToLog(DN_LOG, "Status: No Internet Connection")
    except urllib2.URLError, e:
        print(e.args)
        writeToLog(DN_LOG, "Command: MainTitle: No Internet Connection!")
        writeToLog(DN_LOG, "Status: An Error Occurred")
        writeToLog(DN_LOG, "Command: Image: %s" % FAIL_ICON)
        writeToLog(DN_LOG, "Command: MainText: There is a problem with your Internet Connection. "
                           "Please check your wired or wireless connection and restart your machine.")

# changes DEPNotify Main text to display goldload failure message
def goldLoadFail():
    writeToLog(DN_LOG, "Command: Image: %s" % FAIL_ICON)
    writeToLog(DN_LOG, "Command: MainTitle: Gold Load Failed!")
    writeToLog(DN_LOG, "Status: Error: Cannot reach management server.")
    writeToLog(DN_LOG, "Command: MainText: We are unable to complete the Gold Load at this time. "
                   "Please check your internet connection as it appears we are not able to connect to the management server. "
                   "If you need assistance please contact the Apple team at IS_Apple@bah.com")

# Begins Gold Load Process
def startGoldLoad():
    writeToLog(DN_LOG, "Status: Beginning Gold Load..")
    launchGoldLoad = Popen(GOLD_LOAD_TRIGGER, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    launchGoldLoad
    writeToLog(GL_LOG, launchGoldLoad.communicate()[0])

# Method to check for Jamf Pro connection and run test policy prior to attempting Gold Load
def goldLoadPreCheck(currentUser):
    writeToLog(GL_LOG, "Beginning Gold Load Pre-Check:")
    writeToLog(DN_LOG, "Command: MainTitle: Please Wait")
    writeToLog(GL_LOG, "============================================")
    writeToLog(DN_LOG, "Status: Beginning Gold Load Pre-Checks...")

    # Begin check for connection to Jamf
    writeToLog(GL_LOG, "Checking for connection to Jamf:")
    jamfConnectionCheck = Popen(checkJSS, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    connectionResult = jamfConnectionCheck.communicate()[0]
    returnCode = jamfConnectionCheck.returncode

    if "The JSS is available" in connectionResult:
        writeToLog(GL_LOG, "Connection to Jamf succesful!")
        # Run test policy
        runTestPolicy = Popen(TEST_POLICY, stdout=subprocess.PIPE)
        testPolicyResult = runTestPolicy.communicate()[0]
        if "Script result: up" in testPolicyResult:
            writeToLog(GL_LOG, "Test Policy ran successfully!")
            startGoldLoad()
        elif "No policies were found" in testPolicyResult:
            writeToLog(GL_LOG, "Failed to run Test Policy: policy not found.    - Check machine is in scope")
            goldLoadFail()
        else:
            writeToLog(GL_LOG, "Failed to run test policy")
            goldLoadFail()
    elif returnCode != 0:
        writeToLog(GL_LOG, "Failed to connect to Jamf.")
        writeToLog(GL_LOG, "**********Check internet connection and restart machine**********")
        goldLoadFail()
        time.sleep(5)
        exit(1)

def main():
    # Remove any previous Gold Load and DEPNotify logs
    try:
        os.remove(GL_LOG)
    except OSError:
        print "Gold Load log does not exist"

    try:
        os.remove(DN_LOG)
    except OSError:
        print "DEPNotify Log does not exist"

    #Create new Gold Load Log
    open(GL_LOG, "w")

    currentUser, uID = checkForLoggedInUser()

    writeToLog(GL_LOG, "Logged in User: %s" % currentUser)
    writeToLog(GL_LOG, "User ID: %s" % uID)
    appLaunchPreCheck()
    launchDEPNotify(uID, DN_APP)
    depNotifySetup()
    time.sleep(43)
    goldLoadPreCheck(currentUser)



if __name__ == "__main__":
    main()
