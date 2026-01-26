#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlencode


def die(msg, status=None, body=None):
    print(msg, file=sys.stderr)
    if status is not None:
        print(f"HTTP status: {status}", file=sys.stderr)
    if body is not None:
        try:
            print(f"Response: {body.decode('utf-8')}", file=sys.stderr)
        except Exception:
            print(f"Response (raw): {body}", file=sys.stderr)
    sys.exit(1)


def sha512_hex(value):
    digest = hashlib.sha512()
    digest.update(value.encode("utf-8"))
    return digest.hexdigest()


class ZStackClient:
    def __init__(self, host, username, password, timeout, poll_interval, wait_timeout, allow_get_fallback):
        self.host = host.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.wait_timeout = wait_timeout
        self.allow_get_fallback = allow_get_fallback
        self.session_uuid = None

    def _request(self, method, path_or_url, data=None, headers=None):
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            url = path_or_url
        else:
            url = self.host + path_or_url
        body = None
        if data is not None:
            body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=body, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        if headers:
            for key, value in headers.items():
                req.add_header(key, value)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status, resp.read(), resp.headers
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read(), exc.headers

    def _auth_headers(self):
        if not self.session_uuid:
            die("session uuid missing; login first")
        return {"Authorization": f"OAuth {self.session_uuid}"}

    def _parse_json(self, body, context):
        try:
            return json.loads(body.decode("utf-8"))
        except Exception as exc:
            die(f"Failed to parse {context} JSON: {exc}", None, body)

    def login(self):
        payload = {
            "logInByAccount": {
                "accountName": self.username,
                "password": sha512_hex(self.password),
            }
        }
        status, body, _ = self._request("PUT", "/zstack/v1/accounts/login", data=payload)
        if status != 200:
            die("Login failed.", status, body)
        resp = self._parse_json(body, "login")
        session_uuid = (resp.get("inventory") or {}).get("uuid")
        if not session_uuid:
            session_uuid = (resp.get("session") or {}).get("uuid") or resp.get("sessionUuid")
        if not session_uuid:
            die("Login succeeded but session uuid missing.", status, body)
        self.session_uuid = session_uuid

    def _poll_job(self, job_url):
        deadline = time.time() + self.wait_timeout
        while time.time() < deadline:
            status, body, _ = self._request("GET", job_url, headers=self._auth_headers())
            if status == 200:
                return True, body
            if status >= 400:
                return False, body
            time.sleep(self.poll_interval)
        return False, b"timeout"

    def _handle_async(self, status, body, resp_headers, action_desc):
        if status == 200:
            return
        if status != 202:
            die(f"{action_desc} failed.", status, body)
        payload = {}
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            payload = {}
        job_url = payload.get("location") or resp_headers.get("Location")
        if not job_url:
            die(f"{action_desc} returned 202 but no job location found.", status, body)
        ok, job_body = self._poll_job(job_url)
        if not ok:
            die(f"{action_desc} job failed.", status, job_body)

    def list_vms(self, state=None):
        path = "/zstack/v1/vm-instances"
        if state:
            path += "?" + urlencode({"q": f"state={state}"})
        status, body, _ = self._request("GET", path, headers=self._auth_headers())
        if status != 200:
            die("VM query failed.", status, body)
        return self._parse_json(body, "vm list").get("inventories") or []

    def list_l3_networks(self):
        status, body, _ = self._request("GET", "/zstack/v1/l3-networks", headers=self._auth_headers())
        if status != 200:
            die("L3 networks query failed.", status, body)
        return self._parse_json(body, "l3 networks").get("inventories") or []

    def get_vm_by_uuid(self, vm_uuid):
        status, body, _ = self._request(
            "GET",
            f"/zstack/v1/vm-instances?uuid={vm_uuid}",
            headers=self._auth_headers(),
        )
        if status != 200:
            die("VM query by uuid failed.", status, body)
        vms = self._parse_json(body, "vm by uuid").get("inventories") or []
        return vms[0] if vms else None

    def get_vm_by_name(self, name):
        vms = self.list_vms()
        matches = [vm for vm in vms if vm.get("name") == name or vm.get("hostname") == name]
        if not matches:
            die(f"VM '{name}' not found.")
        if len(matches) > 1:
            die(f"Multiple VMs named '{name}' found: {[vm.get('uuid') for vm in matches]}")
        return matches[0]

    def start_vm(self, vm_uuid):
        payload = {"startVmInstance": {}}
        status, body, resp_headers = self._request(
            "PUT",
            f"/zstack/v1/vm-instances/{vm_uuid}/actions",
            data=payload,
            headers=self._auth_headers(),
        )
        self._handle_async(status, body, resp_headers, "Start VM")

    def stop_vm(self, vm_uuid, stop_type):
        payload = {"stopVmInstance": {"type": stop_type}}
        status, body, resp_headers = self._request(
            "PUT",
            f"/zstack/v1/vm-instances/{vm_uuid}/actions",
            data=payload,
            headers=self._auth_headers(),
        )
        self._handle_async(status, body, resp_headers, "Stop VM")

    def wait_state(self, vm_uuid, desired_state):
        deadline = time.time() + self.wait_timeout
        desired_state = desired_state.lower()
        while time.time() < deadline:
            vm = self.get_vm_by_uuid(vm_uuid)
            if vm:
                state = (vm.get("state") or "").lower()
                if state == desired_state:
                    return vm
            time.sleep(self.poll_interval)
        die(f"VM did not reach state {desired_state} within {self.wait_timeout}s")

    def attach_l3(self, vm_uuid, l3_uuid):
        path = f"/zstack/v1/vm-instances/{vm_uuid}/l3-networks/{l3_uuid}"
        status, body, resp_headers = self._request("POST", path, headers=self._auth_headers())
        if status in (200, 202):
            self._handle_async(status, body, resp_headers, "Attach L3 network")
            return
        if status in (404, 405) and self.allow_get_fallback:
            status, body, resp_headers = self._request("GET", path, headers=self._auth_headers())
            self._handle_async(status, body, resp_headers, "Attach L3 network (GET fallback)")
            return
        die("Attach L3 network failed.", status, body)

    def detach_nic(self, vm_uuid, nic_uuid):
        paths = [
            f"/zstack/v1/vm-instances/nics/{nic_uuid}",
            f"/zstack/v1/vm-instances/{vm_uuid}/nics/{nic_uuid}",
        ]
        for path in paths:
            status, body, resp_headers = self._request("DELETE", path, headers=self._auth_headers())
            if status in (200, 202):
                self._handle_async(status, body, resp_headers, "Detach VM NIC")
                return
            if status == 404:
                continue
            die("Detach VM NIC failed.", status, body)
        die("Detach VM NIC failed: no matching endpoint.")


