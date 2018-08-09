#!/usr/bin/env python
# Check for change in master node of the Wiso cluster.
# There are 2 clusters: test (mst), and production (mss).
# If the master node change, send a email notification.
# A basic documentation can be found in 
# /root/marcelo/bin/wiso/check_wiso.md
# 
# Marcelo Garcia 
# May/2018.
#

import sys
import paramiko as pk
import ConfigParser as cfgparser
import time
from optparse import OptionParser

# Global variables.
# Nagios exit values.
STATE_OK = 0
STATE_WARNING = 1
STATE_CRITICAL = 2
STATE_UNKNOWN = 3

WISO_CONFIG = "/maint/nagios/etc/wiso_master.conf"

def read_config(config, wiso_cluster):
    """Read a configuration file using the 'ConfigParser' object. The 
       'config_file' is similar to MS-Windows INI file."""
    # Read config file.
    try:
        master = config.get(wiso_cluster, 'master')
        # Just for safety, clean the variable from spurious characters.
        master = master.strip()
    except cfgparser.NoSectionError:
        # The section/cluster given is not valid.
        print sys.argv[0] + ": section " + wiso_cluster + " does not exists"
        # Print the list with sections in the config file.
        print "Options are" + ",".join([" %s" % ss for ss in config.sections()])
        sys.exit(STATE_UNKNOWN)

    # Return
    return master

def read_pcs(master_cfg, debug=False):
    """SSH to master node and query for the master with 'pcs status'. The
       function returns only the host name, but there is no check to make
       sure that is a valid hostname."""

    if debug:
        # During the debug, return the master as empty string to simulate
        # the pcs not having a master.
        master = ""
        return master

    # Now we ssh to 'master_cfg' and query the master of the cluster.
    try:
        command = "pcs status | grep Masters| awk '{print $3}'"
        ssh_client = pk.SSHClient()
        ssh_client.load_system_host_keys()
        ssh_client.connect(master_cfg)
        stdin,stdout, stderr = ssh_client.exec_command(command)
        out_cmd = stdout.read()
        ssh_client.close()
    except IOError as error:
        # Something went wrong... 
        # Probably bad host name.
        print error
        sys.exit(STATE_UNKNOWN)
    else:
        # If we are here, there was no exception...
        # 
        # The 'ssh' should return only the name of the master, and nothing
        # else, so we can assume that it has only the server name.
        master = out_cmd.strip()

    # There is no check if "master" is a valid host name. 
    return master

def send_notification(email_info):
    """Send an email based on a dictionary with the fields for the message"""
    import smtplib
    from email.mime.text import MIMEText

    msg = MIMEText(email_info['message'])
    msg['Subject'] = email_info['Subject']
    msg['From'] = 'wiso@' + email_info['From'] + '.mysite.com'
    msg['To'] = email_info['To']
    s = smtplib.SMTP('localhost')
    dummy = s.sendmail('wiso@' + email_info['From'] + '.mysite.com', \
                       [email_info['To']], msg.as_string())
    # return nothing.
    return

def notif_master_change(master_old, master_new, addr2notify):
    """Send a notification to 'addr2notify' for change in the master from 
    'master_old' to 'master_new'"""

    email_info = {}
    email_info['message']  = "Wiso server changed from " + master_old + \
                             " to " + master_new 
    email_info['From'] = master_new
    email_info['To'] = addr2notify
    email_info['Subject'] = "Wiso server changed!!"

    send_notification(email_info)

    return

def notif_no_pcs_master(master, addr2notify):
    """Notification to 'addr2notify' about no pcs master found."""

    email_info = {}
    email_info['message'] = "Could not get master node from 'pcs status'!! \n" + \
          "Please check status of Wiso cluster!"
    email_info['From'] = master
    email_info['To'] = addr2notify
    email_info['Subject'] = "No pcs server found"

    send_notification(email_info)

    return

#
# Main routine.
#
if __name__ == "__main__":
    wiso_cluster = ""
    master_cfg = ""
    master_pcs = ""

    # Process command line arguments.
    parser = OptionParser()
    parser.add_option("-c", "--cluster", type="string", dest="wiso_cluster",
            help="Wiso cluster to query, 'mst' or 'mss'")
    (options, args) = parser.parse_args()

    if not options.wiso_cluster:
        print sys.argv[0] + ": missing Wiso cluster.\n" + \
            "Use '-h' or '--help' for options"
        sys.exit(STATE_UNKNOWN)
    else:
        wiso_cluster = options.wiso_cluster.upper()
        # print wiso_cluster

    # Open the config file
    config = cfgparser.ConfigParser()
    config.read(WISO_CONFIG)
    # Read config file and return the 'master' defined.
    master_cfg = read_config(config, wiso_cluster)

    # Now we ssh to 'master_cfg' and query the master of the cluster.
    master_pcs = read_pcs(master_cfg, debug=False)
    print "master = {0}".format(master_pcs)

    if master_pcs != master_cfg :
        # First we need to check that we have a valid host as master. During
        # a maintenance, or a more serious problem, there could be no master
        # defined.

        # Define a counter to set a upper limit of tries for the new pcs 
        # master.
        pcs_counter = 1
        while not master_pcs:
            # For some reason there is no master. We will wait for 30 seconds
            # and try again.
            print "The 'pcs status' returned no master."
            print "Sleeping 30 seconds..."
            time.sleep(30)
            print "done." 
            master_pcs = read_pcs(master_cfg, debug=False)
            # We wait for (1 + 4 + 1) * 30 seconds before aborting. There will
            # be a first wait before the loop, and another one after waiting
            # for 4 times, since the 'while' checks for greater than 4.
            if pcs_counter > 5:
                # send notification...
                notif_no_pcs_master(master_cfg, 'marcelomgarcia')
                # and abort script.
                sys.exit(STATE_CRITICAL)
            else:
                pcs_counter = pcs_counter + 1

        print "Ops! The master has changed!!!"
        config.set(wiso_cluster, 'Master', master_pcs)
        # Update the configuration file with the new master.
        fout = open(WISO_CONFIG, 'w')
        config.write(fout)
        fout.close()
        print "Wiso {0} master updated!".format(wiso_cluster)
        # Send notification
        notif_master_change(master_cfg, master_pcs, 'dwdos@mysite.com')
        sys.exit(STATE_WARNING)
    else:
        print "Masters OK."
        sys.exit(STATE_OK)

    # 
    # The End.
    # Have a nice day.
    # 
