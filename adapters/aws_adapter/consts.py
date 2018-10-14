EKS_YAML_FILE = 'apiVersion: v1\nclusters:\n- cluster:\n    server: {endpoint}\n    certificate-authority-data:' + \
                ' {ca_cert}\n  name: kubernetes\ncontexts:\n- context:\n' + \
                '    cluster: kubernetes\n    user: aws\n  name: aws\ncurrent-context: aws\n' + \
                'kind: Config\npreferences: {preferences}\nusers:\n- name: aws\n  user:\n    exec:\n' + \
                '      apiVersion: client.authentication.k8s.io/v1alpha1\n      command: aws-iam-authenticator\n' + \
                '      args:\n        - \"token\"\n        - \"-i\"\n        - \"{cluster_name}\"'
