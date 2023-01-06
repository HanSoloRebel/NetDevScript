#!/usr/bin/env/ python
#coding: utf-8

import getpass
import pexpect
import re
import sys
import time

cisco_template_transceiver_check = ['show interface ethernet {slot_num}/{port_num} | i Ethernet{slot_num}/{port_num}|admin|Description|reliability|flapped|clearing|rate|CRC | exclude fec|bits/sec',
'show lldp neighbors interface ethernet {slot_num}/{port_num} | exclude codes|DOCSIS|WLAN|displayed',
'show interface ethernet {slot_num}/{port_num} transceiver | i type|serial|id|revision|part',
'show interface ethernet {slot_num}/{port_num} transceiver details | i Lane|Rx|Tx|Fault',
'show logging logfile | include "{slot_num}/{port_num} " | i failure | i {year} | last 50',
'show interface ethernet {slot_num}/{port_num} counters errors',
'slot {slot_num} quoted "show hardware internal tah event-history front-port {port_num}"   | i Got pre 1 | i fault pre 1',
'slot {slot_num} show hardware internal tah mac hwlib show mac_errors fp-port {port_num}']

mail_addr = '' #mail_addr
file_name = 'transceiver_check_result_py_script'
event_dict = {}
result = {}
vendor = ''

def ssh_connect(ip, username, password, event):
        result[(event_dict[event]['switch'], event_dict[event]['interface'])] = []
        ssh = pexpect.spawn('ssh {username}@{ip}'.format(username=username, ip=ip))
        ssh.expect ('[Pp]assword:')
        ssh.sendline (password)
        ssh.expect('[#>]')
        ssh.sendline('show clock')
        ssh.expect('[#>]')
        promt = ssh.before
        if re.search(r'Error:', promt):
                for command in huawei_template_transceiver_check:
                        ssh.sendline (command.format(ifName = event_dict[event]['interface']))
                        if 'logbuffer' in command:
                            time.sleep(5)
                        ssh.expect('>')
                        output = ssh.before.rstrip("<{}>".format(event_dict[event]['switch'])).split('\n')
                        result[(event_dict[event]['switch'], event_dict[event]['interface'])].append(output)
        else:
                for command in cisco_template_transceiver_check:
                        ssh.sendline ('terminal length 0')
                        ssh.expect ('#')
                        if command.find('{year}') > 0:
                                ssh.sendline(command.format(year = event_dict[event]['date'][:4], slot_num = event_dict[event]['interface'][event_dict[event]['interface'].find('Ethernet')+len('ethernet'):event_dict[event]['interface'].find('/'):], port_num = event_dict[event]['interface'][event_dict[event]['interface'].find('/')+1:]))
                                ssh.expect ('#')
                                output = ssh.before.replace(' \x08', '').rstrip("{} ".format(event_dict[event]['switch'])).split('\n')
                                result[(event_dict[event]['switch'], event_dict[event]['interface'])].append(output)
                        else:
                                ssh.sendline (command.format(slot_num = event_dict[event]['interface'][event_dict[event]['interface'].find('Ethernet')+len('ethernet'):event_dict[event]['interface'].find('/'):], port_num = event_dict[event]['interface'][event_dict[event]['interface'].find('/')+1:]))
                                ssh.expect ('#')
                                output = ssh.before.replace(' \x08', '').rstrip("{} ".format(event_dict[event]['switch'])).split('\n')
                                result[(event_dict[event]['switch'], event_dict[event]['interface'])].append(output)
        ssh.close()
        return result

def result_write_to_file(result):
        with open('{file}'.format(file = file_name), 'w') as f:
                f.write('To: {mail_address}\n'.format(mail_address = mail_addr))
                f.write('Subject: Transceiver Diagnostic {im}\n'.format(im = ticket))
                f.write('\nДобрый день.\nЗафиксирован флап линка ')
                if len(event_dict.keys()) > 1:
                        f.write('{switch1} {interface1} --- {switch2} {interface2}'.format(switch1 = event_dict['event1']['switch'], interface1 = event_dict['event1']['interface'], switch2 = event_dict['event2']['switch'], interface2 = event_dict['event2']['interface']))
                else:
                        f.write('{switch1} {interface1}'.format(switch1 = event_dict['event1']['switch'], interface1 = event_dict['event1']['interface']))
                f.write('\n\n')
                f.write('\nСобрана диагностическая информация:\n\n')
                for index in result.keys():
                        f.write('#' * len(event_dict['event1']['switch']))
                        f.write('\n')
                        f.write('{:^}'.format(index[0]))
                        f.write('\n')
                        f.write('#' * len(event_dict['event1']['switch']))
                        f.write('\n\n')
                        for check in result[index]:
