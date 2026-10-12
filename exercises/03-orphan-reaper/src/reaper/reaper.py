import botocore
from botocore import client as boto_client, config
from boto3 import client as boto3_clients

class Reaper:
    def __init__(self, policy):
        self.client = boto3_clients('ec2',
            config=config.Config(signature_version=botocore.UNSIGNED, region_name='ap-southeast-1')
        )
        self.policy = policy

    def reap(self):
        max_age_days, exclusive_tag, dry_run = self.policy.parse()
        self.client.get_paginator()
        pass



