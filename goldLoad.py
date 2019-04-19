#!/usr/bin/env python

################################################################################
# goldLoad.py                                                                  #
# Created by Arya (596322)                                                     #
#    03/19/2019                                                                #
#                                                                              #
# This script is used to run the Gold Load policies from Jamf after DEPNotify  #
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
GL_LOG = "/var/log/newGoldLoad.log"
DN_LOG = "/var/tmp/depnotify.log"
DN_APP = "/Applications/Utilities/DEPNotify.app"
DN_SCRIPT = "/Library/Application Support/JAMF/temp/DEPNotifyGoldLoad.py"
CAUTION_ICON = "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/AlertCautionIcon.icns"
goldLoadAgent = "/Library/LaunchAgents/com.boozallen.launchdn.plist"
goldLoadDaemon = "/Library/LaunchDaemons/com.boozallen.launchdepnotify.plist"

# path to JAMF binary
jamf = "/usr/local/bin/jamf"

# List of public facing policies
GOLD_LOAD_POLICY_LIST = sys.argv[4].split(', ')
policyCount = len(GOLD_LOAD_POLICY_LIST)

# List of policies to run silently
SECURITY_POLICIES = sys.argv[5].split(', ')
failedPolicies = []

# write to the specified log
# Gold Load log has time stamping enabled
def writeToLog(currentLog, message):
    with open(currentLog, "a+") as log:
        if currentLog is GL_LOG:
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

# checks policy outcome. Writes to gold load log and DepNotify app depending on policy type (user facing or not)
def checkPolicySuccess(policyType, returnCode, policyName, output, errors):
    if policyType is "GoldLoad":
        if returnCode != 0:
                failure = "Policy %s failed to run" % policyName
                writeToLog(GL_LOG, failure)
                writeToLog(GL_LOG, errors)
                failedPolicies.append(policyName)
        elif returnCode == 0:
            writeToLog(DN_LOG, "Status: Successfully Installed %s" % policyName)
            writeToLog(DN_LOG, 'Command: DeterminateManualStep: \n')

    elif policyType is "Security":
        if returnCode != 0:
                failure = "Policy %s failed to run" % policyName
                writeToLog(GL_LOG, failure)
                writeToLog(GL_LOG, errors)
                failedPolicies.append(policyName)

        elif returnCode == 0:
            writeToLog(GL_LOG, 'Policy: %s ran successfully!' % policyName)
            writeToLog(DN_LOG, 'Policy: %s ran successfully!' % policyName)

# runs the specified policy. 
# output and formatting determined by policy type (user facing or not)
def runPolicy(POLICY_LIST, policyType):
    if policyType is "GoldLoad":
        writeToLog(DN_LOG, "Command: DeterminateManual: %s" % policyCount)
        writeToLog(GL_LOG, "Beginning Gold Load Policies:")
        writeToLog(GL_LOG, "============================================\n")
        writeToLog(DN_LOG, "Installing software..")

    elif policyType is "Security":
        writeToLog(GL_LOG, "============================================")
        writeToLog(GL_LOG, "Beginning Security Policies: \n")
        writeToLog(DN_LOG, "Status: Applying the final touches..")

    for policy in POLICY_LIST:
        CURRENT_POLICY = [jamf, "policy", "-id", "%s" % policy]

        runPolicy = Popen(CURRENT_POLICY, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        policyName = readJamfLog(policy)

        if policyType is "GoldLoad":
            writeToLog(DN_LOG, "Status: Currently installing %s" % policyName)
        elif policyType is "Security":
            writeToLog(DN_LOG, "Currently installing %s" % policyName)

        output, errors = runPolicy.communicate()
        writeToLog(GL_LOG, output)
        returnCode = runPolicy.returncode

        checkPolicySuccess(policyType, returnCode, policyName, output, errors)


def goldLoadComplete():
    if not failedPolicies:
        writeToLog(DN_LOG, "Command: DeterminateOffReset:")
        writeToLog(DN_LOG, "Status: ")
        writeToLog(DN_LOG, "Command: MainTitle: Gold Load Complete!")
        writeToLog(DN_LOG, "Command: ContinueButtonRestart: Restart")
        writeToLog(DN_LOG, "Command: MainText: Congratulations! Your computer has finished Gold loading and is now ready to be used. "
        "Press the Restart button to finalize your setup and get started!")
    else:
        writeToLog(DN_LOG, "Command: DeterminateOffReset:")
        writeToLog(DN_LOG, "Command: Image: %s" % CAUTION_ICON)
        writeToLog(DN_LOG, "Status: Check Gold Load Log..")
        writeToLog(DN_LOG, "Command: MainTitle: Gold Load Completed With Errors")
        writeToLog(DN_LOG, "Command: ContinueButtonRestart: Restart")
        writeToLog(DN_LOG, "Command: MainText: The Gold Load has completed but some policies failed to run. "
        "Please check the Gold Load log for more information. "
        "The computer will need to restart to finish applying changes. "
        "Press the Restart button to continue.")

def goldLoadCleanup():
    LoggedInUser = subprocess.check_output(["stat", "-f%Su", "/dev/console"]).strip()
    userID = subprocess.check_output(["id", "-u", LoggedInUser]).strip()

    # unload LaunchAgent
    writeToLog(GL_LOG, "Removing LaunchAgent")
    unLoadAgent = Popen(["launchctl", "asuser", "%s" % userID, "unload", "%s" % goldLoadAgent], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    unLoadAgentResult, unloadAgentErrors = unLoadAgent.communicate()
    writeToLog(GL_LOG, unLoadAgentResult)
    writeToLog(GL_LOG, unloadAgentErrors)
    
    # delete LaunchAgent
    Popen(["rm", "%s" % goldLoadAgent])

    # delete LaunchDaemon
    writeToLog(GL_LOG, "Removing LaunchDaemon")
    Popen(["rm", "-f", "%s" % goldLoadDaemon])

    # delete the DEPNotify application
    writeToLog(GL_LOG, "Removing DEPNotify.app")
    Popen(["rm", "-rf", "%s" % DN_APP])

    # delete the DEPNotify script
    writeToLog(GL_LOG, "removing DEPNotify Script")
    Popen(["rm", "-f", "%s" % DN_SCRIPT])

    # submits inventory information after gold load is complete
    writeToLog(GL_LOG, "Performing Recon")
    runRecon = Popen(["%s" % jamf, "policy", "-id", "61"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    runReconResult, runReconErrors = runRecon.communicate()
    writeToLog(GL_LOG, runReconResult)
    writeToLog(GL_LOG, runReconErrors)

    # remove DEPNotify Script
    writeToLog(GL_LOG, "Removing DEPNotify Script")



def main():
    runPolicy(GOLD_LOAD_POLICY_LIST, "GoldLoad")
    runPolicy(SECURITY_POLICIES, "Security")
    if not failedPolicies:
        goldLoadComplete()
        goldLoadCleanup()
    else:
        writeToLog(GL_LOG, "The following policies failed:")
        for policy in failedPolicies:
            writeToLog(GL_LOG, "%s" % policy) 
              
        goldLoadComplete()
        goldLoadCleanup()





if __name__ == "__main__":
    main()