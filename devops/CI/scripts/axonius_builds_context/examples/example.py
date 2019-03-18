import sys
sys.path.append(".")
from axoniusbuilds import Builds


# Readonly credentials to our repository
AWS_ACCESS_KEY_ID = ""
AWS_SECRET_ACCESS_KEY = ""


def initialize_environment(instance):
    """
    Gets an Instance object and initializes the needed environment for dockers:
    * Login to axonius ec2 container registry to be able to pull dockers

    Assumes:
    * Its an axonius image:
        * has awscli installed
        * has docker-ce installed
        * has python3

    :param instance: The instance
    :return: True.
    :exception: If anything bad happens.
    """
    stdout, stderr = instance.ssh(
        "mkdir -p ~/.aws && printf \"[default]\\nregion = us-east-2\\n\">~/.aws/config && "
        "printf \"[default]\\naws_access_key_id = {0}\\n"
        "aws_secret_access_key = {1}\\n\">~/.aws/credentials && chmod 600 ~/.aws/* &&"
        "sudo `/home/ubuntu/.local/bin/aws ecr get-login --no-include-email --region us-east-2`\n"
        .format(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    )
    assert "Login Succeeded" in stdout


def main():

    with Builds.Instances.new() as i:
        initialize_environment(i)


if __name__ == '__main__':
    sys.exit(main())
