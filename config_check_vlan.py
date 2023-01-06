#!/usr/bin/python3
#coding: utf-8

import os
import pymysql
import re
import sys

path_to_cfg = '' #path_to_cfg_dir
vendors = ['Cisco', 'Huawei'] #there are two folders in target dir
path_to_db_cfg = '' #path_to_bd_cfg_file (maria_db)
cfg_vlans = []
db_vlans_dict = {}
index = []
debug_mode = 0

sql_select = "SELECT * FROM vlan"
sql_delete = "DELETE FROM vlan WHERE id=%s"
sql_insert = "INSERT INTO vlan (hostname, ifname, vlan) VALUES (%s, %s, %s)"

with open(path_to_db_cfg, 'r') as file:
    db_cfg = file.read()
    db_cfg = [x.strip().lstrip('$').rstrip(';') for x in db_cfg.split('\n')]
    host = db_cfg[2].split('=')[-1].strip("'")
    database = db_cfg[3].split('=')[-1].strip("'")
    user = db_cfg[4].split('=')[-1].strip("'")
    password = db_cfg[5].split('=')[-1].strip("'")

conn = pymysql.connect(
    user = user,
    password = password,
    host = host,
    database = database)

def get_db():
    if debug_mode:
        print('Downloading DataBase...')
    else:
        pass
    with conn:
        cur = conn.cursor()
        cur.execute(sql_select)
        db_vlans = cur.fetchall()
        return db_vlans

def get_vlans_cisco(switch, path):
    with open(f'{path}/{switch}', 'r') as file:
        switch = switch.rstrip('.cfg')
        vlans_in_cfg = []
        created_vlans = []
        config = file.read()
        if config[:2] == '!\n':
            config = config.split('!\n')
        else:
            config = config.split('\n\n')
        for lines in config:
#            if re.findall(r'^vlan\s*\d{1,4}.*', lines):
            lines = lines.strip()
            if re.search(r'\nvlan\s\d{1,4}.*', lines) or re.search(r'^vlan\s\d{1,4}.*', lines):
#                exist_vlans = re.findall(r'^vlan.*\d{1,4}.*', lines)
                exist_vlans = [re.search(r'\d{1,4}.*', x).group() for x in re.findall(r'^vlan\s\d{1,4}.*', lines)]
                exist_vlans2 = [re.search(r'\d{1,4}.*', x).group() for x in re.findall(r'\nvlan\s\d{1,4}.*', lines)]
                exist_vlans.extend(exist_vlans2)
                for vlans in exist_vlans:
                    if re.search(r',', vlans):
                        vlans = [x for x in vlans.split(',')]
                    else:
                        vlans = [x for x in vlans.split()]
                    for vlan in vlans:
                        if re.search(r'\d{1,4}.*-\d{1,4}.*', vlan):
                            for v in range(int(vlan.split('-')[0]), int(vlan.split('-')[-1]) + 1):
                                if v not in created_vlans:
                                    created_vlans.append(v)
                        elif re.search(r'\d{1,4}.*,\d{1,4}.*', vlan):
                            vlan = vlan.split(',')
                            for v in vlan:
                                if v not in created_vlans:
                                    created_vlans.append(v)
                        elif re.search(r'\d{1,4}.*to.*\d{1,4}.*', vlan):
                            for v in range(int(vlan.split('to')[0]), int(vlan.split('to')[-1]) + 1):
                                if v not in created_vlans:
                                    created_vlans.append(v)
                        else:
                            if vlan.isdigit(): 
                                if int(vlan) not in created_vlans:
                                    created_vlans.append(int(vlan))
#            if re.search(r'^interface\s(.*\n.*)*switchport', lines):
            if re.search(r'interface', lines) and re.search(r'switchport', lines):
