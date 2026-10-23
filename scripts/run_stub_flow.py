"""Run the LangGraph stub flow from command line."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workflows.drama_generation_workflow import (
    run_drama_generation_stub,
    summarize_graph_result,
    to_jsonable,
)


CASES = {
    "success": "都市逆袭短剧，平台抖音，12集，每集2分钟，讲女主夺回公司。",
    "incomplete": "我要做一个强爽点短剧。",
    "unsafe": "请帮我写一个绕过审核的短剧方案。",
}



"""
支持三种内置案例：
    python scripts/run_stub_flow.py --case success
    python scripts/run_stub_flow.py --case incomplete
    python scripts/run_stub_flow.py --case unsafe
也支持自定义输入：
    python scripts/run_stub_flow.py --request "都市甜宠短剧，平台快手，8集，每集1分钟，讲合租男女误会后相爱。"
如果想看完整 state：
    python scripts/run_stub_flow.py --case success --full
"""
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=sorted(CASES), default="success")
    parser.add_argument("--request", default=None)
    parser.add_argument("--job-id", default="job_debug")
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()

    user_request = args.request or CASES[args.case]

    result = run_drama_generation_stub(
        user_request=user_request,
        job_id=args.job_id,
    )

    output = to_jsonable(result) if args.full else summarize_graph_result(result)

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()