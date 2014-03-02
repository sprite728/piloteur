smarthome-deployment
====================

Deployment scripts for SmartHome services.

# Usage

Install *ansbile*: `[sudo] pip install ansible` and check that `ansible-playbook` got added to your `$PATH`.

NOTE: these playbooks have been tested with passwordless keyfile access to both GitHub and EC2. They might get stuck with password prompts. Consider using `ssh-agent`.

## EC2

First you will need to get a **ACCESS_KEY** and a **SECRET_KEY** for your account and set them as environment variables.

Ansible is a bit quirky and requires two different names for each values.

My suggestion is to create a `~/.aws/env.sh` file like this

```
export AWS_ACCESS_KEY=XXXXXXXXXXXXXXXXXXXX
export AWS_ACCESS_KEY_ID=XXXXXXXXXXXXXXXXXXXX
export AWS_SECRET_KEY=YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY
export AWS_SECRET_ACCESS_KEY=YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY
export EC2_REGION=us-east-1
```

and import it with `. ~/.aws/env.sh`.

Then, you will need to `[sudo] pip install boto`.

### Spinning up a new instance

To launch a new instance first create an appropriate keypair and security group from the AWS Console.

Then, launch a new instance with

```
ansible-playbook -i inventory.ini new_ec2.yml --extra-vars "keypair_name=KEYPAIR security_group=GROUP"
```

This will create a new *t1.micro* instance in *us-east-1*, fully configured, it will start syncing immediately.

You can login as the user `admin` with the keypair you specified.

### Updating all the hub instances

For this you will need the EC2 inventory plugin.

Download it as follows

```
wget https://raw.github.com/ansible/ansible/devel/plugins/inventory/ec2.ini
wget https://raw.github.com/ansible/ansible/devel/plugins/inventory/ec2.py
chmod +x ec2.py
```

Then simply run

```
ansible-playbook -i ec2.py update_ec2.yml
```

This will get all the tagged hub instances in your account to the current version of the playbook.