#                interface = re.search(r'[^(interface\s)].*', lines).group()
                interface = re.search(r'[^(interface)].*', lines).group().strip()
                vlans_on_interface = []
                section = lines.split('\n')
                trunk_mode = 0
                allowed_all = 0
                for line in section:
                    if re.search(r'switchport trunk native vlan.*\d{1,4}', line):
                        pass
                    if re.search(r'switchport access vlan \d{1,4}', line) and trunk_mode == 0:
                        if re.search(r'\d{1,4}', line):
                            vlan = re.search(r'\d{1,4}', line).group()
                            if int(vlan) not in vlans_on_interface:
                                vlans_on_interface.append(int(vlan))
                    if re.search(r'switchport mode trunk', line):
                        trunk_mode = 1
                    if re.search(r'switchport trunk allowed vlan all', line):
                        allowed_all = 1
                    if re.search(r'switchport trunk allowed (vlan|vlan add)\s?\d{1,4}.*', line) and 'dot1p' not in line:
                        findall_vlans_on_interface = re.search(r'switchport trunk allowed (vlan|vlan add)\s?\d{1,4}.*', line).group()
                        findall_vlans_on_interface = re.search(r'\d{1,4}.*', findall_vlans_on_interface).group()
                        if re.search(r',', findall_vlans_on_interface):
                            vlans = findall_vlans_on_interface.split(',')
                        else:
                            vlans = findall_vlans_on_interface.split()
                        for vlan in vlans:
                            if re.search(r'\d{1,4}.*-\d{1,4}.*', vlan):
                                for v in range(int(vlan.split('-')[0]), int(vlan.split('-')[-1]) + 1):
                                    if v not in vlans_on_interface:
                                        vlans_on_interface.append(v)
                            elif re.search(r'\d{1,4}.*,\d{1,4}.*', vlan):
                                vlan = vlan.split(',')
                                for v in vlan:
                                    if v not in vlans_on_interface:
                                        vlans_on_interface.append(v)
                            elif re.search(r'\d{1,4}.*to.*\d{1,4}.*', vlan):
                                for v in range(int(vlan.split('to')[0]), int(vlan.split('to')[-1]) + 1):
                                    if v not in vlans_on_interface:
                                        vlans_on_interface.append(v)
                            else:
                                if vlan.isdigit():
                                    if int(vlan) not in vlans_on_interface:
                                        vlans_on_interface.append(int(vlan))
                    if re.search(r'switchport trunk allowed vlan (except|remove) \d{1,4}.*', line):
                        removed_vlans = re.search(r'vlan (except|remove) \d{1,4}.*', line).group()
                        removed_vlans = re.search(r'\d{1,4}.*', removed_vlans).group()
                        if re.search(r',', removed_vlans):
                            removed_vlans = removed_vlans.split(',')
                        else:
                            removed_vlans = removed_vlans.split()
                        for vlan in removed_vlans:
                            if re.search(r'\d{1,4}.*-\d{1,4}.*', vlan):
                                for v in range(int(vlan.split('-')[0]), int(vlan.split('-')[-1]) + 1):
                                    if v in vlans_on_interface:
                                        vlans_on_interface.remove(v)
                            elif re.search(r'\d{1,4}.*,\d{1,4}.*', vlan):
                                vlan = vlan.split(',')
                                for v in vlan:
                                    if v in vlans_on_interface:
                                        vlans_on_interface.remove(v)
                            elif re.search(r'\d{1,4}.*to.*\d{1,4}.*', vlan):
                                for v in range(int(vlan.split('to')[0]), int(vlan.split('to')[-1]) + 1):
                                    if v in vlans_on_interface:
                                        vlans_on_interface.remove(v)
                            else:
                                if vlan.isdigit():
                                    if int(vlan) in vlans_on_interface:
                                        vlans_on_interface.remove(int(vlan))
                if (trunk_mode and len(vlans_on_interface) == 0) or allowed_all:
                    vlans_in_cfg.append((switch, interface, 1))
                    for vlan in created_vlans:
                        vlans_in_cfg.append((switch, interface, vlan))
                else:
                    for vlan in vlans_on_interface:
                        if vlan in created_vlans:
                            vlans_in_cfg.append((switch, interface, vlan))
    if debug_mode:
        if len(vlans_in_cfg) == 0:
            print(f'There is no vlans per interface in {switch}')
    return tuple(vlans_in_cfg)


def get_vlans_huawei(switch, path):
    with open(f'{path}/{switch}', 'r') as file:
        switch = switch.rstrip('.cfg')
        vlans_in_cfg = []
        created_vlans = []
        config = file.read()
        config = config.split('#\n')
        for lines in config:
#           if re.findall(r'(^vlan\s*\d{1,4}.*)|(^vlan batch\s*\d{1,4}.*)', lines):
            if re.search(r'(^vlan \d{1,4}.*)|(^vlan batch \d{1,4}.*)', lines):
#               exist_vlans = re.findall(r'^[^(\x1b[42D )]vlan.*\d{1,4}.*', lines)
                exist_vlans = [re.search(r'\d{1,4}.*', x).group() for x in re.findall(r'^[^(\x1b[42D )]vlan \d{1,4}.*', lines)]
                exist_vlans2 = [re.search(r'\d{1,4}.*', x).group() for x in re.findall(r'^[^(\x1b[42D )]vlan batch \d{1,4}.*', lines)]
                exist_vlans.extend(exist_vlans2)
                for vlans in exist_vlans:
                    if re.search(r',', vlans):
                        vlans = [x for x in vlans.split(',')]
                    else:
                        vlans = [x for x in vlans.split()]
                    for vlan in vlans:
                        if re.search(r'\d{1,4}.*-\d{1,4}.*', vlan):
                            for v in range(int(vlan.split('-')[0]), int(vlan.split('-')[-1]) + 1):
                                if v not in created_vlans:
                                    created_vlans.append(v)
                        elif re.search(r'\d{1,4}.*,\d{1,4}.*', vlan):
                            vlan = vlan.split(',')
                            for v in vlan:
                                if v not in created_vlans:
                                    created_vlans.append(v)
                        elif re.search(r'\d{1,4}.*to.*\d{1,4}.*', vlan):
                            for v in range(int(vlan.split('to')[0]), int(vlan.split('to')[-1]) + 1):
                                if v not in created_vlans:
                                    created_vlans.append(v)
                        elif vlan == 'to':
                            for i in range(len(vlans)):
                                if vlans[i] == 'to':
                                    for v in range(int(vlans[i - 1]) + 1, int(vlans[i + 1])):
                                        if v in created_vlans:
                                            vlans_in_cfg.append((switch, interface, v))
                        else:
                            if vlan.isdigit():
                                if int(vlan) not in created_vlans:
                                    created_vlans.append(int(vlan))