def resolve_vm(client, vm_name, vm_uuid):
    if vm_uuid:
        vm = client.get_vm_by_uuid(vm_uuid)
        if not vm:
            die(f"VM uuid '{vm_uuid}' not found.")
        return vm
    if not vm_name:
        die("Provide --vm-name or --vm-uuid")
    return client.get_vm_by_name(vm_name)


def resolve_l3(client, l3_name, l3_uuid):
    if l3_uuid:
        return l3_uuid
    if not l3_name:
        die("Provide --l3-name or --l3-uuid")
    l3s = client.list_l3_networks()
    matches = [l3 for l3 in l3s if l3.get("name") == l3_name]
    if not matches:
        die(f"L3 network '{l3_name}' not found.")
    if len(matches) > 1:
        die(f"Multiple L3 networks named '{l3_name}' found: {[l3.get('uuid') for l3 in matches]}")
    return matches[0].get("uuid")


def cmd_list(args, client):
    vms = client.list_vms(state=args.state)
    l3s = client.list_l3_networks()
    l3_map = {l3.get("uuid"): l3.get("name") for l3 in l3s}
    output = []
    for vm in vms:
        name = vm.get("hostname") or vm.get("name") or vm.get("uuid")
        if args.name and name != args.name:
            continue
        nics = []
        for nic in vm.get("vmNics") or []:
            l3_uuid = nic.get("l3NetworkUuid")
            nics.append({
                "name": l3_map.get(l3_uuid) or l3_uuid,
                "ip": nic.get("ip") or nic.get("guestIp"),
            })
        output.append({
            "name": name,
            "state": vm.get("state"),
            "nics": nics,
        })
    print(json.dumps(output, ensure_ascii=True, indent=2))


