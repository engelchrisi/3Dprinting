# Cura PostProcessingPlugin
# Author:   Christof Engel
# Date:     Apr. 09 2021
#
# Installation
# copy this python script into the folder
# %appData%\cura\4.8\scripts
#
# Cura:
# Put the following place holder into the printer Start-Gcode in CURA
# %BEDLEVELLING%
#
# This will be replaced with:
# G28 ;Home
# ; to avoid https://all3dp.com/2/3d-printer-heat-creep/
# M106 ; with no speed sets the fan to full speed.
# G29 ; Auto bed-level (BL-Touch)
# M109 S225

import datetime
import re

from ..Script import Script


class OptimizeBedLevelling(Script):

    def __init__(self):
        super().__init__()

    def getSettingDataString(self):
        return """{
            "name":"Optimize Bed Levelling",
            "key":"OptimizeG29",
            "metadata": {},
            "version": 2,
            "settings":
            {
                "TurnOn":
                {
                    "label": "Enabled",
                    "description": "When enabled, heating of nozzle will be done while bed levelling",
                    "type": "bool",
                    "default_value": true
                },
                "ForceLevelling":
                {
                    "label": "Force Levelling",
                    "description": "Execute the levelling of the bed otherwise use historic data",
                    "type": "bool",
                    "default_value": false
                }            }
        }"""

    def execute(self, data: list):
        if not self.getSettingValueByKey("TurnOn"):
            return data

        code = ("M117 Homing\n"
                "G28\n"
                "{}\n"
                "M117 Wait for bed temp\n"
                "{}\n"
                "; Use fan to avoid https://all3dp.com/2/3d-printer-heat-creep/\n"
                "M106 ; full speed fan\n"
                "M117 Wait for hotend temp\n"
                "{}")

        G29_code = ("M117 bed levelling \n"
                    "G29 ; Auto bed-level (BL-Touch)")

        # CR-10 V2 persists the bed levelling after G29
        # You can easily test this by switch off/on the printer and executing the M420 S1 V and compare the mesh
        # to the previous run of bed visualizer
        M420_code = ("M420 S1 V ; enable leveling and report the current mesh")

        hotend_wait_cmd = ""
        bed_wait_cmd = ""
        stopIteration = False

        for layer_index, layer in enumerate(data):
            lines = layer.split("\n")
            for line in lines:
                line_index = lines.index(line)
                if line.startswith("M104 "):  # M104 S225 ;set hotend temp
                    hotend_wait_cmd += line + "\n"
                    hotend_wait_cmd += "M105\n"
                    # comment out
                    lines[line_index] = ";" + line + " => delayed"
                elif line.startswith("M109 "):  # M109 S225 => wait for hotend temp
                    hotend_wait_cmd += line
                    # comment out
                    lines[line_index] = ";" + line + " => delayed"
                elif line.startswith("M190 "):  # M190 S75 => wait for bed temp
                    bed_wait_cmd = line
                    # comment out
                    if self.getSettingValueByKey("ForceLevelling"):
                        lines[line_index] = "M117 Waiting for bed temp\n" + \
                            bed_wait_cmd
                    else:
                        lines[line_index] = ";" + line + " => delayed"
                elif line.find("%BEDLEVELLING%") >= 0:
                    # And now insert that into the GCODE
                    if self.getSettingValueByKey("ForceLevelling"):
                        lines[line_index] = code.format(
                            G29_code, bed_wait_cmd, hotend_wait_cmd)
                    else:
                        lines[line_index] = code.format(
                            M420_code, bed_wait_cmd, hotend_wait_cmd)
                    stopIteration = True
                    break

            final_lines = "\n".join(lines)
            data[layer_index] = final_lines
            if (stopIteration):
                break

        return data
