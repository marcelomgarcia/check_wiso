# Check Wiso master

Check if there is a server defined in the wiso cluster. The basic configuration is defined in a file called `wiso_master.conf`. The file is divided into sections, that can be easily read with Python `ConfigParser`. In the configuration file is specified the master of each cluster, production or test.

The script read the master node from the configuration file and try to read the current master using the command `pcs status`. If the master is still the same, the scripts will print a short message that everything is OK and finish. But the server has changed, then, first, we need to know if there is another master defined or if there is no master defined for the cluster. If the master in undefined, the script will send a notification about not having a master defined in pcs and will exit. In principle, the situation of a not defined master can only occur during a maintance where the cluster has to be shutdown for a long time, like fixing a network issue. In general the change from one master should be fast enought, the script will notify about the change, update the configuration file with the new master, and exit.

## Command line options

The user should provide which cluster he wants to test via option in the command line. If no cluster is provided, the script will print a message suggesting to use the *help* option

    [root@nagiosds wiso]# ./check_wiso_master.py
    ./check_wiso_master.py: missing Wiso cluster.
    Use '-h' or '--help' for options
    [root@nagiosds wiso]#

To get the options available, use the `--help` option

    [root@nagiosds wiso]# ./check_wiso_master.py --help
    Usage: check_wiso_master.py [options]

    Options:
    -h, --help            show this help message and exit
    -c WISO_CLUSTER, --cluster=WISO_CLUSTER
                            Wiso cluster to query, 'mst' or 'mss'
    [root@nagiosds wiso]#

There is a basic check if the cluster provided is valid or not:

    [root@nagiosds wiso]# ./check_wiso_master.py -c msx
    ./check_wiso_master.py: section MSX does not exists
    Options are MST, MSS
    [root@nagiosds wiso]#

Once a valid cluster is provided, the next step is to read the master from the configuration file.

## Configuration file

The configuration file is divided into 2 sections: _mss_ and _mst_. The production (mss) and the test (mst) clusters:

    [root@nagiosds wiso]# cat wiso_master.conf
    [MST]
    master = mst1

    [MSS]
    master = mss2

For each section, there is a master node defined. This master node will be used to query for the *pcs* master. Therefore should be a valid server, although there is explict check for that. The test is simply if *ssh* in the *paramiko* module timed out, and then we assume that the server was invalid.

### Reading the file

The script reads the configuration file using the module `ConfigParser` from Python standart library:

    import ConfigParser as cfgparser

The configuration file is define in a global variable

    WISO_CONFIG = "/maint/nagios/etc/wiso_master.conf"

We read the `config` object in the main routine and the `wiso_cluster` variable is the cluster provided by the user

        config = cfgparser.ConfigParser()
        config.read(WISO_CONFIG)
        # Read config file and return the 'master' defined.
        master_cfg = read_config(config, wiso_cluster)

And the master node is read in a function with check if the cluster provided by the user is valid

    def read_config(config, wiso_cluster):
        try:
            master = config.get(wiso_cluster, 'master')
        except cfgparser.NoSectionError:
        (...)
        return master

## Notification

The script will send notification by email in 2 circunstances:

* When the master changes, or,
* when there is no master returned by the pcs command.

## Crontab
