from enum import Enum

import buildscloud


class BuildsComputeType(Enum):
    AWS = buildscloud.compute.aws_compute_manager.AWSComputeManager
    GCP = buildscloud.compute.gcp_compute_manager.GCPComputeManager


class BuildsStorageType(Enum):
    AWS = buildscloud.storage.aws_storage_manager.AWSStorageManager
    GCP = buildscloud.storage.gcp_storage_manager.GCPStorageManager


class BuildsDNSType(Enum):
    CLOUDFLARE = buildscloud.dns.cloudflare_dns_manager.CloudFlareDNSManager
