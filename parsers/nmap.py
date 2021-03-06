#!/usr/bin/env python3
#    Copyright (C) 2017 - 2019 Alexandre Teyar

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
#    limitations under the License.

# TODO:
# * add a "Service vs Hosts" worksheet
# * decide whether to keep the file column or not

from libnmap.parser import NmapParser
from .parser import Parser

import logging
import xlsxwriter


class Nmap(Parser):
    def __init__(self, input_files, output_file):
        super(Nmap, self).__init__(input_files, output_file)

    def print_vars(self):
        logging.info("input file(s): {}".format(
            sorted([x.name for x in self._input_files])))
        logging.info("output file: {}".format(self._output_file))

    def parse(self):
        logging.info("generating worksheet 'Host vs Services'...")
        self.parse_host_services()
        logging.info("generating worksheet 'Host vs OSs'...")
        self.parse_host_oss()
        logging.info("generating worksheet 'OS vs Hosts'...")
        self.parse_os_hosts()

        try:
            self._workbook.close()
        except Exception as e:
            logging.exception("{}".format(e))

    def parse_host_services(self):
        table_data = []
        table_headers = [
            {"header": "File"},
            {"header": "Host IP"},
            {"header": "Port"},
            {"header": "Protocol"},
            {"header": "Service"},
            {"header": "State"},
            {"header": "Banner"},
            {"header": "Reason"}
        ]

        for input_file in self._input_files:
            host_services = get_host_services(input_file.name)

            for host_ip, values in sorted(host_services.items()):
                for value in values:
                    table_data.append(
                        [
                            value["file"],
                            host_ip,
                            value["port"],
                            value["protocol"],
                            value["service"],
                            value["state"],
                            value["banner"],
                            value["reason"]
                        ]
                    )

        worksheet = self._workbook.add_worksheet("Host vs Services")
        self.draw_table(worksheet, table_headers, table_data)

    def parse_host_oss(self):
        table_data = []
        table_headers = [
            {"header": "File"},
            {"header": "Host IP"},
            {"header": "Operating System"},
            {"header": "Accuracy"}
        ]

        for input_file in self._input_files:
            host_os = get_host_oss(input_file.name)

            for host_ip, value in sorted(host_os.items()):
                table_data.append(
                    [
                        value["file"],
                        host_ip,
                        value["name"],
                        value["accuracy"]
                    ]
                )

        worksheet = self._workbook.add_worksheet("Host vs OSs")
        self.draw_table(worksheet, table_headers, table_data)

    def parse_os_hosts(self):
        table_data = []
        table_headers = [
            {"header": "File"},
            {"header": "Operating System"},
            {"header": "Host IP Count"},
            {"header": "Host IP"}
        ]

        for input_file in self._input_files:
            host_os = get_os_hosts(input_file.name)

            for operating_system, value in sorted(host_os.items()):
                # unify, sort and stringify
                table_data.append(
                    [
                        ";".join(sorted(set(value["file"]))),
                        operating_system,
                        len(value["host_ip"]),
                        ";".join(sorted(
                            set(value["host_ip"]),
                            key=lambda x: tuple(map(int, x.split('.')))
                        ))
                    ]
                )

        worksheet = self._workbook.add_worksheet("OS vs Hosts")
        self.draw_table(worksheet, table_headers, table_data)


def get_host_services(file):
    results = {}

    nmap = NmapParser.parse_fromfile(file)

    for host in nmap.hosts:
        if host.is_up():
            services = []

            for port in host.get_ports():
                service = host.get_service(port[0], port[1])

                services.append(
                    {
                        "banner":   service.banner,
                        "file":     file,
                        "port":     service.port,
                        "protocol": service.protocol,
                        "reason":   service.reason,
                        "service":  service.service,
                        "state":    service.state
                    }
                )

            results[host.address] = services

    return results


def get_host_oss(file):
    results = {}

    nmap = NmapParser.parse_fromfile(file)

    for host in nmap.hosts:
        if host.is_up() and host.os_fingerprinted:
            operating_systems = host.os_match_probabilities()

            # the first match has the highest accuracy
            if operating_systems:
                results[host.address] = {
                        "file":     file,
                        "name":     operating_systems[0].name,
                        "accuracy": operating_systems[0].accuracy
                }
        else:
            logging.debug(
                "OS fingerprinting has not been performed for {}".format(
                    host.address
                )
            )

    return results


def get_os_hosts(file):
    results = {}

    nmap = NmapParser.parse_fromfile(file)

    for host in nmap.hosts:
        if host.is_up() and host.os_fingerprinted:
            operating_systems = host.os_match_probabilities()

            if operating_systems:
                # the first match has the highest accuracy
                if operating_systems[0].name in list(results.keys()):
                    results[operating_systems[0].name]["file"].extend(
                        [file]
                    )
                    results[operating_systems[0].name]["host_ip"].extend(
                        [host.address]
                    )
                else:
                    results[operating_systems[0].name] = {
                            "file":     [file],
                            "host_ip":  [host.address],
                    }
        else:
            logging.debug(
                "OS fingerprinting has not been performed for {}".format(
                    host.address
                )
            )

    return results
