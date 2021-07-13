#!/usr/bin/env python3
import requests
import json
import os
import tempfile
import subprocess
download_fwupd_filename = 'fwupd.snap'
repack_fwupd_filename = 'fwupd-repack.snap'

def sendGetRequest(url, headers):
        try:
                r = requests.get(url, verify=False, headers=headers)
                return r
        except requests.exceptions.ConnectionError:
                print("[-] Failed to establish connection\n")
                exit(-1)

def http_get_snap(snap_file: str):
        token_header={
                'Snap-Device-Series': '16',
                'User-Agent': "Mozilla/5.0 (compatible; MSIE 9.0; Windows Phone OS 7.5; Trident/5.0; IEMobile/9.0)"
        }

        url = 'http://api.snapcraft.io/v2/snaps/info/fwupd'
        resp = sendGetRequest(url, headers=token_header)
        json_data = json.loads(resp.text.rstrip('\n'))

        for item in json_data['channel-map']:
                if item['channel']['architecture'] == 'amd64' and \
                   item['channel']['name'] == 'stable' and \
                   item['channel']['track'] == 'latest':
                        url_snap = item['download']['url']
                        revision = item['revision']
                        version  = item['version']
                        name     = json_data['name']

        r = requests.get(url_snap, allow_redirects=True)
        open(snap_file, 'wb').write(r.content)

        print("[snap] name: %s" % name)
        print("[snap] version: %s" % version)
        print("[snap] revision: %s" % revision)
        print("[snap] url_snap: %s" % url_snap)

def repack_snap_no_warn(snap_file: str):
        tmpdir = tempfile.TemporaryDirectory(prefix='fwupd.')
        commandFile = os.path.join(tmpdir.name, "fwupd-command")

        try:
                # extract the snap
                subprocess.run(["unsquashfs", "-f", "-d", tmpdir.name, snap_file], check=True)

                # file present?
                if not os.path.isfile(commandFile):
                        raise ValueError("file not found: fwupd-command")

                # insert environment variant
                with open(commandFile,'r+') as fd:
                        contents    = fd.readlines()
                        line_str    = "exec \"$@\""
                        line_insert = "export FWUPD_SUPPORTED=1\n"

                        for index, line in enumerate(contents):
                                if line_str in line:
                                        contents.insert(index, line_insert)
                                        break

                        fd.seek(0)
                        fd.writelines(contents)

                # wrap up the new one
                new_filedir  = os.path.dirname(snap_file)
                new_file     = os.path.join(new_filedir, repack_fwupd_filename)
                print("[Info] wrap up %s" % tmpdir.name)

                subprocess.run(["snap",
                                "pack",
                                "--filename",
                                repack_fwupd_filename,
                                tmpdir.name,
                                new_filedir],
                                check=True)

                if not os.path.isfile(new_file):
                        raise ValueError("file not found: %s" % new_file)

        except subprocess.CalledProcessError as e:
                print("[Error] %d, %s" % (e.returncode, e.stderr))
        except ValueError as e:
                print("[Error] ", e)

def main(argv):
        snap_download_file = os.path.join(os.getcwd(), download_fwupd_filename)
        snap_new_file = os.path.join(os.getcwd(), repack_fwupd_filename)

        # clean up old files
        if os.path.isfile(snap_download_file):
                os.remove(snap_download_file)

        if os.path.isfile(snap_new_file):
                os.remove(snap_new_file)

        # download snap and rework it!
        http_get_snap(snap_download_file)
        repack_snap_no_warn(snap_download_file)

        return True

## Entry Point ##
if __name__ == '__main__':
        import sys
        main(sys.argv)