def resolve_nic(client, vm, nic_uuid, l3_name, l3_uuid):
    if nic_uuid:
        for nic in vm.get("vmNics") or []:
            if nic.get("uuid") == nic_uuid:
                return nic
        die(f"NIC uuid '{nic_uuid}' not found on VM.")
    if not l3_name and not l3_uuid:
        die("Provide --nic-uuid or --l3-name/--l3-uuid")
    l3_uuid = resolve_l3(client, l3_name, l3_uuid)
    matches = [nic for nic in (vm.get("vmNics") or []) if nic.get("l3NetworkUuid") == l3_uuid]
    if not matches:
        die("No NIC found on target L3 network.")
    if len(matches) > 1:
        die("Multiple NICs match target L3 network; provide --nic-uuid.")
    return matches[0]


def cmd_list_l3(args, client):
    l3s = client.list_l3_networks()
    output = []
    for l3 in l3s:
        name = l3.get("name")
        if args.name and name != args.name:
            continue
        ip_ranges = []
        for ip_range in l3.get("ipRanges") or []:
            ip_ranges.append({
                "startIp": ip_range.get("startIp"),
                "endIp": ip_range.get("endIp"),
                "netmask": ip_range.get("netmask"),
            })
        output.append({
            "name": name,
            "uuid": l3.get("uuid"),
            "ipRanges": ip_ranges,
        })
    print(json.dumps(output, ensure_ascii=True, indent=2))


def cmd_start(args, client):
    vm = resolve_vm(client, args.vm_name, args.vm_uuid)
    if (vm.get("state") or "").lower() == "running":
        print("VM is already running.")
        return
    client.start_vm(vm.get("uuid"))
    client.wait_state(vm.get("uuid"), "running")
    print("VM started.")


def cmd_stop(args, client):
    vm = resolve_vm(client, args.vm_name, args.vm_uuid)
    if (vm.get("state") or "").lower() == "stopped":
        print("VM is already stopped.")
        return
    client.stop_vm(vm.get("uuid"), args.type)
    client.wait_state(vm.get("uuid"), "stopped")
    print("VM stopped.")


def cmd_add_nic(args, client):
    vm = resolve_vm(client, args.vm_name, args.vm_uuid)
    l3_uuid = resolve_l3(client, args.l3_name, args.l3_uuid)
    vm_uuid = vm.get("uuid")
    for nic in vm.get("vmNics") or []:
        if nic.get("l3NetworkUuid") == l3_uuid:
            print("VM already has NIC on target L3 network.")
            return
    if (vm.get("state") or "").lower() == "running":
        client.stop_vm(vm_uuid, "grace")
        client.wait_state(vm_uuid, "stopped")
    client.attach_l3(vm_uuid, l3_uuid)
    client.start_vm(vm_uuid)
    vm = client.wait_state(vm_uuid, "running")
    print(json.dumps({
        "name": vm.get("name"),
        "state": vm.get("state"),
        "vmNics": vm.get("vmNics"),
    }, ensure_ascii=True, indent=2))


def cmd_replace_nic(args, client):
    vm = resolve_vm(client, args.vm_name, args.vm_uuid)
    if not args.to_l3_name and not args.to_l3_uuid:
        die("Provide --to-l3-name or --to-l3-uuid")
    vm_uuid = vm.get("uuid")
    from_nic = resolve_nic(client, vm, args.from_nic_uuid, args.from_l3_name, args.from_l3_uuid)
    to_l3_uuid = resolve_l3(client, args.to_l3_name, args.to_l3_uuid)
    if from_nic.get("l3NetworkUuid") == to_l3_uuid:
        print("Source and target L3 network are the same; nothing to do.")
        return
    target_attached = any(
        nic.get("l3NetworkUuid") == to_l3_uuid for nic in (vm.get("vmNics") or [])
    )
    if (vm.get("state") or "").lower() == "running":
        client.stop_vm(vm_uuid, "grace")
        client.wait_state(vm_uuid, "stopped")
    client.detach_nic(vm_uuid, from_nic.get("uuid"))
    if not target_attached:
        client.attach_l3(vm_uuid, to_l3_uuid)
    client.start_vm(vm_uuid)
    vm = client.wait_state(vm_uuid, "running")
    print(json.dumps({
        "name": vm.get("name"),
        "state": vm.get("state"),
        "vmNics": vm.get("vmNics"),
    }, ensure_ascii=True, indent=2))


