import argparse
import collections
import configparser
from datetime import datetime
# import grp, pwd
from fnmatch import fnmatch
import hashlib
from math import ceil
import os
import re
import sys
import zlib

import git_repository
import git_object

argparser = argparse.ArgumentParser()
argsubparsers = argparser.add_subparsers(title='Commands', dest='command')
argsubparsers.required = True

argsp = argsubparsers.add_parser('init', help='Initialize a new, empty repository')
argsp.add_argument('path', metavar='directory', nargs='?', default='.', 
                   help='Where to create the repository')

argsp = argsubparsers.add_parser('cat-file', help='Provide content of repo objects')
argsp.add_argument('type', metavar="type", choices=['blob', 'commit', 'tag', 'tree'],
                   help='Specify the Type')
argsp.add_argument('object', metavar='object', help='The object to display')

argsp = argsubparsers.add_parser('log', help='Display commit history')
argsp.add_argument('commit', default='HEAD', nargs='?', help='Commit to display')

def main(argv=sys.argv[1:]):
    args = argparser.parse_args(argv)
    match args.command:
        # case 'add'          : cmd_add(args)
        case 'cat-file'     : cmd_cat_file(args)
        # case 'check-ignore' : cmd_check_ignore(args)
        # case 'checkout'     : cmd_checkout(args)
        # case 'commit'       : cmd_commit(args)
        # case 'hash-object'  : cmd_hash_object(args)
        case 'init'         : cmd_init(args)
        case 'log'          : cmd_log(args)
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

def cmd_cat_file(args):
    repo = git_repository.repo_find()
    cat_file(repo, args.object, fmt=args.type.encode())
    
def cat_file(repo, obj, fmt=None):
    obj = git_object.object_read(repo, git_object.object_find(repo, obj, fmt=fmt))
    sys.stdout.buffer.write(obj.serialize())
    
def cmd_log(args):
    repo = git_repository.repo_find()
    
    print('digraph wyaglog{')
    print('  node[shape=rect]')
    log_graphviz(repo, git_object.object_find(repo, args.commit), set())
    print('}')
    
def log_graphviz(repo, sha, seen):
        if sha in seen:
            return
        seen.add(sha)
        
        commit = git_object.object_read(repo, sha)
        short_hash = sha[0:8]
        message = commit.kvlm[None].decode('utf8').strip()
        message = message.replace('\\', '\\\\')
        message = message.replace('\"', '\\\"')
        
        if '\n' in message:
            message = message[:message.index('\n')]
        
        print(f'  c_{sha} [label=\"{sha[0:7]}: {message}]')
        assert commit.fmt==b'commit'
        
        if not b'parent' in commit.kvlm.keys():
            return
        
        parents = commit.kvlm[b'parent']
        
        if type(parents) != list:
            parents = [parents]
        
        for p in parents:
            p = p.decode('ascii')
            print(f'c_{sha} -> c_{p}')
            log_graphviz(repo, p, seen)