"""Fetch comments for a JD product.

This script paginates the JD comment API to retrieve a target number of
comments and saves them to a JSON file. Network access may be blocked in
some environments; handle errors accordingly.
"""

import argparse
import json
import sys
import time
from typing import Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_PRODUCT_ID = "10163229865949"
DEFAULT_TARGET_COUNT = 200
DEFAULT_PAGE_SIZE = 20
DEFAULT_SLEEP_SECONDS = 0.5
DEFAULT_TIMEOUT = 10


def build_headers(product_id: str) -> Dict[str, str]:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Referer": f"https://item.jd.com/{product_id}.html",
    }


def fetch_page(product_id: str, page: int, page_size: int, *, timeout: int) -> List[Dict]:
    base_url = "https://club.jd.com/comment/productPageComments.action"
    params = {
        "productId": product_id,
        "score": 0,
        "sortType": 5,
        "page": page,
        "pageSize": page_size,
        "isShadowSku": 0,
        "fold": 1,
    }
    url = f"{base_url}?{urlencode(params)}"

    request = Request(url, headers=build_headers(product_id))
    with urlopen(request, timeout=timeout) as response:
        data = response.read().decode("utf-8")

    try:
        payload = json.loads(data)
    except json.JSONDecodeError:
        raise ValueError("无法解析返回的 JSON 数据")

    comments = payload.get("comments")
    if not isinstance(comments, list):
        raise ValueError("响应中缺少评论数据")

    return comments


def collect_comments(
    product_id: str,
    target_count: int,
    page_size: int,
    *,
    sleep_seconds: float,
    timeout: int,
) -> List[Dict]:
    comments: List[Dict] = []
    page = 0

    while len(comments) < target_count:
        try:
            page_comments = fetch_page(product_id, page, page_size, timeout=timeout)
        except (HTTPError, URLError, ValueError) as exc:
            print(f"第 {page} 页获取失败：{exc}", file=sys.stderr)
            break

        if not page_comments:
            print("没有更多评论，提前结束。")
            break

        comments.extend(page_comments)
        print(f"已获取第 {page} 页，累计 {len(comments)} 条评论。")
        page += 1
        time.sleep(sleep_seconds)

    return comments[:target_count]


def save_comments(comments: List[Dict], output_file: str) -> None:
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(comments, f, ensure_ascii=False, indent=2)
    print(f"已保存 {len(comments)} 条评论到 {output_file}")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="抓取指定京东商品的评论并保存为 JSON 文件")
    parser.add_argument("--product-id", default=DEFAULT_PRODUCT_ID, help="商品 ID，例如 10163229865949")
    parser.add_argument("--target-count", type=int, default=DEFAULT_TARGET_COUNT, help="需要抓取的评论数量")
    parser.add_argument("--page-size", type=int, default=DEFAULT_PAGE_SIZE, help="每页请求的评论数量")
    parser.add_argument("--sleep", type=float, default=DEFAULT_SLEEP_SECONDS, help="每次请求后的休眠秒数")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="请求超时时间（秒）")
    parser.add_argument(
        "--output",
        default=None,
        help="输出文件名，默认生成 comments_<product_id>.json",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)
    output_file = args.output or f"comments_{args.product_id}.json"

    comments = collect_comments(
        args.product_id,
        args.target_count,
        args.page_size,
        sleep_seconds=args.sleep,
        timeout=args.timeout,
    )

    if not comments:
        print("未能获取到评论，可能是网络限制或接口变化。", file=sys.stderr)
        return

    save_comments(comments, output_file)


if __name__ == "__main__":
    main()