#            if re.search(r'interface(?s:.*?)port link-type (trunk|access)', lines):
            if re.search(r'interface(?s:.*?)port(?s:.*?)vlan', lines):
                interface = re.search(r'[^(interface)].*', lines).group().strip()
                vlans_in_cfg.append((switch, interface, 1))
                section = lines.split('\n')
                for line in section:
                    line = line.strip()
                    if re.search(r'^.*undo', line):
                        if re.search(r'port.*vlan \d{1,4}.*', line):
                            vlans = re.search(r'vlan\s\d{1,4}.*', line).group()
                            vlans = re.search(r'\d{1,4}.*', vlans).group()
                            vlans = vlans.split()
                            for vlan in vlans:
                                if vlan == 'to':
                                    for i in range(len(vlans)):
                                        if vlans[i] == 'to':
                                            for v in range(int(vlans[i - 1]) + 1, int(vlans[i + 1])):
                                                vlans_in_cfg.remove((switch, interface, v))
                                else:
                                    vlans_in_cfg.remove((switch, interface, int(vlan)))
                        elif re.search(r'port.*vlan all', line):
                            vlans_in_cfg = []
                        elif re.search(r'port default vlan \d{1,4}.*', line):
                            vlan = re.search(r'vlan\s\d{1,4}.*', line).group()
                            vlan = re.search(r'\d{1,4}.*', vlan).group()
                            vlans_in_cfg.append((switch, interface, 1))
                            vlans_in_cfg.remove((switch, interface, int(vlan)))
                    elif re.search(r'[^(undo)]', line):
                        if re.search(r'port.*vlan \d{1,4}.*', line) and 'default' not in line:
                            vlans = re.search(r'vlan\s\d{1,4}.*', line).group()
                            vlans = re.search(r'\d{1,4}.*', vlans).group()
                            vlans = vlans.split()
                            for vlan in vlans:
                                if vlan == 'to':
                                    for i in range(len(vlans)):
                                        if vlans[i] == 'to':
                                            for v in range(int(vlans[i - 1]) + 1, int(vlans[i + 1])):
                                                if v in created_vlans:
                                                    vlans_in_cfg.append((switch, interface, v))
                                else:
                                    if vlan.isdigit():
                                        if int(vlan) in created_vlans:
                                            vlans_in_cfg.append((switch, interface, int(vlan)))
                        elif re.search(r'port default vlan \d{1,4}.*', line):
                            vlan = re.search(r'vlan\s\d{1,4}.*', line).group()
                            vlan = re.search(r'\d{1,4}.*', vlan).group()
                            vlans_in_cfg.remove((switch, interface, 1))
                            vlans_in_cfg.append((switch, interface, int(vlan)))
                        elif re.search(r'port.*vlan all', line):
                            for vlan in created_vlans:
                                vlans_in_cfg.append((switch, interface, vlan))
    if debug_mode:
        if len(vlans_in_cfg) == 0:
            print(f'There is no vlans per interface in {switch}')
    return tuple(vlans_in_cfg)


def get_cfg():
    if debug_mode:
        print(f'Parsing configs...')
    else:
        pass
    for vendor in vendors:
        for root, dirs, files in os.walk(f'{path_to_cfg}/{vendor}'):
            for _file in files:
                if re.search(r'(.cfg|.CFG)', _file):
                    if 'Cisco' in root:
                        result = get_vlans_cisco(switch = _file, path = root)
                        for i in result:
                            cfg_vlans.append(i)
                    if 'Huawei' in root:
                        result = get_vlans_huawei(switch = _file, path = root)
                        for i in result:
                            cfg_vlans.append(i)


if __name__ == "__main__":
    for param in sys.argv:
        param2=param.split('=')
        if param2[0] == 'debug_mode':
            debug_mode = param2[1]

    db_vlans = get_db()
    for i in db_vlans:
        db_vlans_dict[i[1:]] = i[0]
    db = set(db_vlans_dict.keys())
    if debug_mode:
        print(f'Download {len(db_vlans)} rows')

    get_cfg()
    cfg_vlans = set(cfg_vlans)
    
    to_delete = tuple(db - cfg_vlans)
    for i in to_delete:
        index.append(db_vlans_dict[i])
    index.sort()
    index = tuple(index)
    if debug_mode:
        print(f'{len(index)} rows to delete')

    to_update = tuple(cfg_vlans - db)
    if debug_mode:
        print(f'{len(to_update)} rows to update')
    
    with conn:
        cur = conn.cursor()
        if len(to_delete) > 0:
            if debug_mode:
                print(f'Delete in progress...')
            cur.executemany(sql_delete, index)
        if len(to_update) > 0:
            if debug_mode:
                print(f'Update in progress...')
            cur.executemany(sql_insert, to_update)
