#!/usr/bin/env python3
from getpass import getpass
from werkzeug.security import generate_password_hash

def main():
    pwd = getpass('Enter password to hash: ')
    if not pwd:
        print('No password entered. Aborting.')
        return
    print(generate_password_hash(pwd))

if __name__ == '__main__':
    main()
