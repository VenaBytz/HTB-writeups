#!/usr/bin/venv/bin/python3
import paramiko
import socket
import argparse
import logging

parser = argparse.ArgumentParser()
parser.add_argument("-f","--file",  required=True)
parser.add_argument("--host", required=True)
parser.add_argument("--port", default=22, type=int)
parser.add_argument("--key", required=True)
parser.add_argument("--passphrase", required=True)

args = parser.parse_args()

def try_ssh_connection(user):
  client = paramiko.SSHClient()
  client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
  pkey = paramiko.Ed25519Key.from_private_key_file(
    args.key,
    password=args.passphrase
  )
  try:
    client.connect(
      hostname=args.host,
      username=user,
      pkey=pkey,
      look_for_keys=False,
      allow_agent=False,
      timeout=5
    )
    stdin, stdout, stderr = client.exec_command('id')
    print(f"Valid user: {user}")
    print(stdout.read().decode())
    client.close()
    return True
  except paramiko.AuthenticationException:
    print(f"Invalid {user}")
  except Exception as e:
    print(f"Error with user {user}: {e}")
  return False

def main():
  with open (args.file, 'r') as f:
    for user in f:
      user=user.strip()
      if not user:
        continue
      try_ssh_connection(user)

if __name__ == "__main__":
    main()