def cmd_remove_nic(args, client):
    vm = resolve_vm(client, args.vm_name, args.vm_uuid)
    vm_uuid = vm.get("uuid")

    nic = resolve_nic(client, vm, args.nic_uuid, args.l3_name, args.l3_uuid)
    nic_uuid = nic.get("uuid")

    if (vm.get("state") or "").lower() == "running":
        client.stop_vm(vm_uuid, "grace")
        client.wait_state(vm_uuid, "stopped")
    client.detach_nic(vm_uuid, nic_uuid)
    client.start_vm(vm_uuid)
    vm = client.wait_state(vm_uuid, "running")
    print(json.dumps({
        "name": vm.get("name"),
        "state": vm.get("state"),
        "vmNics": vm.get("vmNics"),
    }, ensure_ascii=True, indent=2))


def build_parser():
    parser = argparse.ArgumentParser(description="ZStack VM operations")
    parser.add_argument("--host", default=os.environ.get("ZSTACK_HOST", "http://localhost:8080"))
    parser.add_argument("--username", default=os.environ.get("ZSTACK_USERNAME"))
    parser.add_argument("--password", default=os.environ.get("ZSTACK_PASSWORD"))
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--poll-interval", type=int, default=3)
    parser.add_argument("--wait-timeout", type=int, default=300)
    parser.add_argument("--allow-get-fallback", action="store_true", help="Allow GET fallback for attach L3 endpoint")

    subparsers = parser.add_subparsers(dest="command")
    if hasattr(subparsers, "required"):
        subparsers.required = True

    list_parser = subparsers.add_parser("list-vms", help="List VM status and NICs")
    list_parser.add_argument("--state", help="Filter by VM state, e.g. Running or Stopped")
    list_parser.add_argument("--name", help="Filter by VM name/hostname")
    list_parser.set_defaults(func=cmd_list)

    l3_parser = subparsers.add_parser("list-l3", help="List L3 networks and IP ranges")
    l3_parser.add_argument("--name", help="Filter by L3 name")
    l3_parser.set_defaults(func=cmd_list_l3)

    start_parser = subparsers.add_parser("start-vm", help="Start a VM")
    start_parser.add_argument("--vm-name")
    start_parser.add_argument("--vm-uuid")
    start_parser.set_defaults(func=cmd_start)

    stop_parser = subparsers.add_parser("stop-vm", help="Stop a VM")
    stop_parser.add_argument("--vm-name")
    stop_parser.add_argument("--vm-uuid")
    stop_parser.add_argument("--type", default="grace", choices=["grace", "cold"], help="Shutdown type")
    stop_parser.set_defaults(func=cmd_stop)

    add_parser = subparsers.add_parser("add-nic", help="Stop VM, attach L3 NIC, start VM")
    add_parser.add_argument("--vm-name")
    add_parser.add_argument("--vm-uuid")
    add_parser.add_argument("--l3-name")
    add_parser.add_argument("--l3-uuid")
    add_parser.set_defaults(func=cmd_add_nic)

    replace_parser = subparsers.add_parser("replace-nic", help="Stop VM, detach NIC, attach L3, start VM")
    replace_parser.add_argument("--vm-name")
    replace_parser.add_argument("--vm-uuid")
    replace_parser.add_argument("--from-nic-uuid")
    replace_parser.add_argument("--from-l3-name")
    replace_parser.add_argument("--from-l3-uuid")
    replace_parser.add_argument("--to-l3-name")
    replace_parser.add_argument("--to-l3-uuid")
    replace_parser.set_defaults(func=cmd_replace_nic)

    remove_parser = subparsers.add_parser("remove-nic", help="Stop VM, detach NIC, start VM")
    remove_parser.add_argument("--vm-name")
    remove_parser.add_argument("--vm-uuid")
    remove_parser.add_argument("--nic-uuid")
    remove_parser.add_argument("--l3-name")
    remove_parser.add_argument("--l3-uuid")
    remove_parser.set_defaults(func=cmd_remove_nic)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.username:
        die("Missing username. Set --username or ZSTACK_USERNAME.")
    if not args.password:
        die("Missing password. Set --password or ZSTACK_PASSWORD.")

    client = ZStackClient(
        host=args.host,
        username=args.username,
        password=args.password,
        timeout=args.timeout,
        poll_interval=args.poll_interval,
        wait_timeout=args.wait_timeout,
        allow_get_fallback=args.allow_get_fallback,
    )
    client.login()
    args.func(args, client)


if __name__ == "__main__":
    main()
