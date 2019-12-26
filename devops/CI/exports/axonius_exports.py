import time
import json
import signal
import urllib
import pathlib
import tempfile
import argparse
import traceback
import contextlib
import subprocess

import boto3
import requests


class ExportFileAlreadyExists(Exception):
    pass


_SCRIPT_FOLDER = pathlib.Path(__file__).parent.absolute()


def main():
    parser = argparse.ArgumentParser('Tool for exporting Axonius releases')

    parser.add_argument('--s3-bucket', default='axonius-releases', type=str)
    parser.add_argument('--notify-exports', action='store_true')
    parser.add_argument('--exports-notifications-url', type=str)
    parser.add_argument('--piggyback-arguments', type=json.loads, default={})
    parser.add_argument('--exports-server-token', type=str)
    parser.add_argument('--disable-ssl-verification', action='store_true')
    parser.add_argument('--teamcity-step', type=str, help='Normal teamcity usage')
    parser.add_argument('--teamcity-log', type=str, help='Normal teamcity usage')
    parser.add_argument('--teamcity-owner', type=str, help='Normal teamcity usage')

    subparsers = parser.add_subparsers()

    s3_parser = subparsers.add_parser('s3')
    s3_subparsers = s3_parser.add_subparsers()

    s3_upload_parser = s3_subparsers.add_parser('upload')

    s3_upload_parser.add_argument('--export-name', required=True, dest='name')
    s3_upload_parser.add_argument('--installer', type=pathlib.Path, default=None)
    s3_upload_parser.add_argument('--ova', type=pathlib.Path, default=None)
    s3_upload_parser.set_defaults(entrypoint=s3_upload)

    installer_parser = subparsers.add_parser('installer')
    git_arguments = installer_parser.add_argument_group('git')
    git_arguments.add_argument('--fork', required=True, type=str)
    git_arguments.add_argument('--branch')
    git_arguments.add_argument('--name', type=str, required=True)
    installer_parser.add_argument('--output', type=pathlib.Path,
                                  default=None, required=False,
                                  help='Will use axonius_[name].py where name is the argument given as name if not specified.')
    installer_parser.add_argument('--git-hash-file', type=pathlib.Path,
                                  default=None, required=False,
                                  help='Will use axonius_[name]_git_hash.txt where name is the argument given as name if not specified. This file contains the commit hash of the resulting installer.')
    installer_parser.set_defaults(entrypoint=installer)

    cloud_parser = subparsers.add_parser('cloud')
    installer_path_arguments = cloud_parser.add_mutually_exclusive_group(required=True)
    installer_path_arguments.add_argument('--installer', type=pathlib.Path,
                                          default=None, help='Local path to the installer')
    installer_path_arguments.add_argument('--installer-s3-name', type=str,
                                          help='Name of the release to download from s3')
    installer_path_arguments.add_argument('--installer-url', type=str, help='URL to download the installer from')
    cloud_parser.add_argument('--except', type=str, default='', dest='except_')
    cloud_parser.add_argument('--only', type=str, default='')
    cloud_parser.add_argument('--ami-regions', type=str, default='')
    cloud_parser.add_argument('--force', default=False, action='store_true')
    cloud_parser.add_argument('--name', type=str, required=True)
    cloud_parser.set_defaults(entrypoint=cloud)

    ova_parser = subparsers.add_parser('ova')
    ova_vmdk_arguments = ova_parser.add_mutually_exclusive_group(required=True)
    ova_vmdk_arguments.add_argument('--local-vmdk-name', type=pathlib.Path)
    ova_vmdk_arguments.add_argument('--remote-vmdk-name', type=str)
    ova_vmdk_arguments.add_argument('--gce-image-name', type=str,
                                    help='Full name of the gce image to create the ova from.')
    ova_vmdk_arguments.add_argument('--export-name', type=str, dest='name',
                                    help='Name of the export to generate ova from.')
    ova_output_arguments = ova_parser.add_mutually_exclusive_group(required=True)
    ova_output_arguments.add_argument('-o', '--output', type=str)
    ova_parser.set_defaults(entrypoint=ova)

    args = parser.parse_args()
    if args.teamcity_step:
        _teamcity_defaults_mutate_args(args)

    entrypoint = getattr(args, 'entrypoint', None)
    if entrypoint is None:
        parser.error('You must specify a subcommand, see --help')
    if args.entrypoint == installer and not args.branch and not args.commit_id:
        parser.error('One must specify atleast one of --branch and --commit-id')

    notify = create_notify(args)
    notify_failure = lambda *a: notify({'name': args.name, 'status': 'failure'})
    signal.signal(signal.SIGTERM, notify_failure)
    try:
        args.entrypoint(args, notify)
    except Exception:
        notify_failure()
        raise


