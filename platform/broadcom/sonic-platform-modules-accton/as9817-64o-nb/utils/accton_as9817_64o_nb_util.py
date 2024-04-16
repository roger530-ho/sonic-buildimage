#!/usr/bin/env python3
#
# Copyright (C) 2016 Accton Networks, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
usage: accton_as9817_64o_nb_util.py [-h] [-d] [-f] {install,clean,threshold} ...

AS9817-64O-NB Platform Utility

optional arguments:
  -h, --help            show this help message and exit
  -d, --debug           run with debug mode
  -f, --force           ignore error during installation or clean

Utility Command:
  {install,clean,threshold}
    install             : install drivers and generate related sysfs nodes
    clean               : uninstall drivers and remove related sysfs nodes
    threshold           : modify thermal threshold
"""
import subprocess
import sys
import logging
import re
import time
import os
import glob
import argparse
from sonic_py_common.general import getstatusoutput_noshell


PROJECT_NAME = 'as9817_64o_nb'
version = '0.1.0'
verbose = False
DEBUG = False
FAN_PWM = 67
args = []
FORCE = 0
#logging.basicConfig(filename= PROJECT_NAME+'.log', filemode='w',level=logging.DEBUG)
#logging.basicConfig(level=logging.INFO)


if DEBUG == True:
    print(sys.argv[0])
    print('ARGV      :', sys.argv[1:])


def main():
    global DEBUG
    global args
    global FORCE
    global THRESHOLD_RANGE_LOW, THRESHOLD_RANGE_HIGH

    util_parser = argparse.ArgumentParser(description="AS9817-64O-NB Platform Utility")
    util_parser.add_argument("-d", "--debug", dest='debug', action='store_true', default=False,
                             help="run with debug mode")
    util_parser.add_argument("-f", "--force", dest='force', action='store_true', default=False,
                             help="ignore error during installation or clean")
    subcommand = util_parser.add_subparsers(dest='cmd', title='Utility Command', required=True)
    subcommand.add_parser('install', help=': install drivers and generate related sysfs nodes')
    subcommand.add_parser('clean', help=': uninstall drivers and remove related sysfs nodes')
    threshold_parser = subcommand.add_parser('threshold', help=': modify thermal threshold')
    threshold_parser.add_argument("-l", dest='list', action='store_true', default=False,
                                  help="list avaliable thermal")
    threshold_parser.add_argument("-t", dest='thermal', type=str, metavar='THERMAL_NAME',
                                  help="thermal name, ex: -t 'Temp sensor 1'")
    threshold_parser.add_argument("-ht", dest='high_threshold', type=restricted_float,
                                  metavar='THRESHOLD_VALUE',
                                  help="high threshold: %.1f ~ %.1f" % (THRESHOLD_RANGE_LOW, THRESHOLD_RANGE_HIGH))
    threshold_parser.add_argument("-hct", dest='high_crit_threshold', type=restricted_float,
                                  metavar='THRESHOLD_VALUE',
                                  help="high critical threshold : %.1f ~ %.1f" % (THRESHOLD_RANGE_LOW, THRESHOLD_RANGE_HIGH))
    args = util_parser.parse_args()

    if DEBUG == True:
        print(args)
        print(len(sys.argv))

    DEBUG = args.debug
    FORCE = 1 if args.force else 0

    if args.cmd == 'install':
        do_install()
    elif args.cmd == 'clean':
        do_uninstall()
    elif args.cmd == 'threshold':
        do_threshold()

    return 0

def show_help():
    print(__doc__ % {'scriptName' : sys.argv[0].split("/")[-1]})
    sys.exit(0)

def my_log(txt):
    if DEBUG == True:
        print("[DEBUG]"+txt)
    return

def log_os_system(cmd, show):
    logging.info('Run :'+cmd)
    status, output = subprocess.getstatusoutput(cmd)
    #status, output = getstatusoutput_noshell(cmd)
    my_log (cmd +"with result:" + str(status))
    my_log ("      output:"+output)
    if status:
        logging.info('Failed :'+cmd)
        if show:
            print('Failed :'+cmd)
    return  status, output

def driver_check():
    ret, lsmod = log_os_system("ls /sys/module/*accton*", 0)
    logging.info('mods:'+lsmod)
    if ret :
        return False
    else :
        return True

kos = [
    'modprobe i2c_dev',
    'modprobe i2c_i801',
    'modprobe i2c_ismt',
    'modprobe optoe',
    'modprobe at24',
    'modprobe i2c-ocores',
    'modprobe accton_as9817_64_fpga',
    'modprobe accton_as9817_64_mux',
    'modprobe accton_as9817_64_cpld',
    'modprobe accton_as9817_64_fan',
    'modprobe accton_as9817_64_led',
    'modprobe accton_as9817_64_psu'
]

def driver_install():
    global FORCE

    # Load 10G ethernet driver
    status, output = log_os_system("modprobe ice", 1)
    if status:
        if FORCE == 0:
            return status

    status, output = log_os_system("depmod -ae", 1)
    for i in range(0,len(kos)):
        status, output = log_os_system(kos[i], 1)
        if status:
            if FORCE == 0:
                return status
    print("Done driver_install")

    return 0

def driver_uninstall():
    global FORCE

    for i in range(0,len(kos)):
        rm = kos[-(i+1)].replace("modprobe", "modprobe -rq")
        rm = rm.replace("insmod", "rmmod")
        lst = rm.split(" ")
        if len(lst) > 3:
            del(lst[3])
        rm = " ".join(lst)
        status, output = log_os_system(rm, 1)
        if status:
            if FORCE == 0:
                return status
    return 0

i2c_prefix = '/sys/bus/i2c/devices/'

sfp_map =  [
     2, 3, 4, 5, 6, 7, 8, 9,10,11,12,13,14,15,16,17,
    18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,
    34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,
    50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,
    66,67
]

osfp_start = 0
osfp_end   = 63

mknod =[
    # Select FPGA I2C relay channel(0x78) to CPU
    'echo as9817_64_mux 0x78 > /sys/bus/i2c/devices/i2c-0/new_device',
    # Select FPGA I2C relay channel(0x70) to CPU
    'echo as9817_64_mux 0x70 > /sys/bus/i2c/devices/i2c-0/new_device',
    # Select FAN CPLD I2C relay channel(0x76) to CPU
    'echo as9817_64_mux 0x76 > /sys/bus/i2c/devices/i2c-76/new_device',

    'echo as9817_64_fpga_i2c 0x60 > /sys/bus/i2c/devices/i2c-0/new_device',
    'echo 24c02 0x56 > /sys/bus/i2c/devices/i2c-68/new_device',
    'echo as9817_64_cpld2 0x62 > /sys/bus/i2c/devices/i2c-74/new_device',
    'echo as9817_64_cpld3 0x63 > /sys/bus/i2c/devices/i2c-74/new_device',

    'echo as9817_64_fan 0x33 > /sys/bus/i2c/devices/i2c-76/new_device',
    'echo ps_2302_6l 0x58 > /sys/bus/i2c/devices/i2c-77/new_device',
    'echo ps_2302_6l 0x59 > /sys/bus/i2c/devices/i2c-77/new_device',
    'echo lm75 0x48 > /sys/bus/i2c/devices/i2c-78/new_device',
    'echo lm75 0x49 > /sys/bus/i2c/devices/i2c-79/new_device',
    'echo lm75 0x4a > /sys/bus/i2c/devices/i2c-78/new_device',
    'echo lm75 0x4b > /sys/bus/i2c/devices/i2c-78/new_device',
    'echo lm75 0x4c > /sys/bus/i2c/devices/i2c-78/new_device',
    'echo lm75 0x4d > /sys/bus/i2c/devices/i2c-79/new_device',
    # FAN Board lm75
    'echo lm75 0x4d > /sys/bus/i2c/devices/i2c-84/new_device',
    'echo lm75 0x4e > /sys/bus/i2c/devices/i2c-85/new_device',
]

mkfile = [
    '/tmp/device_threshold.json',
    '/tmp/device_threshold.json.lock'
]

def device_install():
    global FORCE

    status, output =log_os_system("i2cset -f -y 0 0x60 0x0f 0x03", 1)
    if status:
        print(output)
        if FORCE == 0:
            return status

    for i in range(0,len(mknod)):
        #for pca954x need times to built new i2c buses
        if mknod[i].find('as9817_64_mux') != -1:
           time.sleep(1)

        status, output = log_os_system(mknod[i], 1)
        if status:
            print(output)
            if FORCE == 0:
                return status

    for i in range(0,len(sfp_map)):
        if i > osfp_end:
            status, output =log_os_system("echo optoe2 0x50 > /sys/bus/i2c/devices/i2c-"+str(sfp_map[i])+"/new_device", 1)
        else:
            status, output =log_os_system("echo optoe3 0x50 > /sys/bus/i2c/devices/i2c-"+str(sfp_map[i])+"/new_device", 1)
        if status:
            print(output)
            if FORCE == 0:
                return status

    # Release RESET pin for all QSFP-DD.
    for i in range(0, (osfp_end + 1)):
        status, output = log_os_system("echo 0 > /sys/devices/platform/as9817_64_fpga/module_reset_{}".format(i + 1), 1)
        if status:
            print(output)

    # Disable Low Power Mode for all QSFP-DD.
    for i in range(0, (osfp_end + 1)):
        status, output = log_os_system("echo 0 > /sys/devices/platform/as9817_64_fpga/module_lp_mode_{}".format(i + 1), 1)
        if status:
            print(output)

    # Prevent permission issues between root or admin users for sonic_platform/helper.py
    for i in range(0,len(mkfile)):
        try:
            # Create empty file
            open(mkfile[i], 'a').close()
            log_os_system("chmod 666 {}".format(mkfile[i]), 1)
        except OSError:
            print('Failed : creating the file %s.' % (mkfile[i]))
            log_os_system("chmod 666 {}".format(mkfile[i]), 1)
            if FORCE == 0:
                return -1

    print("Done device_install")
    return

def device_uninstall():
    global FORCE

    for i in range(0,len(sfp_map)):
        target = "/sys/bus/i2c/devices/i2c-"+str(sfp_map[i])+"/delete_device"
        status, output =log_os_system("echo 0x50 > "+ target, 1)
        if status:
            print(output)
            if FORCE == 0:
                return status

    for i in range(len(mknod)):
        target = mknod[-(i+1)]
        temp = target.split()
        del temp[1]
        temp[-1] = temp[-1].replace('new_device', 'delete_device')
        status, output = log_os_system(" ".join(temp), 1)
        if status:
            print(output)
            if FORCE == 0:
                return status

    for i in range(0,len(mkfile)):
        status, output = log_os_system('rm -f ' + mkfile[i], 1)
        if status:
            print(output)
            if FORCE == 0:
                return status

    return

def system_ready():
    if driver_check() == False:
        return False
    if not device_exist():
        return False
    return True

PLATFORM_ROOT_PATH = '/usr/share/sonic/device'
PLATFORM_API2_WHL_FILE_PY3 ='sonic_platform-1.0-py3-none-any.whl'
def do_sonic_platform_install():
    device_path = "{}{}{}{}".format(PLATFORM_ROOT_PATH, '/x86_64-accton_', PROJECT_NAME, '-r0')
    SONIC_PLATFORM_BSP_WHL_PKG_PY3 = "/".join([device_path, PLATFORM_API2_WHL_FILE_PY3])

    #Check API2.0 on py whl file
    status, output = log_os_system("pip3 show sonic-platform > /dev/null 2>&1", 0)
    if status:
        if os.path.exists(SONIC_PLATFORM_BSP_WHL_PKG_PY3):
            status, output = log_os_system("pip3 install "+ SONIC_PLATFORM_BSP_WHL_PKG_PY3, 1)
            if status:
                print("Error: Failed to install {}".format(PLATFORM_API2_WHL_FILE_PY3))
                return status
            else:
                print("Successfully installed {} package".format(PLATFORM_API2_WHL_FILE_PY3))
        else:
            print('{} is not found'.format(PLATFORM_API2_WHL_FILE_PY3))
    else:
        print('{} has installed'.format(PLATFORM_API2_WHL_FILE_PY3))

    return

def do_sonic_platform_clean():
    status, output = log_os_system("pip3 show sonic-platform > /dev/null 2>&1", 0)
    if status:
        print('{} does not install, not need to uninstall'.format(PLATFORM_API2_WHL_FILE_PY3))

    else:
        status, output = log_os_system("pip3 uninstall sonic-platform -y", 0)
        if status:
            print('Error: Failed to uninstall {}'.format(PLATFORM_API2_WHL_FILE_PY3))
            return status
        else:
            print('{} is uninstalled'.format(PLATFORM_API2_WHL_FILE_PY3))

    return

def do_install():
    print("Checking system....")
    if driver_check() == False:
        print("No driver, installing....")
        status = driver_install()
        if status:
            if FORCE == 0:
                return  status
    else:
        print(PROJECT_NAME.upper()+" drivers detected....")

    if not device_exist():
        print("No device, installing....")
        status = device_install()
        if status:
            if FORCE == 0:
                return  status
    else:
        print(PROJECT_NAME.upper()+" devices detected....")

    # Turn off LOC LED if needed
    log_os_system("echo 0 > /sys/class/leds/as9817_64_led::loc/brightness", 1)
    # Turn off ALARM LED if needed
    log_os_system("echo 0 > /sys/class/leds/as9817_64_led::alarm/brightness", 1)

    do_sonic_platform_install()

    return

def do_uninstall():
    print("Checking system....")
    if not device_exist():
        print(PROJECT_NAME.upper() +" has no device installed....")
    else:
        print("Removing device....")
        status = device_uninstall()
        if status:
            if FORCE == 0:
                return  status

    if driver_check()== False :
        print(PROJECT_NAME.upper() +" has no driver installed....")
    else:
        print("Removing installed driver....")
        status = driver_uninstall()
        if status:
            if FORCE == 0:
                return  status

    do_sonic_platform_clean()

    return

def device_exist():
    ret1, log = log_os_system("ls "+i2c_prefix+"*0070", 0)
    ret2, log = log_os_system("ls "+i2c_prefix+"i2c-2", 0)
    return not(ret1 or ret2)

THRESHOLD_RANGE_LOW = 30.0
THRESHOLD_RANGE_HIGH = 110.0
# Code to initialize chassis object
init_chassis_code = \
    "import sonic_platform.platform\n"\
    "platform = sonic_platform.platform.Platform()\n"\
    "chassis = platform.get_chassis()\n\n"

# Looking for thermal
looking_for_thermal_code = \
    "thermal = None\n"\
    "all_thermals = chassis.get_all_thermals()\n"\
    "for psu in chassis.get_all_psus():\n"\
    "    all_thermals += psu.get_all_thermals()\n"\
    "for tmp in all_thermals:\n"\
    "    if '{}' == tmp.get_name():\n"\
    "        thermal = tmp\n"\
    "        break\n"\
    "if thermal == None:\n"\
    "    print('{} not found!')\n"\
    "    exit(1)\n\n"

def avaliable_thermals():
    global init_chassis_code

    get_all_thermal_name_code = \
        "thermal_list = []\n"\
        "all_thermals = chassis.get_all_thermals()\n"\
        "for psu in chassis.get_all_psus():\n"\
        "    all_thermals += psu.get_all_thermals()\n"\
        "for tmp in all_thermals:\n"\
        "    thermal_list.append(tmp.get_name())\n"\
        "print(str(thermal_list)[1:-1])\n"

    all_code = "{}{}".format(init_chassis_code, get_all_thermal_name_code)

    status, output = getstatusoutput_noshell(["docker", "exec", "pmon", "python3", "-c", all_code])
    if status != 0:
        return ""
    return output

def restricted_float(x):
    global THRESHOLD_RANGE_LOW, THRESHOLD_RANGE_HIGH

    try:
        x = float(x)
    except ValueError:
        raise argparse.ArgumentTypeError("%r not a floating-point literal" % (x,))

    if x < THRESHOLD_RANGE_LOW or x > THRESHOLD_RANGE_HIGH:
        raise argparse.ArgumentTypeError("%r not in range [%.1f ~ %.1f]" % 
                                         (x, THRESHOLD_RANGE_LOW, THRESHOLD_RANGE_HIGH))

    return x

def get_high_threshold(name):
    global init_chassis_code, looking_for_thermal_code

    get_high_threshold_code = \
        "try:\n"\
        "    print(thermal.get_high_threshold())\n"\
        "    exit(0)\n"\
        "except NotImplementedError:\n"\
        "    print('Not implement the get_high_threshold method!')\n"\
        "    exit(1)"

    all_code = "{}{}{}".format(init_chassis_code, looking_for_thermal_code.format(name, name),
                               get_high_threshold_code)

    status, output = getstatusoutput_noshell(["docker", "exec", "pmon", "python3", "-c", all_code])
    if status == 1:
        return None

    return float(output)

def get_high_crit_threshold(name):
    global init_chassis_code, looking_for_thermal_code

    get_high_crit_threshold_code = \
        "try:\n"\
        "    print(thermal.get_high_critical_threshold())\n"\
        "    exit(0)\n"\
        "except NotImplementedError:\n"\
        "    print('Not implement the get_high_critical_threshold method!')\n"\
        "    exit(1)"

    all_code = "{}{}{}".format(init_chassis_code, looking_for_thermal_code.format(name, name),
                               get_high_crit_threshold_code)

    status, output = getstatusoutput_noshell(["docker", "exec", "pmon", "python3", "-c", all_code])
    if status == 1:
        return None

    return float(output)

def do_threshold():
    global args, init_chassis_code, looking_for_thermal_code

    if args.list:
        print("Thermals: " + avaliable_thermals())
        return

    if args.thermal is None:
        print("The following arguments are required: -t")
        return

    set_threshold_code = ""
    if args.high_threshold is not None:
        if args.high_crit_threshold is not None and \
            args.high_threshold >= args.high_crit_threshold:
           print("Invalid Threshold!(High threshold can not be more than " \
                 "or equal to high critical threshold.)")
           exit(1)

        high_crit = get_high_crit_threshold(args.thermal)
        if high_crit is not None and \
           args.high_threshold >= high_crit:
           print("Invalid Threshold!(High threshold can not be more than " \
                 "or equal to high critical threshold.)")
           exit(1)

        set_threshold_code += \
            "try:\n"\
            "    if thermal.set_high_threshold({}) is False:\n"\
            "        print('{}: set_high_threshold failure!')\n"\
            "        exit(1)\n"\
            "except NotImplementedError:\n"\
            "    print('Not implement the set_high_threshold method!')\n"\
            "print('Apply the new high threshold successfully.')\n"\
            "\n".format(args.high_threshold, args.thermal)

    if args.high_crit_threshold is not None:
        high = get_high_threshold(args.thermal)
        if high is not None and \
            args.high_crit_threshold <= high:
            print("Invalid Threshold!(High critical threshold can not " \
                  "be less than or equal to high threshold.)")
            exit(1)

        set_threshold_code += \
            "try:\n"\
            "    if thermal.set_high_critical_threshold({}) is False:\n"\
            "        print('{}: set_high_critical_threshold failure!')\n"\
            "        exit(1)\n"\
            "except NotImplementedError:\n"\
            "    print('Not implement the set_high_critical_threshold method!')\n"\
            "print('Apply the new high critical threshold successfully.')\n"\
            "\n".format(args.high_crit_threshold, args.thermal)

    if set_threshold_code == "":
        return

    all_code = "{}{}{}".format(init_chassis_code, looking_for_thermal_code.format(args.thermal, args.thermal), set_threshold_code)

    status, output = getstatusoutput_noshell(["docker", "exec", "pmon", "python3", "-c", all_code])
    print(output)

if __name__ == "__main__":
    main()
