#!/usr/bin/env python3
import subprocess
import tarfile
from pathlib import Path
import sys

# pylint: disable=too-many-branches


def main():
    file_name = sys.argv[1] if len(sys.argv) > 1 else 'configuration_script.tar'
    working_dir = Path().home()
    file_path = Path(working_dir, 'cortex/uploaded_files/', file_name)
    new_file_path = Path(working_dir, file_name)
    try:
        # get the uploaded tar file from fix location
        file_path.replace(new_file_path)
        # check tar file for original content
        all_files_valid = True
        with tarfile.open(new_file_path, 'r') as file:
            for filename in ['axcs_job.axonius', 'axonius.sig']:
                try:
                    _ = file.getmember(filename)
                except KeyError:
                    all_files_valid = False
            if all_files_valid:
                file.extract('axcs_job.axonius')
                file.extract('axonius.sig')
                print('axonius tar extracted')

        if all_files_valid:
            # decrypting and validate files
            encrypted_script = Path(working_dir, 'axcs_job.axonius')
            signature_file = Path(working_dir, 'axonius.sig')
            verify_configuration_script = Path(working_dir, 'cortex/devops/scripts/offline/', 'verify_configuration.py')
            try:
                verify_configuration_script.chmod(0o755)
                verify_command = subprocess.run([str(verify_configuration_script),
                                                 '--file', str(encrypted_script),
                                                 '--signature', str(signature_file)])

                if verify_command.returncode == 0:
                    runnable_script = Path(working_dir, 'axonius_configuration')
                    try:
                        print('axonius script valid')
                        runnable_script.chmod(0o755)
                        subprocess.run(['sudo', 'bash', '-c', str(runnable_script)])
                        print('axonius script done')
                    except Exception as e:
                        print(f'axonius script error:{e}')
                    finally:
                        if runnable_script.exists():
                            runnable_script.unlink()
                else:
                    print('axonius script not valid')
            except Exception as e:
                print(f'configuration verification error: {e}')
            finally:
                try:
                    if encrypted_script.exists():
                        encrypted_script.unlink()
                except Exception as e:
                    print(f'Failed removing encrypted script: {e}')
                try:
                    if signature_file.exists():
                        signature_file.unlink()
                except Exception as e:
                    print(f'Failed removing signature file: {e}')
                try:
                    verify_configuration_script.chmod(0o644)
                except Exception as e:
                    print(f'Failed unchmoding verify_configuration file: {e}')

        else:
            print('not original axonius tar')
    finally:
        # this script will self destruct in ..
        # this file is copied to the host home folder, can't run from cortex folder
        # so it'll delete itself after execution if it is not the original file and the tar file
        if new_file_path.exists():
            new_file_path.unlink()
        if Path(__file__).name != 'execute_configuration_script.py':
            Path(__file__).unlink()


if __name__ == '__main__':
    main()