def _teamcity_defaults_mutate_args(args):
    args.notify_exports = True
    args.disable_ssl_verification = True
    if args.teamcity_owner:
        args.piggyback_arguments.setdefault('owner', args.teamcity_owner)
    if args.teamcity_log:
        args.piggyback_arguments.setdefault(f'{args.teamcity_step}_log', args.teamcity_log)


def installer(args, notify):
    notify({'name': args.name, 'subcommand': 'installer', 'step': 'start', 'fork': args.fork, 'branch': args.branch})
    installer_packer_file = _SCRIPT_FOLDER.joinpath('axonius_generate_installer.json')
    output_installer_file = (args.output or pathlib.Path(f'axonius_{args.name}.py')).absolute()
    git_hash_file = (args.git_hash_file or pathlib.Path(f'axonius_{args.name}_git_hash.txt')).absolute()
    subprocess.run(['packer', 'build', '-timestamp-ui',
                    '-var', f'build_name={args.name}',
                    '-var', f'output_file={output_installer_file}',
                    '-var', f'git_hash_file={git_hash_file}',
                    '-var', f'fork={args.fork}',
                    '-var', f'branch={args.branch}', installer_packer_file],
                   check=True, cwd=_SCRIPT_FOLDER)
    notify({'name': args.name, 'subcommand': 'installer', 'step': 'finished', 'fork': args.fork,
            'branch': args.branch, 'installer_git_hash': git_hash_file.read_text()})


def cloud(args, notify):
    notify({'name': args.name, 'subcommand': 'cloud', 'step': 'start'})
    cloud_packer_file = _SCRIPT_FOLDER.joinpath('axonius_deploy.json')
    with tempfile.TemporaryDirectory() as temporary_directory:
        manifest_path = pathlib.Path(temporary_directory).joinpath(f'manifest-{args.name}.json').absolute()
        with local_installer_path(args) as installer_path:
            subprocess_arguments = ['packer', 'build', '-timestamp-ui',
                                    '-var', f'installer={installer_path}',
                                    '-var', f'name={args.name}',
                                    '-var', f'manifest_file={manifest_path}',
                                    '-var', f'ami_regions={args.ami_regions}']
            print(' '.join(subprocess_arguments))
            if args.except_:
                subprocess_arguments.append(f'-except={args.except_}')
            if args.only:
                subprocess_arguments.append(f'-only={args.only}')
            if args.force:
                subprocess_arguments.append('-force')
            subprocess_arguments.append(cloud_packer_file)
            subprocess.run(subprocess_arguments, check=True, cwd=_SCRIPT_FOLDER)
            with manifest_path.open() as manifest_file:
                manifest = json.load(manifest_file)

                # A bit of a hack, for GCE `artificat_id` is just the image name (which may not contain ':'), and for
                # AWS, it is in the format `region`:`ami_id`, so we want to take the last part only.
                def extract_id(s): return s.split(':')[-1]
                artifacts = {f'artifact.{build["builder_type"]}': extract_id(
                    build["artifact_id"]) for build in manifest['builds']}

            notify({'name': args.name, 'subcommand': 'cloud', **artifacts})
    notify({'name': args.name, 'subcommand': 'cloud', 'step': 'finished'})


def ova(args, notify):
    notify({'name': args.name, 'subcommand': 'ova', 'step': 'start'})
    with local_vmdk_path(args) as vmdk:
        with tempfile.TemporaryDirectory() as vmx_directory:
            vmx_path = pathlib.Path(vmx_directory).joinpath('axonius.vmx')
            _create_axonius_vmx(vmdk, vmx_path)
            subprocess.run(['ovftool', '--targetType=ova', vmx_path, args.output], check=True)
    notify({'name': args.name, 'subcommand': 'ova', 'step': 'finish'})


