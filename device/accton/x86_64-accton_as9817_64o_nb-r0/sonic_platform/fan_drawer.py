########################################################################
#
# Module contains an implementation of SONiC Platform Base API and
# provides the Fan-Drawers' information available in the platform.
#
########################################################################

try:
    from sonic_platform_base.fan_drawer_base import FanDrawerBase
    from .helper import APIHelper
except ImportError as e:
    raise ImportError(str(e) + "- required module not found")

FANS_PER_FANTRAY = 2

SYSLED_FNODE= {
    0: "/sys/bus/i2c/devices/76-0033/hwmon/hwmon*/fan1_led",
    1: "/sys/bus/i2c/devices/76-0033/hwmon/hwmon*/fan2_led",
    2: "/sys/bus/i2c/devices/76-0033/hwmon/hwmon*/fan3_led",
    3: "/sys/bus/i2c/devices/76-0033/hwmon/hwmon*/fan4_led",
}

SYSLED_MODES = {
    "0" : FanDrawerBase.STATUS_LED_COLOR_OFF,
    "16" : FanDrawerBase.STATUS_LED_COLOR_GREEN,
    "10" : FanDrawerBase.STATUS_LED_COLOR_RED
}

class FanDrawer(FanDrawerBase):
    """Platform-specific Fan class"""

    def __init__(self, fantray_index):

        FanDrawerBase.__init__(self)
        # FanTray is 0-based in platforms
        self.fantrayindex = fantray_index
        self.__initialize_fan_drawer()
        self._api_helper = APIHelper()

    def __initialize_fan_drawer(self):
        from sonic_platform.fan import Fan
        for i in range(FANS_PER_FANTRAY):
            self._fan_list.append(Fan(self.fantrayindex, i))

    def get_name(self):
        """
        Retrieves the fan drawer name
        Returns:
            string: The name of the device
        """
        return "FanTray{}".format(self.fantrayindex+1)

    def set_status_led(self, color):
        """
        Sets the state of the fan drawer status LED

        Args:
            color: A string representing the color with which to set the
                   fan drawer status LED

        Returns:
            bool: True if status LED state is set successfully, False if not
        """
        mode = None
        for key, val in SYSLED_MODES.items():
            if val == color:
                mode = key
                break

        if mode is None:
            return False
        else:
            return self._api_helper.glob_write_txt_file(SYSLED_FNODE[self.fantrayindex], mode)

    def get_status_led(self):
        """
        Gets the state of the fan drawer LED

        Returns:
            A string, one of the predefined STATUS_LED_COLOR_* strings above
        """
        val = self._api_helper.glob_read_txt_file(SYSLED_FNODE[self.fantrayindex])
        return SYSLED_MODES[val] if val in SYSLED_MODES else "UNKNOWN"

    def is_replaceable(self):
        """
        Indicate whether this device is replaceable.
        Returns:
            bool: True if it is replaceable.
        """
        return True

    def get_presence(self):
        """
        Retrieves the presence of the device
        Returns:
            bool: True if device is present, False if not
        """
        return self._fan_list[0].get_presence()

    def get_model(self):
        """
        Retrieves the model number (or part number) of the device
        Returns:
            string: Model/part number of device
        """
        return self._fan_list[0].get_model()

    def get_serial(self):
        """
        Retrieves the serial number of the device
        Returns:
            string: Serial number of device
        """
        return self._fan_list[0].get_serial()

    def get_status(self):
        """
        Retrieves the operational status of the device
        Returns:
            A boolean value, True if device is operating properly, False if not
        """
        return self._fan_list[0].get_status()

    def get_position_in_parent(self):
        """
        Retrieves 1-based relative physical position in parent device.
        If the agent cannot determine the parent-relative position
        for some reason, or if the associated value of
        entPhysicalContainedIn is'0', then the value '-1' is returned
        Returns:
            integer: The 1-based relative physical position in parent device
            or -1 if cannot determine the position
        """
        return (self.fantrayindex+1)

    def is_replaceable(self):
        """
        Indicate whether this device is replaceable.
        Returns:
            bool: True if it is replaceable.
        """
        return True

