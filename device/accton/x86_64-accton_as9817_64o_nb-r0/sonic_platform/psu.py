#############################################################################
# Edgecore
#
# Module contains an implementation of SONiC Platform Base API and
# provides the PSUs status which are available in the platform
#
#############################################################################

try:
    from sonic_platform_base.psu_base import PsuBase
    from .helper import APIHelper
except ImportError as e:
    raise ImportError(str(e) + "- required module not found")

I2C_PATH = "/sys/bus/i2c/devices/{}-00{}/"

PSU_NAME_LIST = ["PSU-1", "PSU-2"]
PSU_NUM_FAN = [1, 1]
PSU_HWMON_PATH = {
    0: "/sys/bus/i2c/devices/77-0058/hwmon/hwmon*/psu",
    1: "/sys/bus/i2c/devices/77-0059/hwmon/hwmon*/psu",
}
PSU_PWR_GOOD_PATH = {
    0: "/sys/bus/i2c/devices/0-0060/psu1_power_good",
    1: "/sys/bus/i2c/devices/0-0060/psu2_power_good",
}
PSU_PRESENT_PATH = {
    0: "/sys/bus/i2c/devices/0-0060/psu1_present",
    1: "/sys/bus/i2c/devices/0-0060/psu2_present",
}

THERMAL_COUNT_PER_PSU = 3

SYSLED_FNODE= {
    0: "/sys/class/leds/as9817_64_led::psu1/brightness",
    1: "/sys/class/leds/as9817_64_led::psu2/brightness"
}

SYSLED_MODES = {
    "0" : PsuBase.STATUS_LED_COLOR_OFF,
    "16" : PsuBase.STATUS_LED_COLOR_GREEN,
    "10" : PsuBase.STATUS_LED_COLOR_RED
}