def s3_upload(args, notify):
    notify({'name': args.name, 'subcommand': 's3_upload', 'step': 'start'})
    s3_keys = {'installer': f'{args.name}/axonius_{args.name}.py',
               'ova': f'{args.name}/{args.name}/{args.name}_export.ova'}

    bucket = args.s3_bucket

    s3_client = boto3.client('s3')

    for key, s3_key in s3_keys.items():
        local_path = getattr(args, key)
        if local_path:
            try_upload_to_s3(s3_client, local_path, bucket, s3_key)
            url = urllib.parse.urljoin(f'http://{bucket}.s3-accelerate.amazonaws.com', s3_key)
            notify({'name': args.name, 'subcommand': 's3_upload', f's3_{key}': url})
    notify({'name': args.name, 'subcommand': 's3_upload', 'step': 'finished'})


def try_upload_to_s3(s3_client, local_path, bucket, key):
    key_exists = s3_client.list_objects_v2(Bucket=bucket, Prefix=key)['KeyCount']
    if key_exists:
        raise ExportFileAlreadyExists()

    s3_client.upload_file(Filename=str(local_path), Bucket=bucket, Key=key)


def create_notify(args):
    headers = {'X-Auth-Token': args.exports_server_token} if args.exports_server_token else None
    if args.notify_exports:
        def notify(data):
            params = dict(**data, **args.piggyback_arguments)
            print(f'Notify with params: {params}')
            try:
                requests.post(args.exports_notifications_url, json=params, headers=headers,
                              verify=not args.disable_ssl_verification).raise_for_status()
            except Exception:
                print(f'Notify failed with data: {params}')
                traceback.print_exc()

        return notify
    return lambda *args, **kwargs: None


@contextlib.contextmanager
def local_installer_path(args):
    if args.installer is not None:
        yield args.installer
    else:
        releases_bucket = args.s3_bucket
        axonius_releases_url_for_release = f'https://{releases_bucket}.s3.us-east-2.amazonaws.com/{{0}}/axonius_{{0}}.py'.format
        url = args.installer_url or axonius_releases_url_for_release(args.installer_s3_name)
        with tempfile.TemporaryDirectory() as temporary_directory:
            installer_name = pathlib.PosixPath(urllib.parse.urlparse(url).path).name
            temporary_local_installer = pathlib.Path(temporary_directory).joinpath(installer_name)
            subprocess.run(['curl', url, '-o', temporary_local_installer])
            yield temporary_local_installer


@contextlib.contextmanager
def remote_vmdk_path(args):
    if args.remote_vmdk_name:
        yield args.remote_vmdk_name

    else:
        gce_image_name = args.gce_image_name or 'axonius-' + args.name
        remote_vmdk_name = f'temp_vmdk_export_{hex(int(time.time() * 10))}' + gce_image_name + '.vmdk'
        vmdk_export_arguments = ['gcloud', 'compute', 'images', 'export', f'--destination-uri=gs://axonius-releases/{remote_vmdk_name}',
                                 '--export-format=vmdk', f'--image={gce_image_name}', '--network=axonius-office-vpc', '--subnet=private-subnet',
                                 '--log-location=gs://axonius-releases/logs', '--zone=us-east1-b']
        subprocess.run(vmdk_export_arguments, check=True)
        try:
            yield remote_vmdk_name
        finally:
            subprocess.run(['gsutil', 'rm', f'gs://axonius-releases/{remote_vmdk_name}'], check=True)


@contextlib.contextmanager
def local_vmdk_path(args):
    if args.local_vmdk_name:
        yield args.local_vmdk_name
    with tempfile.TemporaryDirectory() as temporary_directory:
        temporary_local_vmdk = pathlib.Path(temporary_directory).joinpath('vmdk.vmdk')
        with remote_vmdk_path(args) as remote_vmdk:
            subprocess.run(['gsutil', 'cp',
                            f'gs://axonius-releases/{remote_vmdk}', temporary_local_vmdk],
                           check=True)
        yield temporary_local_vmdk


