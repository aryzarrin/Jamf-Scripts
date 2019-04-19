#!/bin/bash

userName=$(stat -f %Su /dev/console)

py_script="
from LaunchServices import LSSetDefaultRoleHandlerForContentType
from LaunchServices import LSSetDefaultHandlerForURLScheme
LSSetDefaultHandlerForURLScheme('mailto', 'com.microsoft.Outlook')
LSSetDefaultRoleHandlerForContentType('com.apple.mail.email', 0x00000002, 'com.microsoft.Outlook')
LSSetDefaultRoleHandlerForContentType('public.vcard', 0x00000002, 'com.microsoft.Outlook')
LSSetDefaultRoleHandlerForContentType('com.apple.ical.ics', 0x00000002, 'com.microsoft.Outlook')
LSSetDefaultRoleHandlerForContentType('com.microsoft.outlook16.icalendar', 0x00000002, 'com.microsoft.Outlook')
"
echo "Configuring mail settings for "$userName
sudo -u $userName -H python -c "$py_script"