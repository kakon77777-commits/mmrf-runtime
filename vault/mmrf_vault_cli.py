from __future__ import annotations
import argparse, json
from pathlib import Path
from mmrf_federated_vault import *


def main():
    p=argparse.ArgumentParser(prog='mmrf-vault')
    sub=p.add_subparsers(dest='command',required=True)
    g=sub.add_parser('generate-node')
    g.add_argument('--node-id',required=True); g.add_argument('--private-dir',required=True); g.add_argument('--public-dir',required=True)
    g.add_argument('--role',action='append',default=['vault']); g.add_argument('--measurement',action='append',required=True)
    a=sub.add_parser('attest'); a.add_argument('--descriptor',required=True); a.add_argument('--identity-private',required=True)
    a.add_argument('--measurement',required=True); a.add_argument('--config-hash',required=True); a.add_argument('--output',required=True)
    args=p.parse_args()
    if args.command=='generate-node':
        print(json.dumps(generate_node_material(node_id=args.node_id,private_dir=Path(args.private_dir),public_dir=Path(args.public_dir),roles=args.role,accepted_measurements=args.measurement),ensure_ascii=False,indent=2))
    elif args.command=='attest':
        d=json.loads(Path(args.descriptor).read_text()); result=issue_attestation(node_id=d['node_id'],descriptor=d,identity_private_path=Path(args.identity_private),measurement_sha256=args.measurement,config_sha256=args.config_hash)
        Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)); print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