def _create_axonius_vmx(vmdk_path, target_vmx_path):
    with target_vmx_path.open('w') as target_vmx:
        target_vmx.write(_get_axonius_vmx_data(vmdk_path))


def _get_axonius_vmx_data(vmdk_path):
    return f'''.encoding = "UTF-8"
bios.bootorder = "hdd,cdrom"
checkpoint.vmstate = ""
cleanshutdown = "TRUE"
config.version = "8"
displayname = "axonius-generated"
ehci.pcislotnumber = "-1"
ehci.present = "FALSE"
ethernet0.addresstype = "generated"
ethernet0.bsdname = "en0"
ethernet0.connectiontype = "bridged"
ethernet0.displayname = "Ethernet"
ethernet0.linkstatepropagation.enable = "FALSE"
ethernet0.pcislotnumber = "33"
ethernet0.present = "TRUE"
ethernet0.virtualdev = "e1000"
ethernet0.vnet = ""
ethernet0.wakeonpcktrcv = "FALSE"
extendedconfigfile = "axonius.vmxf"
floppy0.present = "FALSE"
guestos = "ubuntu-64"
hgfs.linkrootshare = "TRUE"
hgfs.maprootshare = "TRUE"
ide0:0.clientdevice = "TRUE"
ide0:0.devicetype = "cdrom-raw"
ide0:0.filename = "auto detect"
ide0:0.present = "TRUE"
isolation.tools.hgfs.disable = "FALSE"
memsize = "32768"
monitor.phys_bits_used = "40"
msg.autoanswer = "true"
numa.autosize.cookie = "80001"
numa.autosize.vcpu.maxpervirtualnode = "8"
numvcpus = "8"
nvme0.present = "FALSE"
nvram = "axonius.nvram"
parallel0.autodetect = "FALSE"
parallel0.bidirectional = ""
parallel0.filename = ""
parallel0.present = "FALSE"
parallel0.startconnected = "FALSE"
pcibridge0.pcislotnumber = "17"
pcibridge0.present = "TRUE"
pcibridge4.functions = "8"
pcibridge4.pcislotnumber = "21"
pcibridge4.present = "TRUE"
pcibridge4.virtualdev = "pcieRootPort"
pcibridge5.functions = "8"
pcibridge5.pcislotnumber = "22"
pcibridge5.present = "TRUE"
pcibridge5.virtualdev = "pcieRootPort"
pcibridge6.functions = "8"
pcibridge6.pcislotnumber = "23"
pcibridge6.present = "TRUE"
pcibridge6.virtualdev = "pcieRootPort"
pcibridge7.functions = "8"
pcibridge7.pcislotnumber = "24"
pcibridge7.present = "TRUE"
pcibridge7.virtualdev = "pcieRootPort"
powertype.poweroff = "soft"
powertype.poweron = "soft"
powertype.reset = "soft"
powertype.suspend = "soft"
proxyapps.publishtohost = "FALSE"
sata0.present = "FALSE"
scsi0.pcislotnumber = "16"
scsi0.present = "TRUE"
scsi0.virtualdev = "lsilogic"
scsi0:0.filename = "{vmdk_path.absolute()}"
scsi0:0.present = "TRUE"
scsi0:0.redo = ""
serial0.autodetect = "FALSE"
serial0.filename = ""
serial0.filetype = ""
serial0.pipe.endpoint = ""
serial0.present = "FALSE"
serial0.startconnected = "FALSE"
serial0.trynorxloss = ""
serial0.yieldonmsrread = ""
softpoweroff = "TRUE"
sound.autodetect = "TRUE"
sound.filename = "-1"
sound.present = "FALSE"
sound.startconnected = "FALSE"
svga.vramsize = "134217728"
tools.synctime = "TRUE"
tools.upgrade.policy = "upgradeAtPowerCycle"
usb.pcislotnumber = "-1"
usb.present = "FALSE"
virtualhw.productcompatibility = "hosted"
virtualhw.version = "9"
vmotion.checkpointfbsize = "134217728"'''


if __name__ == '__main__':
    main()
