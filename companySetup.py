#!/usr/bin/env python

################################################################################
# jamfProcess.py                                                               #
# Created by Arya.                                                             #
#    03/19/2019                                                                #
#                                                                              #
# This script is used to run the Imaging policies from Jamf after DEPNotify    #
# has performed its checks.                                                    #
################################################################################

import SystemConfiguration
import Foundation
import subprocess
import os
from subprocess import Popen
import time
import datetime
import sys

# resources used on the system
JAMF_LOG = "/private/var/log/jamf.log"
IMAGE_LOG = "/var/log/newImage.log"
DN_LOG = "/var/tmp/depnotify.log"
DN_APP = "/Applications/Utilities/DEPNotify.app"
DN_SCRIPT = "/Library/Application Support/JAMF/temp/DEPNotifyImage.py"
CAUTION_ICON = "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/AlertCautionIcon.icns"
imageLoadAgent = "/Library/LaunchAgents/com.<company name>.launchdn.plist"
imageLoadDaemon = "/Library/LaunchDaemons/com.<company name>.launchdepnotify.plist"

# path to JAMF binary
jamf = "/usr/local/bin/jamf"

# List of public facing policies
IMAGE_POLICY_LIST = sys.argv[4].split(', ')
policyCount = len(IMAGE_POLICY_LIST)

# List of policies to run silently
SECURITY_POLICIES = sys.argv[5].split(', ')
failedPolicies = []

# write to the specified log
# Image log has time stamping enabled
def writeToLog(currentLog, message):
    with open(currentLog, "a+") as log:
        if currentLog is IMAGE_LOG:
            timeStamp = datetime.datetime.now().strftime("%m-%d-%y %H:%M:%S")
            for line in message.split("\n"):
                log.write('{0}: {1}\n'.format(timeStamp, line))
        else:
            log.write(message + '\n')

# read an active log (i.e. jamf.log)
def readActiveLog(logFile):
        logFile.seek(0, os.SEEK_END) # End-of-file
        while True:
             line = logFile.readline()
             if not line:
                 time.sleep(0.1)    # Sleep briefly
                 continue
             yield line

# extract policyName from the jamf log
def readJamfLog(policyNumber):
    # reads the jamf log and watches for the policy ID being called then extracts the name from the next line
    searchText = "Checking for policy ID %s..." % policyNumber
    jamfLog = open (JAMF_LOG, "r")
    logLines = readActiveLog(jamfLog)

    for line in logLines:
        if searchText in line:
            policyName = next(logLines)
            return policyName.split("Executing Policy ")[1].strip("\n")

# checks policy outcome. Writes to imaging log and DepNotify app depending on policy type (user facing or not)
def checkPolicySuccess(policyType, returnCode, policyName, output, errors):
    if policyType is "Public":
        if returnCode != 0:
                failure = "Policy %s failed to run" % policyName
                writeToLog(IMAGE_LOG, failure)
                writeToLog(IMAGE_LOG, errors)
                failedPolicies.append(policyName)
        elif returnCode == 0:
            writeToLog(DN_LOG, "Status: Successfully Installed %s" % policyName)
            writeToLog(DN_LOG, 'Command: DeterminateManualStep: \n')

    elif policyType is "Security":
        if returnCode != 0:
                failure = "Policy %s failed to run" % policyName
                writeToLog(IMAGE_LOG, failure)
                writeToLog(IMAGE_LOG, errors)
                failedPolicies.append(policyName)

        elif returnCode == 0:
            writeToLog(IMAGE_LOG, 'Policy: %s ran successfully!' % policyName)
            writeToLog(DN_LOG, 'Policy: %s ran successfully!' % policyName)

