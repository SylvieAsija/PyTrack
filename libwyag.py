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

argsp = argsubparsers.add_parser('ls-tree', help='Print a tree object')
argsp.add_argument('-r', dest='recursive', action='store_true', help='Recurse into sub trees')
argsp.add_argument('tree', help='A tree object')

argps = argsubparsers.add_parser('checkout', help='Checkout a commit')
argsp.add_argument('commit', help='The commit or tree to checkout')
argsp.add_argument('path', help='The empty directory to checkout on')


def main(argv=sys.argv[1:]):
    args = argparser.parse_args(argv)
    match args.command:
        # case 'add'          : cmd_add(args)
        case 'cat-file'     : cmd_cat_file(args)
        # case 'check-ignore' : cmd_check_ignore(args)
        case 'checkout'     : cmd_checkout(args)
        # case 'commit'       : cmd_commit(args)
        # case 'hash-object'  : cmd_hash_object(args)
        case 'init'         : cmd_init(args)
        case 'log'          : cmd_log(args)
        # case 'ls-files'     : cmd_ls_files(args)
        case 'ls-tree'      : cmd_ls_tree(args)
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

def cmd_ls_tree(args):
    repo = git_repository.repo_find()
    ls_tree(repo, args.tree, args.recursive)
    
def ls_tree(repo, ref, recursive=None, prefix=''):
    sha = git_object.object_find(repo, ref, fmt=b'tree')
    obj = git_object.object_read(repo, sha)
    for item in obj.items():
        if len(item.mode) == 5:
            type = item.mode[0:1]
        else:
            type = item.mode[0:2]
        
        match type:
            case b'04'  : type = 'tree'
            case b'10'  : type = 'blob'
            case b'12'  : type = 'blob'
            case b'16'  : type = 'commit'
            case _      : raise Exception(f'Weird tree leaf mode {item.mode}')
        
        if not (recursive and type=='tree'):
            print(f'{'0' * (6 - len(item.mode)) + item.mode.decode('ascii')} {type} {item.sha}\t{os.path.join(prefix, item.path)}')
        else:
            ls_tree(repo, item.sha, recursive, os.path.join(prefix, item.path))

def cmd_checkout(args):
    repo = git_repository.repo_find()
    
    obj = git_object.object_read(repo, git_object.object_find(repo, args.commit))
    
    if obj.fmt == b'commit':
        obj = git_object.object_read(repo, obj.kvlm[b'tree'].decode('ascee'))
        
    if os.path.exists(args.path):
        if not os.path.isdir(args.path):
            raise Exception(f'Not a directory {args.path}')
        if os.listdir(args.path):
            raise Exception(f'Directory not empty {args.path}')
    else:
        os.makedirs(args.path)
    
    tree_checkout(repo, obj, os.path.realpath(args.path))

def tree_checkout(repo, tree, path):
    for item in tree.items:
        obj = git_object.object_read(repo, item.sha)
        dest = os.path.join(path, item.path)
        
        if obj.fmt == b'tree':
            os.mkdir(dest)
            tree_checkout(repo, obj, dest)
        elif obj.fmt == b'blob':
            with open(dest, 'wb') as f:
                f.write(obj.blobdata)