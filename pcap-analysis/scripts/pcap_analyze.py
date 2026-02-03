#!/usr/bin/env python3
"""Analyze local PCAP files without external mcpcap dependencies."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from scapy.all import (
    BOOTP,
    DHCP,
    DNS,
    ICMP,
    IP,
    TCP,
    UDP,
    IPv6,
    PcapReader,
    rdpcap,
)


SUPPORTED_EXTENSIONS = (".pcap", ".pcapng", ".cap")


@dataclass
class Config:
    max_packets: Optional[int] = None

    def validate(self) -> None:
        if self.max_packets is not None and self.max_packets <= 0:
            raise ValueError("max_packets must be a positive integer")


class BaseAnalyzer:
    def __init__(self, config: Config) -> None:
        self.config = config

    def analyze_packets(self, pcap_file: str) -> dict[str, Any]:
        return self._handle_local_analysis(pcap_file)

    def _handle_local_analysis(self, pcap_file: str) -> dict[str, Any]:
        if pcap_file.startswith(("http://", "https://")):
            return {
                "error": "HTTP URL input is not supported. Provide a local PCAP path.",
                "pcap_file": pcap_file,
            }

        if not os.path.exists(pcap_file):
            return {"error": f"PCAP file not found: {pcap_file}", "pcap_file": pcap_file}

        if not pcap_file.lower().endswith(SUPPORTED_EXTENSIONS):
            return {
                "error": (
                    f"File '{pcap_file}' is not a supported PCAP file "
                    f"{SUPPORTED_EXTENSIONS}"
                ),
                "pcap_file": pcap_file,
            }

        try:
            return self._analyze_protocol_file(pcap_file)
        except Exception as exc:
            return {
                "error": f"Failed to analyze PCAP file '{pcap_file}': {str(exc)}",
                "pcap_file": pcap_file,
            }

    def _analyze_protocol_file(self, pcap_file: str) -> dict[str, Any]:
        raise NotImplementedError


class DNSAnalyzer(BaseAnalyzer):
    def analyze_dns_packets(self, pcap_file: str) -> dict[str, Any]:
        return self.analyze_packets(pcap_file)

    def _analyze_protocol_file(self, pcap_file: str) -> dict[str, Any]:
        packets = rdpcap(pcap_file)
        dns_packets = [pkt for pkt in packets if pkt.haslayer(DNS)]

        if not dns_packets:
            return {
                "file": pcap_file,
                "total_packets": len(packets),
                "dns_packets_found": 0,
                "message": "No DNS packets found in this capture",
            }

        packets_to_analyze = dns_packets
        limited = False
        if self.config.max_packets and len(dns_packets) > self.config.max_packets:
            packets_to_analyze = dns_packets[: self.config.max_packets]
            limited = True

        packet_details = [
            self._analyze_dns_packet(pkt, i)
            for i, pkt in enumerate(packets_to_analyze, 1)
        ]

        stats = self._generate_statistics(packet_details)

        result = {
            "file": pcap_file,
            "analysis_timestamp": datetime.now().isoformat(),
            "total_packets_in_file": len(packets),
            "dns_packets_found": len(dns_packets),
            "dns_packets_analyzed": len(packet_details),
            "statistics": stats,
            "packets": packet_details,
        }
        if limited:
            result["note"] = (
                f"Analysis limited to first {self.config.max_packets} DNS packets due to --max-packets setting"
            )
        return result

    def _analyze_dns_packet(self, pkt: Any, packet_number: int) -> dict[str, Any]:
        dns_layer = pkt[DNS]

        src_ip = dst_ip = "unknown"
        if pkt.haslayer(IP):
            src_ip = pkt[IP].src
            dst_ip = pkt[IP].dst
        elif pkt.haslayer(IPv6):
            src_ip = pkt[IPv6].src
            dst_ip = pkt[IPv6].dst

        protocol = "unknown"
        if pkt.haslayer(UDP):
            protocol = "UDP"
        elif pkt.haslayer(TCP):
            protocol = "TCP"

        questions = []
        if dns_layer.qd:
            for q in dns_layer.qd:
                try:
                    name = (
                        q.qname.decode().rstrip(".")
                        if hasattr(q.qname, "decode")
                        else str(q.qname).rstrip(".")
                    )
                    questions.append(
                        {
                            "name": name,
                            "type": getattr(q, "qtype", 0),
                            "class": getattr(q, "qclass", 0),
                        }
                    )
                except (AttributeError, UnicodeDecodeError) as exc:
                    questions.append(
                        {
                            "name": f"<parsing_error: {str(exc)}>",
                            "type": getattr(q, "qtype", 0),
                            "class": getattr(q, "qclass", 0),
                        }
                    )

        answers = []
        if dns_layer.an:
            for a in dns_layer.an:
                try:
                    if hasattr(a, "rrname"):
                        if hasattr(a.rrname, "decode"):
                            name = a.rrname.decode().rstrip(".")
                        else:
                            name = str(a.rrname).rstrip(".")
                    else:
                        name = "<unknown>"

                    answer_data = {
                        "name": name,
                        "type": getattr(a, "type", 0),
                        "class": getattr(a, "rclass", 0),
                        "ttl": getattr(a, "ttl", 0),
                    }

                    if hasattr(a, "rdata"):
                        try:
                            if a.type == 1:
                                answer_data["address"] = str(a.rdata)
                            elif a.type == 28:
                                answer_data["address"] = str(a.rdata)
                            elif a.type == 5:
                                answer_data["cname"] = str(a.rdata).rstrip(".")
                            elif a.type == 15:
                                answer_data["mx"] = str(a.rdata)
                            else:
                                answer_data["data"] = str(a.rdata)
                        except Exception as rdata_error:
                            answer_data["data"] = (
                                f"<rdata_parsing_error: {str(rdata_error)}>")

                    answers.append(answer_data)
                except (AttributeError, UnicodeDecodeError) as exc:
                    answers.append(
                        {
                            "name": f"<parsing_error: {str(exc)}>",
                            "type": getattr(a, "type", 0),
                            "class": getattr(a, "rclass", 0),
                            "ttl": getattr(a, "ttl", 0),
                        }
                    )

        return {
            "packet_number": packet_number,
            "timestamp": datetime.fromtimestamp(float(pkt.time)).isoformat(),
            "src_ip": src_ip,
            "dst_ip": dst_ip,
            "protocol": protocol,
            "dns_id": getattr(dns_layer, "id", 0),
            "flags": {
                "is_response": bool(getattr(dns_layer, "qr", 0)),
                "authoritative": bool(getattr(dns_layer, "aa", 0)),
                "truncated": bool(getattr(dns_layer, "tc", 0)),
                "recursion_desired": bool(getattr(dns_layer, "rd", 0)),
                "recursion_available": bool(getattr(dns_layer, "ra", 0)),
            },
            "question_count": getattr(dns_layer, "qdcount", 0),
            "answer_count": getattr(dns_layer, "ancount", 0),
            "questions": questions,
            "answers": answers,
        }

    def _generate_statistics(self, packet_details: list[dict[str, Any]]) -> dict[str, Any]:
        query_count = sum(1 for p in packet_details if not p["flags"]["is_response"])
        response_count = sum(1 for p in packet_details if p["flags"]["is_response"])
        unique_domains = set()
        for p in packet_details:
            for q in p["questions"]:
                unique_domains.add(q["name"])

        return {
            "queries": query_count,
            "responses": response_count,
            "unique_domains_queried": len(unique_domains),
            "unique_domains": list(unique_domains),
        }


class DHCPAnalyzer(BaseAnalyzer):
    def analyze_dhcp_packets(self, pcap_file: str) -> dict[str, Any]:
        return self.analyze_packets(pcap_file)

    def _analyze_protocol_file(self, pcap_file: str) -> dict[str, Any]:
        packets = rdpcap(pcap_file)
        dhcp_packets = [pkt for pkt in packets if pkt.haslayer(BOOTP)]

        if not dhcp_packets:
            return {
                "file": pcap_file,
                "total_packets": len(packets),
                "dhcp_packets_found": 0,
                "message": "No DHCP packets found in this capture",
            }

        packets_to_analyze = dhcp_packets
        limited = False
        if self.config.max_packets and len(dhcp_packets) > self.config.max_packets:
            packets_to_analyze = dhcp_packets[: self.config.max_packets]
            limited = True

        packet_details = [
            self._analyze_dhcp_packet(pkt, i)
            for i, pkt in enumerate(packets_to_analyze, 1)
        ]

        stats = self._generate_statistics(packet_details)

        result = {
            "file": pcap_file,
            "total_packets": len(packets),
            "dhcp_packets_found": len(dhcp_packets),
            "dhcp_packets_analyzed": len(packet_details),
            "statistics": stats,
            "packets": packet_details,
        }

        if limited:
            result["note"] = (
                f"Analysis limited to first {self.config.max_packets} DHCP packets due to --max-packets setting"
            )

        return result

    def _analyze_dhcp_packet(self, packet: Any, packet_num: int) -> dict[str, Any]:
        info = {
            "packet_number": packet_num,
            "timestamp": packet.time,
        }

        if packet.haslayer(IP):
            ip_layer = packet[IP]
            info.update({"src_ip": ip_layer.src, "dst_ip": ip_layer.dst})

        if packet.haslayer(UDP):
            udp_layer = packet[UDP]
            info.update({"src_port": udp_layer.sport, "dst_port": udp_layer.dport})

        if packet.haslayer(BOOTP):
            bootp_layer = packet[BOOTP]
            info.update(
                {
                    "client_ip": str(bootp_layer.ciaddr),
                    "your_ip": str(bootp_layer.yiaddr),
                    "server_ip": str(bootp_layer.siaddr),
                    "relay_ip": str(bootp_layer.giaddr),
                    "client_mac": bootp_layer.chaddr[:6].hex(":"),
                    "transaction_id": bootp_layer.xid,
                }
            )

        if packet.haslayer(DHCP):
            dhcp_options = packet[DHCP].options
            dhcp_info: dict[str, Any] = {
                "message_type": None,
                "server_id": None,
                "hostname": None,
                "requested_ip": None,
                "lease_time": None,
                "subnet_mask": None,
                "router": None,
                "dns_servers": None,
                "domain_name": None,
            }

            for option in dhcp_options:
                if isinstance(option, tuple):
                    key, value = option
                    if key == "message-type":
                        dhcp_info["message_type"] = value
                    elif key == "server_id":
                        dhcp_info["server_id"] = value
                    elif key == "hostname":
                        dhcp_info["hostname"] = value
                    elif key == "requested_addr":
                        dhcp_info["requested_ip"] = value
                    elif key == "lease_time":
                        dhcp_info["lease_time"] = value
                    elif key == "subnet_mask":
                        dhcp_info["subnet_mask"] = value
                    elif key == "router":
                        dhcp_info["router"] = value
                    elif key == "name_server":
                        dhcp_info["dns_servers"] = value
                    elif key == "domain":
                        dhcp_info["domain_name"] = value
                    elif key == "client_id":
                        if isinstance(value, bytes):
                            dhcp_info["client_id"] = value.hex(":")
                        else:
                            dhcp_info["client_id"] = str(value)

            info.update(dhcp_info)

        return info

    def _generate_statistics(self, packet_details: list[dict[str, Any]]) -> dict[str, Any]:
        stats = {
            "unique_clients": set(),
            "unique_servers": set(),
            "message_types": {},
            "transactions": [],
        }

        for pkt in packet_details:
            if "client_mac" in pkt:
                stats["unique_clients"].add(pkt["client_mac"])
            if "server_ip" in pkt and pkt["server_ip"] != "0.0.0.0":
                stats["unique_servers"].add(pkt["server_ip"])

            message_type = pkt.get("message_type")
            if message_type:
                stats["message_types"][message_type] = (
                    stats["message_types"].get(message_type, 0) + 1
                )

            stats["transactions"].append(
                {
                    "transaction_id": pkt.get("transaction_id"),
                    "client_mac": pkt.get("client_mac"),
                    "message_type": message_type,
                    "requested_ip": pkt.get("requested_ip"),
                    "assigned_ip": pkt.get("your_ip"),
                }
            )

        return {
            "unique_clients_count": len(stats["unique_clients"]),
            "unique_servers_count": len(stats["unique_servers"]),
            "unique_clients": list(stats["unique_clients"]),
            "unique_servers": list(stats["unique_servers"]),
            "message_type_counts": stats["message_types"],
            "transaction_count": len(stats["transactions"]),
            "transactions": stats["transactions"],
        }


class ICMPAnalyzer(BaseAnalyzer):
    def analyze_icmp_packets(self, pcap_file: str) -> dict[str, Any]:
        return self.analyze_packets(pcap_file)

    def _analyze_protocol_file(self, pcap_file: str) -> dict[str, Any]:
        packets = rdpcap(pcap_file)
        icmp_packets = [pkt for pkt in packets if pkt.haslayer(ICMP)]

        if not icmp_packets:
            return {
                "file": pcap_file,
                "total_packets": len(packets),
                "icmp_packets_found": 0,
                "message": "No ICMP packets found in this capture",
            }

        packets_to_analyze = icmp_packets
        limited = False
        if self.config.max_packets and len(icmp_packets) > self.config.max_packets:
            packets_to_analyze = icmp_packets[: self.config.max_packets]
            limited = True

        packet_details = [
            self._analyze_icmp_packet(pkt, i)
            for i, pkt in enumerate(packets_to_analyze, 1)
        ]

        stats = self._generate_statistics(packet_details)

        result = {
            "file": pcap_file,
            "analysis_timestamp": datetime.now().isoformat(),
            "total_packets": len(packets),
            "icmp_packets_found": len(icmp_packets),
            "icmp_packets_analyzed": len(packet_details),
            "statistics": stats,
            "packets": packet_details,
        }

        if limited:
            result["note"] = (
                f"Analysis limited to first {self.config.max_packets} ICMP packets due to --max-packets setting"
            )

        return result

    def _analyze_icmp_packet(self, packet: Any, packet_num: int) -> dict[str, Any]:
        info = {
            "packet_number": packet_num,
            "timestamp": datetime.fromtimestamp(float(packet.time)).isoformat(),
        }

        if packet.haslayer(IP):
            ip_layer = packet[IP]
            info.update(
                {
                    "src_ip": ip_layer.src,
                    "dst_ip": ip_layer.dst,
                    "ip_version": 4,
                    "ttl": ip_layer.ttl,
                    "packet_size": len(packet),
                }
            )
        elif packet.haslayer(IPv6):
            ipv6_layer = packet[IPv6]
            info.update(
                {
                    "src_ip": ipv6_layer.src,
                    "dst_ip": ipv6_layer.dst,
                    "ip_version": 6,
                    "ttl": None,
                    "packet_size": len(packet),
                }
            )

        icmp_layer = packet[ICMP]
        info.update(
            {
                "type": icmp_layer.type,
                "code": icmp_layer.code,
                "checksum": getattr(icmp_layer, "chksum", None),
                "identifier": getattr(icmp_layer, "id", None),
                "sequence": getattr(icmp_layer, "seq", None),
                "payload_size": len(icmp_layer.payload),
            }
        )

        return info

    def _generate_statistics(self, packet_details: list[dict[str, Any]]) -> dict[str, Any]:
        stats = {
            "echo_requests": 0,
            "echo_replies": 0,
            "echo_pairs": [],
            "unreachable_destinations": set(),
        }

        request_map: dict[tuple[Any, Any, Any], dict[str, Any]] = {}

        for pkt in packet_details:
            icmp_type = pkt.get("type")
            if icmp_type == 8:
                stats["echo_requests"] += 1
                key = (pkt.get("identifier"), pkt.get("sequence"), pkt.get("src_ip"))
                request_map[key] = pkt
            elif icmp_type == 0:
                stats["echo_replies"] += 1
                key = (pkt.get("identifier"), pkt.get("sequence"), pkt.get("dst_ip"))
                req_pkt = request_map.get(key)
                if req_pkt:
                    stats["echo_pairs"].append(
                        {
                            "request": req_pkt,
                            "reply": pkt,
                        }
                    )
            elif icmp_type == 3:
                stats["unreachable_destinations"].add(pkt.get("dst_ip"))

        return {
            "echo_requests": stats["echo_requests"],
            "echo_replies": stats["echo_replies"],
            "echo_sessions": len(stats["echo_pairs"]),
            "echo_pairs": stats["echo_pairs"],
            "unreachable_destinations_count": len(stats["unreachable_destinations"]),
            "unreachable_destinations": list(stats["unreachable_destinations"]),
        }


class CapInfosAnalyzer(BaseAnalyzer):
    def analyze_capinfos(self, pcap_file: str) -> dict[str, Any]:
        return self.analyze_packets(pcap_file)

    def _analyze_protocol_file(self, pcap_file: str) -> dict[str, Any]:
        packets = rdpcap(pcap_file)
        stats = self._generate_statistics(packets)

        results = {
            "file_size_bytes": os.path.getsize(pcap_file),
            "filename": os.path.basename(pcap_file),
            "file_encapsulation": self._detect_linktype(pcap_file),
        }

        return results | stats

    def _detect_linktype(self, path: str) -> str:
        linktype_map = {
            1: "Ethernet",
            101: "Raw IP",
            105: "IEEE 802.11 Wireless LAN",
            113: "Linux cooked-mode capture v1",
            228: "Raw IPv4",
            229: "Raw IPv6",
            276: "Linux cooked-mode capture v2",
        }
        try:
            with PcapReader(path) as reader:
                linktype = getattr(reader, "linktype", None)
        except Exception:
            linktype = None

        return linktype_map.get(linktype, f"Unknown ({linktype})" if linktype else "Unknown")

    def _generate_statistics(self, packet_details: list) -> dict[str, Any]:
        if not packet_details:
            return {"error": "No packets found"}

        packet_count = len(packet_details)
        data_size = sum(len(pkt) for pkt in packet_details)
        first_time = float(packet_details[0].time)
        last_time = float(packet_details[-1].time)
        duration = max(last_time - first_time, 0.000001)
        data_byte_rate = data_size / duration if duration > 0 else 0
        data_bit_rate = (data_size * 8) / duration if duration > 0 else 0
        avg_packet_size = data_size / packet_count if packet_count > 0 else 0
        avg_packet_rate = packet_count / duration if duration > 0 else 0

        return {
            "packet_count": packet_count,
            "data_size_bytes": data_size,
            "capture_duration_seconds": duration,
            "first_packet_time": first_time,
            "last_packet_time": last_time,
            "data_rate_bytes": data_byte_rate,
            "data_rate_bits": data_bit_rate,
            "average_packet_size_bytes": avg_packet_size,
            "average_packet_rate": avg_packet_rate,
        }


class TCPAnalyzer(BaseAnalyzer):
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self._analysis_type = "connections"
        self._analysis_kwargs: dict[str, Any] = {}

    def analyze_tcp_connections(
        self,
        pcap_file: str,
        server_ip: Optional[str] = None,
        server_port: Optional[int] = None,
        detailed: bool = False,
    ) -> dict[str, Any]:
        return self._analyze_by_type(
            pcap_file,
            analysis_type="connections",
            server_ip=server_ip,
            server_port=server_port,
            detailed=detailed,
        )

    def analyze_tcp_anomalies(
        self,
        pcap_file: str,
        server_ip: Optional[str] = None,
        server_port: Optional[int] = None,
    ) -> dict[str, Any]:
        return self._analyze_by_type(
            pcap_file,
            analysis_type="anomalies",
            server_ip=server_ip,
            server_port=server_port,
        )

    def analyze_tcp_retransmissions(
        self,
        pcap_file: str,
        server_ip: Optional[str] = None,
        threshold: float = 0.02,
    ) -> dict[str, Any]:
        return self._analyze_by_type(
            pcap_file,
            analysis_type="retransmissions",
            server_ip=server_ip,
            threshold=threshold,
        )

    def analyze_tcp_traffic_flow(
        self,
        pcap_file: str,
        server_ip: str,
        server_port: Optional[int] = None,
    ) -> dict[str, Any]:
        return self._analyze_by_type(
            pcap_file,
            analysis_type="traffic_flow",
            server_ip=server_ip,
            server_port=server_port,
        )

    def _analyze_by_type(self, pcap_file: str, analysis_type: str, **kwargs: Any) -> dict[str, Any]:
        self._analysis_type = analysis_type
        self._analysis_kwargs = kwargs
        return self.analyze_packets(pcap_file)

    def _analyze_protocol_file(self, pcap_file: str) -> dict[str, Any]:
        packets = rdpcap(pcap_file)
        tcp_packets = [pkt for pkt in packets if pkt.haslayer(TCP)]

        if not tcp_packets:
            return {
                "file": pcap_file,
                "total_packets": len(packets),
                "tcp_packets_found": 0,
                "message": "No TCP packets found in this capture",
            }

        filtered_packets = self._apply_filters(
            tcp_packets,
            self._analysis_kwargs.get("server_ip"),
            self._analysis_kwargs.get("server_port"),
        )

        if self._analysis_type == "connections":
            return self._analyze_connections(pcap_file, filtered_packets, packets)
        if self._analysis_type == "anomalies":
            return self._analyze_anomalies(pcap_file, filtered_packets)
        if self._analysis_type == "retransmissions":
            return self._analyze_retrans(pcap_file, filtered_packets)
        if self._analysis_type == "traffic_flow":
            return self._analyze_flow(pcap_file, filtered_packets)

        return {"error": f"Unknown analysis type: {self._analysis_type}"}

    def _apply_filters(
        self, packets: list, server_ip: Optional[str], server_port: Optional[int]
    ) -> list:
        if not server_ip and not server_port:
            return packets

        filtered = []
        for pkt in packets:
            src_ip, dst_ip = self._extract_ips(pkt)
            tcp = pkt[TCP]

            if server_ip and src_ip != server_ip and dst_ip != server_ip:
                continue
            if server_port and tcp.sport != server_port and tcp.dport != server_port:
                continue

            filtered.append(pkt)

        return filtered

    def _analyze_connections(self, pcap_file: str, tcp_packets: list, all_packets: list) -> dict[str, Any]:
        from collections import defaultdict

        connections = defaultdict(list)
        for pkt in tcp_packets:
            conn_key = self._get_connection_key(pkt)
            connections[conn_key].append(pkt)

        connection_details = []
        successful_handshakes = 0
        failed_handshakes = 0
        reset_connections = 0
        normal_close = 0
        issues = []

        for conn_key, pkts in connections.items():
            conn_info = self._analyze_single_connection(conn_key, pkts)
            connection_details.append(conn_info)

            if conn_info["handshake_completed"]:
                successful_handshakes += 1
            else:
                failed_handshakes += 1

            if conn_info["close_reason"] == "reset":
                reset_connections += 1
            elif conn_info["close_reason"] == "normal":
                normal_close += 1

        total_rst = sum(c["rst_count"] for c in connection_details)
        total_retrans = sum(c["retransmissions"] for c in connection_details)

        if reset_connections > 0:
            issues.append(f"{reset_connections} connections terminated by RST")
        if total_retrans > 0:
            issues.append(f"{total_retrans} retransmissions detected")
        if failed_handshakes > 0:
            issues.append(f"{failed_handshakes} failed handshakes")

        return {
            "file": pcap_file,
            "analysis_timestamp": datetime.now().isoformat(),
            "total_packets": len(all_packets),
            "tcp_packets_found": len(tcp_packets),
            "filter": {
                "server_ip": self._analysis_kwargs.get("server_ip"),
                "server_port": self._analysis_kwargs.get("server_port"),
            },
            "summary": {
                "total_connections": len(connections),
                "successful_handshakes": successful_handshakes,
                "failed_handshakes": failed_handshakes,
                "established_connections": successful_handshakes,
                "reset_connections": reset_connections,
                "normal_close": normal_close,
                "active_connections": len(connections) - reset_connections - normal_close,
            },
            "connections": connection_details
            if self._analysis_kwargs.get("detailed", False)
            else connection_details[:10],
            "issues": issues,
        }

    def _analyze_single_connection(self, conn_key: tuple, packets: list) -> dict[str, Any]:
        src_ip, src_port, dst_ip, dst_port = conn_key

        syn_count = 0
        syn_ack_count = 0
        ack_count = 0
        rst_count = 0
        fin_count = 0
        data_packets = 0
        retransmissions = 0

        seen_seqs = set()
        handshake_completed = False

        for pkt in packets:
            tcp = pkt[TCP]
            flags = tcp.flags

            if flags & 0x02:
                syn_count += 1
            if flags & 0x12 == 0x12:
                syn_ack_count += 1
            if flags & 0x10:
                ack_count += 1
            if flags & 0x04:
                rst_count += 1
            if flags & 0x01:
                fin_count += 1

            if len(tcp.payload) > 0:
                data_packets += 1

            seq = tcp.seq
            if seq in seen_seqs and len(tcp.payload) > 0:
                retransmissions += 1
            seen_seqs.add(seq)

        if syn_count > 0 and syn_ack_count > 0 and ack_count > 0:
            handshake_completed = True

        close_reason = "unknown"
        if rst_count > 0:
            close_reason = "reset"
        elif fin_count >= 2:
            close_reason = "normal"
        elif len(packets) > 3:
            close_reason = "active"

        return {
            "client": f"{src_ip}:{src_port}",
            "server": f"{dst_ip}:{dst_port}",
            "state": "closed" if close_reason in ["reset", "normal"] else "active",
            "handshake_completed": handshake_completed,
            "syn_count": syn_count,
            "syn_ack_count": syn_ack_count,
            "ack_count": ack_count,
            "rst_count": rst_count,
            "fin_count": fin_count,
            "data_packets": data_packets,
            "retransmissions": retransmissions,
            "close_reason": close_reason,
            "packet_count": len(packets),
        }

    def _analyze_anomalies(self, pcap_file: str, tcp_packets: list) -> dict[str, Any]:
        from collections import defaultdict

        connections = defaultdict(list)
        for pkt in tcp_packets:
            conn_key = self._get_connection_key(pkt)
            connections[conn_key].append(pkt)

        stats = self._collect_tcp_statistics(connections, tcp_packets)
        patterns = self._detect_tcp_patterns(stats)

        return {
            "file": pcap_file,
            "analysis_timestamp": datetime.now().isoformat(),
            "filter": {
                "server_ip": self._analysis_kwargs.get("server_ip"),
                "server_port": self._analysis_kwargs.get("server_port"),
            },
            "statistics": stats,
            "patterns": patterns,
            "summary": self._generate_pattern_summary(patterns),
        }

    def _analyze_retrans(self, pcap_file: str, tcp_packets: list) -> dict[str, Any]:
        from collections import defaultdict

        threshold = self._analysis_kwargs.get("threshold", 0.02)

        connections = defaultdict(list)
        for pkt in tcp_packets:
            conn_key = self._get_connection_key(pkt)
            connections[conn_key].append(pkt)

        by_connection = []
        total_retrans = 0
        worst_rate = 0
        worst_conn = ""

        for conn_key, pkts in connections.items():
            src_ip, src_port, dst_ip, dst_port = conn_key
            conn_str = f"{src_ip}:{src_port} <-> {dst_ip}:{dst_port}"

            conn_info = self._analyze_single_connection(conn_key, pkts)
            retrans_count = conn_info["retransmissions"]
            total_retrans += retrans_count

            retrans_rate = retrans_count / len(pkts) if len(pkts) > 0 else 0

            by_connection.append(
                {
                    "connection": conn_str,
                    "retrans_count": retrans_count,
                    "total_packets": len(pkts),
                    "retrans_rate": retrans_rate,
                }
            )

            if retrans_rate > worst_rate:
                worst_rate = retrans_rate
                worst_conn = conn_str

        by_connection.sort(key=lambda x: x["retrans_rate"], reverse=True)

        overall_rate = total_retrans / len(tcp_packets) if len(tcp_packets) > 0 else 0
        connections_above_threshold = sum(
            1 for c in by_connection if c["retrans_rate"] > threshold
        )

        return {
            "file": pcap_file,
            "analysis_timestamp": datetime.now().isoformat(),
            "total_packets": len(tcp_packets),
            "total_retransmissions": total_retrans,
            "retransmission_rate": overall_rate,
            "threshold": threshold,
            "exceeds_threshold": overall_rate > threshold,
            "by_connection": by_connection[:10],
            "summary": {
                "worst_connection": worst_conn,
                "worst_retrans_rate": worst_rate,
                "connections_above_threshold": connections_above_threshold,
            },
        }

    def _analyze_flow(self, pcap_file: str, tcp_packets: list) -> dict[str, Any]:
        server_ip = self._analysis_kwargs.get("server_ip")
        server_port = self._analysis_kwargs.get("server_port")

        if not server_ip:
            return {"error": "server_ip is required for traffic flow analysis"}

        client_to_server = {
            "packet_count": 0,
            "byte_count": 0,
            "syn_count": 0,
            "rst_count": 0,
            "fin_count": 0,
            "data_packets": 0,
            "retransmissions": 0,
        }

        server_to_client = {
            "packet_count": 0,
            "byte_count": 0,
            "syn_count": 0,
            "rst_count": 0,
            "fin_count": 0,
            "data_packets": 0,
            "retransmissions": 0,
        }

        client_seqs = set()
        server_seqs = set()

        for pkt in tcp_packets:
            src_ip, dst_ip = self._extract_ips(pkt)
            tcp = pkt[TCP]
            flags = tcp.flags

            is_client_to_server = dst_ip == server_ip
            if server_port:
                is_client_to_server = tcp.dport == server_port

            stats = client_to_server if is_client_to_server else server_to_client
            seqs = client_seqs if is_client_to_server else server_seqs

            stats["packet_count"] += 1
            stats["byte_count"] += len(pkt)

            if flags & 0x02:
                stats["syn_count"] += 1
            if flags & 0x04:
                stats["rst_count"] += 1
            if flags & 0x01:
                stats["fin_count"] += 1
            if len(tcp.payload) > 0:
                stats["data_packets"] += 1

            seq = tcp.seq
            if seq in seqs and len(tcp.payload) > 0:
                stats["retransmissions"] += 1
            seqs.add(seq)

        total_client = client_to_server["packet_count"]
        total_server = server_to_client["packet_count"]
        asymmetry_ratio = total_client / total_server if total_server > 0 else 0

        client_rst = client_to_server["rst_count"]
        server_rst = server_to_client["rst_count"]
        if client_rst > server_rst:
            rst_source = "client"
            interpretation = (
                f"Client sends all RST packets ({client_rst} vs {server_rst}). "
                "Server responds normally. Suggests client-side issue (possibly firewall)."
            )
        elif server_rst > client_rst:
            rst_source = "server"
            interpretation = "Server sends more RST packets. Suggests server-side rejection or service issue."
        else:
            rst_source = "balanced"
            interpretation = "Balanced RST distribution."

        return {
            "file": pcap_file,
            "analysis_timestamp": datetime.now().isoformat(),
            "server": f"{server_ip}:{server_port or 'any'}",
            "client_to_server": client_to_server,
            "server_to_client": server_to_client,
            "analysis": {
                "asymmetry_ratio": asymmetry_ratio,
                "primary_rst_source": rst_source,
                "data_flow_direction": "client_heavy"
                if asymmetry_ratio > 1.2
                else "server_heavy"
                if asymmetry_ratio < 0.8
                else "balanced",
                "interpretation": interpretation,
            },
        }

    def _get_connection_key(self, pkt: Any) -> tuple:
        src_ip, dst_ip = self._extract_ips(pkt)
        tcp = pkt[TCP]
        return (src_ip, tcp.sport, dst_ip, tcp.dport)

    def _extract_ips(self, pkt: Any) -> tuple:
        if pkt.haslayer(IP):
            return pkt[IP].src, pkt[IP].dst
        if pkt.haslayer(IPv6):
            return pkt[IPv6].src, pkt[IPv6].dst
        return "unknown", "unknown"

    def _collect_tcp_statistics(self, connections: dict, tcp_packets: list) -> dict[str, Any]:
        stats = {
            "total_connections": len(connections),
            "total_packets": len(tcp_packets),
            "handshake": {"successful": 0, "failed": 0, "incomplete": 0},
            "flags": {"syn": 0, "syn_ack": 0, "rst": 0, "fin": 0, "ack": 0},
            "rst_distribution": {
                "by_source": {},
                "by_direction": {"to_server": 0, "from_server": 0, "unknown": 0},
                "connections_with_rst": [],
            },
            "retransmissions": {"total": 0, "by_connection": {}},
            "connection_states": {"established": 0, "reset": 0, "closed": 0, "unknown": 0},
        }

        server_ip = self._analysis_kwargs.get("server_ip")

        for conn_key, pkts in connections.items():
            src_ip, src_port, dst_ip, dst_port = conn_key
            conn_info = self._analyze_single_connection(conn_key, pkts)

            if conn_info["handshake_completed"]:
                stats["handshake"]["successful"] += 1
            else:
                stats["handshake"]["failed"] += 1

            for pkt in pkts:
                tcp = pkt[TCP]
                flags = tcp.flags

                if flags & 0x02:
                    stats["flags"]["syn"] += 1
                if flags & 0x12 == 0x12:
                    stats["flags"]["syn_ack"] += 1
                if flags & 0x04:
                    stats["flags"]["rst"] += 1
                    pkt_src_ip, _ = self._extract_ips(pkt)
                    stats["rst_distribution"]["by_source"][pkt_src_ip] = (
                        stats["rst_distribution"]["by_source"].get(pkt_src_ip, 0) + 1
                    )

                    if server_ip:
                        if pkt_src_ip == server_ip:
                            stats["rst_distribution"]["by_direction"]["from_server"] += 1
                        else:
                            stats["rst_distribution"]["by_direction"]["to_server"] += 1
                    else:
                        stats["rst_distribution"]["by_direction"]["unknown"] += 1

                if flags & 0x01:
                    stats["flags"]["fin"] += 1
                if flags & 0x10:
                    stats["flags"]["ack"] += 1

            if conn_info["rst_count"] > 0:
                stats["rst_distribution"]["connections_with_rst"].append(
                    f"{src_ip}:{src_port} <-> {dst_ip}:{dst_port}"
                )

            retrans = conn_info["retransmissions"]
            stats["retransmissions"]["total"] += retrans
            if retrans > 0:
                conn_str = f"{src_ip}:{src_port} <-> {dst_ip}:{dst_port}"
                stats["retransmissions"]["by_connection"][conn_str] = retrans

            if conn_info["close_reason"] == "reset":
                stats["connection_states"]["reset"] += 1
            elif conn_info["close_reason"] == "normal":
                stats["connection_states"]["closed"] += 1
            elif conn_info["handshake_completed"]:
                stats["connection_states"]["established"] += 1
            else:
                stats["connection_states"]["unknown"] += 1

        stats["retransmissions"]["rate"] = (
            stats["retransmissions"]["total"] / stats["total_packets"]
            if stats["total_packets"] > 0
            else 0
        )

        return stats

    def _detect_tcp_patterns(self, stats: dict[str, Any]) -> list[dict[str, Any]]:
        patterns = []

        rst_by_dir = stats["rst_distribution"]["by_direction"]
        if rst_by_dir["to_server"] > 0 or rst_by_dir["from_server"] > 0:
            total_rst = rst_by_dir["to_server"] + rst_by_dir["from_server"]
            if total_rst > 0:
                patterns.append(
                    {
                        "pattern": "rst_directional_asymmetry",
                        "category": "connection_termination",
                        "observations": {
                            "rst_to_server": rst_by_dir["to_server"],
                            "rst_from_server": rst_by_dir["from_server"],
                            "ratio": rst_by_dir["to_server"] / total_rst,
                            "affected_connections": stats["rst_distribution"][
                                "connections_with_rst"
                            ],
                        },
                        "description": (
                            f"RST packets show directional bias: {rst_by_dir['to_server']} "
                            f"toward server, {rst_by_dir['from_server']} from server"
                        ),
                    }
                )

        retrans_rate = stats["retransmissions"]["rate"]
        if retrans_rate > 0:
            patterns.append(
                {
                    "pattern": "packet_retransmission",
                    "category": "reliability",
                    "observations": {
                        "total_retransmissions": stats["retransmissions"]["total"],
                        "total_packets": stats["total_packets"],
                        "rate": retrans_rate,
                        "threshold": 0.02,
                        "exceeds_threshold": retrans_rate > 0.02,
                        "by_connection": stats["retransmissions"]["by_connection"],
                    },
                    "description": (
                        f"Retransmission rate: {retrans_rate:.2%} "
                        f"({stats['retransmissions']['total']}/{stats['total_packets']} packets)"
                    ),
                }
            )

        total_attempts = stats["handshake"]["successful"] + stats["handshake"]["failed"]
        if total_attempts > 0:
            failure_rate = stats["handshake"]["failed"] / total_attempts
            if failure_rate > 0:
                patterns.append(
                    {
                        "pattern": "handshake_completion",
                        "category": "connection_establishment",
                        "observations": {
                            "successful": stats["handshake"]["successful"],
                            "failed": stats["handshake"]["failed"],
                            "failure_rate": failure_rate,
                        },
                        "description": (
                            f"Handshake success rate: {(1 - failure_rate):.1%} "
                            f"({stats['handshake']['successful']}/{total_attempts})"
                        ),
                    }
                )

        total_conns = stats["total_connections"]
        if total_conns > 0:
            rst_rate = stats["connection_states"]["reset"] / total_conns
            if rst_rate > 0.1:
                patterns.append(
                    {
                        "pattern": "abnormal_termination",
                        "category": "connection_lifecycle",
                        "observations": {
                            "reset_count": stats["connection_states"]["reset"],
                            "normal_close": stats["connection_states"]["closed"],
                            "total_connections": total_conns,
                            "reset_rate": rst_rate,
                        },
                        "description": (
                            f"{rst_rate:.1%} of connections terminated by RST "
                            f"({stats['connection_states']['reset']}/{total_conns})"
                        ),
                    }
                )

        if stats["flags"]["syn"] > 0:
            syn_ack_ratio = stats["flags"]["syn_ack"] / stats["flags"]["syn"]
            if syn_ack_ratio < 0.5:
                patterns.append(
                    {
                        "pattern": "syn_response_imbalance",
                        "category": "connection_establishment",
                        "observations": {
                            "syn_count": stats["flags"]["syn"],
                            "syn_ack_count": stats["flags"]["syn_ack"],
                            "response_ratio": syn_ack_ratio,
                        },
                        "description": (
                            f"Only {syn_ack_ratio:.1%} of SYN packets received SYN-ACK response"
                        ),
                    }
                )

        return patterns

    def _generate_pattern_summary(self, patterns: list[dict[str, Any]]) -> dict[str, Any]:
        summary = {"total_patterns": len(patterns), "by_category": {}, "notable_observations": []}

        for pattern in patterns:
            category = pattern["category"]
            summary["by_category"][category] = summary["by_category"].get(category, 0) + 1

        for pattern in patterns:
            if pattern["pattern"] == "rst_directional_asymmetry":
                obs = pattern["observations"]
                if obs["ratio"] > 0.9 or obs["ratio"] < 0.1:
                    summary["notable_observations"].append(
                        {
                            "type": "strong_rst_asymmetry",
                            "detail": f"RST packets heavily biased: {obs['ratio']:.1%} in one direction",
                        }
                    )

            if pattern["pattern"] == "packet_retransmission":
                obs = pattern["observations"]
                if obs["exceeds_threshold"]:
                    summary["notable_observations"].append(
                        {
                            "type": "high_retransmission",
                            "detail": f"Retransmission rate {obs['rate']:.2%} exceeds typical threshold of 2%",
                        }
                    )

        return summary


def build_analyzers(config: Config) -> dict[str, Any]:
    return {
        "dns": DNSAnalyzer(config),
        "dhcp": DHCPAnalyzer(config),
        "icmp": ICMPAnalyzer(config),
        "capinfos": CapInfosAnalyzer(config),
        "tcp": TCPAnalyzer(config),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze local PCAP files without MCP.")
    parser.add_argument(
        "--type",
        required=True,
        choices=[
            "dns",
            "dhcp",
            "icmp",
            "capinfos",
            "tcp-connections",
            "tcp-anomalies",
            "tcp-retransmissions",
            "tcp-traffic-flow",
            "all",
        ],
        help="Analysis type",
    )
    parser.add_argument("--pcap", required=True, help="Local PCAP file path")
    parser.add_argument("--server-ip", help="Server IP for TCP filters")
    parser.add_argument("--server-port", type=int, help="Server port for TCP filters")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.02,
        help="Retransmission rate threshold (tcp-retransmissions)",
    )
    parser.add_argument(
        "--max-packets",
        type=int,
        help="Maximum packets to analyze (per protocol)",
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Return detailed connection list (tcp-connections)",
    )
    parser.add_argument(
        "--no-traffic-flow",
        action="store_true",
        help="Skip tcp-traffic-flow when running --type all",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    parser.add_argument("--output", help="Write JSON output to file")

    return parser.parse_args()


def emit_output(payload: dict[str, Any], args: argparse.Namespace, exit_code: int = 0) -> int:
    indent = 2 if args.pretty else None
    serialized = json.dumps(payload, indent=indent, ensure_ascii=True, default=str)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(serialized)
            handle.write("\n")
    else:
        print(serialized)

    return exit_code


def main() -> int:
    args = parse_args()
    config = Config(max_packets=args.max_packets)
    config.validate()

    analyzers = build_analyzers(config)

    try:
        if args.type == "all":
            results: dict[str, Any] = {
                "capinfos": analyzers["capinfos"].analyze_capinfos(args.pcap),
                "dns": analyzers["dns"].analyze_dns_packets(args.pcap),
                "dhcp": analyzers["dhcp"].analyze_dhcp_packets(args.pcap),
                "icmp": analyzers["icmp"].analyze_icmp_packets(args.pcap),
                "tcp-connections": analyzers["tcp"].analyze_tcp_connections(
                    args.pcap,
                    server_ip=args.server_ip,
                    server_port=args.server_port,
                    detailed=args.detailed,
                ),
                "tcp-anomalies": analyzers["tcp"].analyze_tcp_anomalies(
                    args.pcap,
                    server_ip=args.server_ip,
                    server_port=args.server_port,
                ),
                "tcp-retransmissions": analyzers["tcp"].analyze_tcp_retransmissions(
                    args.pcap,
                    server_ip=args.server_ip,
                    threshold=args.threshold,
                ),
            }

            if not args.no_traffic_flow:
                if not args.server_ip:
                    results["tcp-traffic-flow"] = {
                        "error": "server_ip is required for tcp-traffic-flow",
                        "pcap_file": args.pcap,
                    }
                else:
                    results["tcp-traffic-flow"] = analyzers["tcp"].analyze_tcp_traffic_flow(
                        args.pcap,
                        server_ip=args.server_ip,
                        server_port=args.server_port,
                    )

            return emit_output(results, args)

        if args.type == "dns":
            return emit_output(analyzers["dns"].analyze_dns_packets(args.pcap), args)
        if args.type == "dhcp":
            return emit_output(analyzers["dhcp"].analyze_dhcp_packets(args.pcap), args)
        if args.type == "icmp":
            return emit_output(analyzers["icmp"].analyze_icmp_packets(args.pcap), args)
        if args.type == "capinfos":
            return emit_output(analyzers["capinfos"].analyze_capinfos(args.pcap), args)
        if args.type == "tcp-connections":
            return emit_output(
                analyzers["tcp"].analyze_tcp_connections(
                    args.pcap,
                    server_ip=args.server_ip,
                    server_port=args.server_port,
                    detailed=args.detailed,
                ),
                args,
            )
        if args.type == "tcp-anomalies":
            return emit_output(
                analyzers["tcp"].analyze_tcp_anomalies(
                    args.pcap,
                    server_ip=args.server_ip,
                    server_port=args.server_port,
                ),
                args,
            )
        if args.type == "tcp-retransmissions":
            return emit_output(
                analyzers["tcp"].analyze_tcp_retransmissions(
                    args.pcap,
                    server_ip=args.server_ip,
                    threshold=args.threshold,
                ),
                args,
            )
        if args.type == "tcp-traffic-flow":
            if not args.server_ip:
                return emit_output(
                    {"error": "server_ip is required for tcp-traffic-flow", "pcap_file": args.pcap},
                    args,
                    exit_code=1,
                )
            return emit_output(
                analyzers["tcp"].analyze_tcp_traffic_flow(
                    args.pcap,
                    server_ip=args.server_ip,
                    server_port=args.server_port,
                ),
                args,
            )

        return emit_output({"error": f"Unknown analysis type: {args.type}"}, args, exit_code=1)
    except Exception as exc:
        return emit_output({"error": str(exc)}, args, exit_code=1)


if __name__ == "__main__":
    raise SystemExit(main())
