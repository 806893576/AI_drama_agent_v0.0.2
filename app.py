"""项目启动入口。"""

from __future__ import annotations

import argparse
import json

import uvicorn

from api.server import app
from graph.execution_options import ExecutionOptions
from workflows.generation_workflow import run_generation


def main() -> None:
    parser = argparse.ArgumentParser(description="Drama Agent Platform")
    parser.add_argument("--serve", action="store_true", help="启动 HTTP API 服务")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--request", help="直接运行一次短剧生成")
    parser.add_argument("--fast-draft", action="store_true", help="跳过审核类节点，快速生成草案")
    args = parser.parse_args()

    if args.serve:
        uvicorn.run(app, host=args.host, port=args.port)
        return

    if args.request:
        options = ExecutionOptions.fast_draft() if args.fast_draft else None
        result = run_generation(args.request, execution_options=options)
        print(json.dumps(result.summary, ensure_ascii=False, indent=2))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
