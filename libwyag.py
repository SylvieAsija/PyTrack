import argparse
import collections
import configparser
from datetime import datetime
import grp, pwd
from fnmatch import fnmatch
import hashlib
from math import ceil
import os
import re
import sys
import zlib

import git_repository

argparser = argparse.ArgumentParser()
argsubparsers = argparser.add_subparsers(title='Commands', dest='command')
argsubparsers.required = True
argsp = argsubparsers.add_parser('init', help='Initialize a new, empty repository')
argsp.add_argument('path', metavar='directory', nargs='?', default='.', help='Where to create the repository')
    
def main(argv=sys.argv[1:]):
    args = argparser.parse_args(argv)
    match args.command:
        # case 'add'          : cmd_add(args)
        # case 'cat-file'     : cmd_cat_file(args)
        # case 'check-ignore' : cmd_check_ignore(args)
        # case 'checkout'     : cmd_checkout(args)
        # case 'commit'       : cmd_commit(args)
        # case 'hash-object'  : cmd_hash_object(args)
        case 'init'         : cmd_init(args)
        # case 'log'          : cmd_log(args)
        # case 'ls-files'     : cmd_ls_files(args)
        # case 'ls-tree'      : cmd_ls_tree(args)
        # case 'rev-parse'    : cmd_rev_parse(args)
        # case 'rm'           : cmd_rm(args)
        # case 'show-ref'     : cmd_show_ref(args)
        # case 'status'       : cmd_status(args)
        # case 'tag'          : cmd_tag(args)
        case _              : print('Invalid Command')
        
def cmd_init(args):
    git_repository.repo_create(args.path)