#                                if vendor == 'Cisco':
#                                        f.write('{}#'.format(index[0]))
                                f.write('{}#'.format(index[0]))
                                for line in check:
                                        if line.startswith(' show') or line.startswith(' slot') or line.startswith('display'):
                                                f.writelines(line)
                                        else:
#                                               f.write('\n')
                                                f.writelines(line)
                                                f.write('\n')

                f.write('С уважением,\nPy_Script')



        return None


def send_mail():
        print('Please check your e-mail!')
        mail = pexpect.spawn('/bin/bash -c "cat transceiver_check_result_py_script | msmtp {mail_address}"'.format(mail_address = mail_addr))
        mail.expect (pexpect.EOF)
        return None


sw1 = raw_input('Enter sys_log1:')
#input check
sw2 = raw_input('Enter sys_log2:')
#input check
user = raw_input('user:')
pswd = getpass.getpass()
#ValueErrore
ticket = raw_input('IM:')
#default value


if len(sw1) != 0:
        if sw1.find('ETHPORT') > 0:
                event_dict['event1'] = {'date': sw1.split()[0], 'time': sw1.split()[1].strip(':'), 'switch': sw1.split()[2].strip(':'), 'alarm': sw1.split()[3].strip('%:'), 'interface': sw1.split()[5], 'description': sw1.split()[6].lstrip('(description:---').rstrip(')')}
        elif sw1.find('BFD') > 0:
                event_dict['event1'] = {'date': sw1.split()[0], 'time': sw1.split()[1].strip(':'), 'switch': sw1.split()[2].strip(':'), 'alarm': sw1.split()[3].strip('%:'), 'interface': sw1.split()[12].replace('Eth', 'Ethernet'), 'description': sw1.split()[-1].lstrip('(description:---').rstrip(')')}
        elif sw1.find('OSPF') > 0:
                event_dict['event1'] = {'date': sw1.split()[0], 'time': sw1.split()[1].strip(':'), 'switch': sw1.split()[2].strip(':'), 'alarm': sw1.split()[3].strip('%:'), 'interface': sw1.split()[9], 'description': sw1.split()[-1].lstrip('(description:---').rstrip(')')}
        elif sw1.find('Zabbix') > 0:
                alarm = sw1.split()[9] + ' ' + sw1.split()[10] + ' ' + sw1.split()[11] + ' ' + sw1.split()[12] + ' ' + sw1.split()[14] + ' ' + sw1.split()[15] + ' ' + sw1.split()[16]
                event_dict['event1'] = {'date': sw1.split()[0], 'time': sw1.split()[1].strip(':'), 'switch': sw1.split()[4], 'alarm': alarm, 'interface': sw1.split()[13], 'description': 'None'}

if len(sw2) != 0:
        if sw2.find('ETHPORT') > 0:
                event_dict['event2'] = {'date': sw2.split()[0], 'time': sw2.split()[1].strip(':'), 'switch': sw2.split()[2].strip(':'), 'alarm': sw2.split()[3].strip('%:'), 'interface': sw2.split()[5], 'description': sw2.split()[6].lstrip('(description:---').rstrip(')')}
        elif sw2.find('BFD') > 0:
                event_dict['event2'] = {'date': sw2.split()[0], 'time': sw2.split()[1].strip(':'), 'switch': sw2.split()[2].strip(':'), 'alarm': sw2.split()[3].strip('%:'), 'interface': sw2.split()[12].replace('Eth', 'Ethernet'), 'description': sw2.split()[-1].lstrip('(description:---').rstrip(')')}
        elif sw2.find('OSPF') > 0:
                event_dict['event2'] = {'date': sw2.split()[0], 'time': sw2.split()[1].strip(':'), 'switch': sw2.split()[2].strip(':'), 'alarm': sw2.split()[3].strip('%:'), 'interface': sw2.split()[9], 'description': sw2.split()[-1].lstrip('(description:---').rstrip(')')}
        elif sw2.find('Zabbix') > 0:
                alarm = sw2.split()[9] + ' ' + sw2.split()[10] + ' ' + sw2.split()[11] + ' ' + sw2.split()[12] + ' ' + sw2.split()[14] + ' ' + sw2.split()[15] + ' ' + sw2.split()[16]
                event_dict['event2'] = {'date': sw2.split()[0], 'time': sw2.split()[1].strip(':'), 'switch': sw2.split()[4], 'alarm': alarm, 'interface': sw2.split()[13], 'description': 'None'}


print('Diagnostic check in progress...')
for event in event_dict:
        ssh_connect(ip = event_dict[event]['switch'], username = user, password = pswd, event = event)
result_write_to_file(result)
send_mail()
pexpect.spawn('rm transceiver_check_result_py_script')