class Psu(PsuBase):
    """Platform-specific Psu class"""

    def __init__(self, psu_index=0):
        PsuBase.__init__(self)
        self.index = psu_index
        self._api_helper = APIHelper()

        self.hwmon_path = PSU_HWMON_PATH[psu_index]
        self.power_good_path = PSU_PWR_GOOD_PATH[psu_index]
        self.present_path = PSU_PRESENT_PATH[psu_index]

        self.__initialize_fan()
        self.__initialize_thermal()

    def __initialize_fan(self):
        from sonic_platform.fan import Fan
        for fan_index in range(0, PSU_NUM_FAN[self.index]):
            fan = Fan(fan_index, is_psu_fan=True, psu_index=self.index)
            self._fan_list.append(fan)

    def __initialize_thermal(self):
        from sonic_platform.thermal import Thermal
        for thermal_id in range(0, THERMAL_COUNT_PER_PSU):
            thermal = Thermal(thermal_index=thermal_id, is_psu=True, psu_index=self.index)
            self._thermal_list.append(thermal)

    def get_voltage(self):
        """
        Retrieves current PSU voltage output
        Returns:
            A float number, the output voltage in volts,
            e.g. 12.1
        """
        if self.get_status() is not True:
            return 0.0

        val = self._api_helper.glob_read_txt_file(self.hwmon_path + "_v_out")
        if val is not None:
            return float(val)/ 1000
        else:
            return 0.0

    def get_current(self):
        """
        Retrieves present electric current supplied by PSU
        Returns:
            A float number, the electric current in amperes, e.g 15.4
        """
        if self.get_status() is not True:
            return 0.0

        val = self._api_helper.glob_read_txt_file(self.hwmon_path + "_i_out")
        if val is not None:
            return float(val)/1000
        else:
            return 0.0

    def get_power(self):
        """
        Retrieves current energy supplied by PSU
        Returns:
            A float number, the power in watts, e.g. 302.6
        """
        if self.get_status() is not True:
            return 0.0

        val = self._api_helper.glob_read_txt_file(self.hwmon_path + "_p_out")
        if val is not None:
            return float(val)/1000
        else:
            return 0.0

    def get_powergood_status(self):
        """
        Retrieves the powergood status of PSU
        Returns:
            A boolean, True if PSU has stablized its output voltages and passed all
            its internal self-tests, False if not.
        """
        return self.get_status()

    def set_status_led(self, color):
        """
        Sets the state of the PSU status LED
        Args:
            color: A string representing the color with which to set the PSU status LED
                   Note: Only support green and off
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
            return self._api_helper.write_txt_file(SYSLED_FNODE[self.index], mode)

    def get_status_led(self):
        """
        Gets the state of the PSU status LED
        Returns:
            A string, one of the predefined STATUS_LED_COLOR_* strings above
        """
        val = self._api_helper.read_txt_file(SYSLED_FNODE[self.index])
        return SYSLED_MODES[val] if val in SYSLED_MODES else "UNKNOWN"

    def get_temperature(self):
        """
        Retrieves current temperature reading from PSU
        Returns:
            A float number of current temperature in Celsius up to nearest thousandth
            of one degree Celsius, e.g. 30.125
        """
        return self._thermal_list[1].get_temperature()

    def get_temperature_high_threshold(self):
        """
        Retrieves the high threshold temperature of PSU
        Returns:
            A float number, the high threshold temperature of PSU in Celsius
            up to nearest thousandth of one degree Celsius, e.g. 30.125
        """
        return self._thermal_list[1].get_high_threshold()

    def get_voltage_high_threshold(self):
        """
        Retrieves the high threshold PSU voltage output
        Returns:
            A float number, the high threshold output voltage in volts,
            e.g. 12.1
        """
        val = self._api_helper.glob_read_txt_file(self.hwmon_path + "_v_out_max")
        if val is not None:
            return float(val)/ 1000
        else:
            return 0.0

    def get_voltage_low_threshold(self):
        """
        Retrieves the low threshold PSU voltage output
        Returns:
            A float number, the low threshold output voltage in volts,
            e.g. 12.1
        """
        return 11.83

        val = self._api_helper.glob_read_txt_file(self.hwmon_path + "_v_out_min")
        if val is not None:
            return float(val)/ 1000
        else:
            return 0.0

    def get_maximum_supplied_power(self):
        """
        Retrieves the maximum supplied power by PSU
        Returns:
            A float number, the maximum power output in Watts.
            e.g. 1200.1
        """
        val = self._api_helper.glob_read_txt_file(self.hwmon_path + "_mfr_pout_max")
        if val is not None:
            return float(val)/1000
        else:
            return 0.0

    def get_name(self):
        """
        Retrieves the name of the device
            Returns:
            string: The name of the device
        """
        return PSU_NAME_LIST[self.index]

    def get_presence(self):
        """
        Retrieves the presence of the PSU
        Returns:
            bool: True if PSU is present, False if not
        """
        val = self._api_helper.glob_read_txt_file(self.present_path)
        if val is not None:
            return int(val, 10) == 1
        else:
            return False

    def get_status(self):
        """
        Retrieves the operational status of the device
        Returns:
            A boolean value, True if device is operating properly, False if not
        """
        val = self._api_helper.glob_read_txt_file(self.power_good_path)
        if val is not None:
            return int(val, 10) == 1
        else:
            return False

    def get_model(self):
        """
        Retrieves the model number (or part number) of the device
        Returns:
            string: Model/part number of device
        """
        model = self._api_helper.glob_read_txt_file(self.hwmon_path + "_mfr_model")
        if model is None:
            return "N/A"
        return model

    def get_serial(self):
        """
        Retrieves the serial number of the device
        Returns:
            string: Serial number of device
        """
        serial = self._api_helper.glob_read_txt_file(self.hwmon_path + "_mfr_serial")
        if serial is None:
            return "N/A"
        return serial

    def get_revision(self):
        """
        Retrieves the serial number of the device
        Returns:
            string: Serial number of device
        """
        revision = self._api_helper.glob_read_txt_file(self.hwmon_path + "_mfr_revision")
        if revision is None:
            return "N/A"
        return revision

    def get_position_in_parent(self):
        """
        Retrieves 1-based relative physical position in parent device. If the agent cannot determine the parent-relative position
        for some reason, or if the associated value of entPhysicalContainedIn is '0', then the value '-1' is returned
        Returns:
            integer: The 1-based relative physical position in parent device or -1 if cannot determine the position
        """
        return self.index+1

    def is_replaceable(self):
        """
        Indicate whether this device is replaceable.
        Returns:
            bool: True if it is replaceable.
        """
        return True