# runs the specified policy. 
# output and formatting determined by policy type (user facing or not)
def runPolicy(POLICY_LIST, policyType):
    if policyType is "Public":
        writeToLog(DN_LOG, "Command: DeterminateManual: %s" % policyCount)
        writeToLog(IMAGE_LOG, "Beginning Image Policies:")
        writeToLog(IMAGE_LOG, "============================================\n")
        writeToLog(DN_LOG, "Installing software..")

    elif policyType is "Security":
        writeToLog(IMAGE_LOG, "============================================")
        writeToLog(IMAGE_LOG, "Beginning Security Policies: \n")
        writeToLog(DN_LOG, "Status: Applying the final touches..")

    for policy in POLICY_LIST:
        CURRENT_POLICY = [jamf, "policy", "-id", "%s" % policy]

        runPolicy = Popen(CURRENT_POLICY, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        policyName = readJamfLog(policy)

        if policyType is "Public":
            writeToLog(DN_LOG, "Status: Currently installing %s" % policyName)
        elif policyType is "Security":
            writeToLog(DN_LOG, "Currently installing %s" % policyName)

        output, errors = runPolicy.communicate()
        writeToLog(IMAGE_LOG, output)
        returnCode = runPolicy.returncode

        checkPolicySuccess(policyType, returnCode, policyName, output, errors)


def imageComplete():
    if not failedPolicies:
        writeToLog(DN_LOG, "Command: DeterminateOffReset:")
        writeToLog(DN_LOG, "Status: ")
        writeToLog(DN_LOG, "Command: MainTitle: Image Complete!")
        writeToLog(DN_LOG, "Command: ContinueButtonRestart: Restart")
        writeToLog(DN_LOG, "Command: MainText: Congratulations! Your computer has finished Imaging and is now ready to be used. "
        "Press the Restart button to finalize your setup and get started!")
    else:
        writeToLog(DN_LOG, "Command: DeterminateOffReset:")
        writeToLog(DN_LOG, "Command: Image: %s" % CAUTION_ICON)
        writeToLog(DN_LOG, "Status: Check Imaging Log..")
        writeToLog(DN_LOG, "Command: MainTitle: Imaging Completed With Errors")
        writeToLog(DN_LOG, "Command: ContinueButtonRestart: Restart")
        writeToLog(DN_LOG, "Command: MainText: The Image has completed but some policies failed to run. "
        "Please check the Imaging log for more information. "
        "The computer will need to restart to finish applying changes. "
        "Press the Restart button to continue.")

def imageCleanup():
    LoggedInUser = subprocess.check_output(["stat", "-f%Su", "/dev/console"]).strip()
    userID = subprocess.check_output(["id", "-u", LoggedInUser]).strip()

    # unload LaunchAgent
    writeToLog(GL_LOG, "Removing LaunchAgent")
    unLoadAgent = Popen(["launchctl", "asuser", "%s" % userID, "unload", "%s" % imageLoadAgent], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    unLoadAgentResult, unloadAgentErrors = unLoadAgent.communicate()
    writeToLog(GL_LOG, unLoadAgentResult)
    writeToLog(GL_LOG, unloadAgentErrors)
    
    # delete LaunchAgent
    Popen(["rm", "%s" % imageLoadAgent])

    # delete LaunchDaemon
    writeToLog(GL_LOG, "Removing LaunchDaemon")
    Popen(["rm", "-f", "%s" % imageLoadDaemon])

    # delete the DEPNotify application
    writeToLog(GL_LOG, "Removing DEPNotify.app")
    Popen(["rm", "-rf", "%s" % DN_APP])

    # delete the DEPNotify script
    writeToLog(GL_LOG, "removing DEPNotify Script")
    Popen(["rm", "-f", "%s" % DN_SCRIPT])

    # submits inventory information after image is complete
    writeToLog(GL_LOG, "Performing Recon")
    runRecon = Popen(["%s" % jamf, "recon"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    runReconResult, runReconErrors = runRecon.communicate()
    writeToLog(GL_LOG, runReconResult)
    writeToLog(GL_LOG, runReconErrors)

    # remove DEPNotify Script
    writeToLog(IMAGE_LOG, "Removing DEPNotify Script")



def main():
    runPolicy(IMAGE_POLICY_LIST, "Public")
    runPolicy(SECURITY_POLICIES, "Security")
    if not failedPolicies:
        imageComplete()
        imageCleanup()
    else:
        writeToLog(IMAGE_LOG, "The following policies failed:")
        for policy in failedPolicies:
            writeToLog(IMAGE_LOG, "%s" % policy) 
              
        imageComplete()
        imageCleanup()





if __name__ == "__main__":
    main()
