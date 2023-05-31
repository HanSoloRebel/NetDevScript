#!/usr/bin/python3
#coding: utf-8

from sys import argv
import pexpect
import re
import json

ciscoTemplateTransceiverCheck = ['show interface {ifName} | exclude Load-Interval',
'show interface {ifName} transceiver details',
'show logging logfile | include {ifName} | include %ETHPORT-5-IF_DOWN | last 1']
#'show interface {ifName} counters errors']

class Device:
    def __init__(self, mgmtIP, ifName):
        self.mgmtIP = mgmtIP
        self.ifName = ifName
        self.vendor = 'unknown'
        self.output = []


def sshConnect(mgmtIP, ifName, login, password):
    result = []
    vendor = 'unknown'
    ssh = pexpect.spawn(f'ssh {login}@{mgmtIP}')
    ssh.expect ('[Pp]assword:')
    ssh.sendline (password)
    ssh.expect('[#>]')
    ssh.sendline('terminal length 0')
    ssh.expect('[#>]')
#    promt = ssh.before.decode('utf-8')
    ssh.sendline('show version')
    ssh.expect('[#>]')
    promt = ssh.before.decode('utf-8')
    if re.search(r'Cisco', promt):
        vendor = 'Cisco'
        result.append(vendor)
        for command in ciscoTemplateTransceiverCheck:
            ssh.sendline(command.format(ifName = ifName))
            ssh.expect ('#')
            output = ssh.before.decode('utf-8')
            result.append(output)
    ssh.close()
    return result

def outputParser(outputs):
    result = {device.mgmtIP: {device.ifName: {}}}
    index = 0
    regex0 = (r'\nEthernet.+ is (?P<adminState>.+)'
             r'|admin state is (?P<state>.+),'
             r'|Last link flapped (?P<lastFlapped>.+)'
             r'|Last clearing of "show interface" counters (?P<lastClearing>.+)'
             r'|Description: (?P<description>.+)'
             r'|Internet Address is (?P<ipAddress>.+)'
             r'|300 seconds input rate (?P<inputRate>.+)'
             r'|300 seconds output rate (?P<outputRate>.+)'
             r'|(?P<inputError>\d+) input error'
             r'|(?P<outputError>\d+) output error')
    regex1 = (r'type is (?P<transceiverType>.+)'
              r'|serial number is (?P<serialNumber>.+)')
    regex2 = (r'is down \((?P<lastDownReason>.+)\)')
    for output in outputs:
        if index == 0:
            index += 1
            lines = output.split('\n')
            for line in lines:
                match = re.search(regex0, line)
                if match:
                    result[device.mgmtIP][device.ifName][match.lastgroup] = match.group(match.lastgroup).strip()
        elif index == 1:
            index += 1
            txPower = [value.split()[0] for value in re.findall(r'Tx Power\s+(.+)', output)]
            result[device.mgmtIP][device.ifName]['txPower'] = txPower
            rxPower = [value.split()[0] for value in re.findall(r'Rx Power\s+(.+)', output)]
            result[device.mgmtIP][device.ifName]['rxPower'] = rxPower
            lines = output.split('\n')
            for line in lines:
                match = re.search(regex1, line)
                if match:
                    result[device.mgmtIP][device.ifName][match.lastgroup] = match.group(match.lastgroup).strip()
        elif index == 2:
            index += 1
            match = re.search(regex2, output)
            if match:
                result[device.mgmtIP][device.ifName][match.lastgroup] = match.group(match.lastgroup)
    return result
        

if __name__ == "__main__":
    scriptName, mgmtIP, ifName, login, password  = argv
    device = Device(mgmtIP, ifName)
    device.vendor, *device.output = sshConnect(device.mgmtIP, device.ifName, login, password)
    result = outputParser(device.output)
    with open('transceiverButton.json', 'w') as file:
        json.dump(result, file)
