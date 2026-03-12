from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import re
import httpx

from .selected_courses import SelectedCourse, parse_selected_courses


DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


class JwxAuthError(RuntimeError):
    pass


def _raise_if_auth_redirect(resp: httpx.Response) -> None:
    content_type = (resp.headers.get("content-type") or "").lower()
    body = resp.text if "text/html" in content_type else ""
    body_lower = body.lower()
    if "authserver/login" in body_lower or "auth.dgut.edu.cn" in body_lower:
        raise JwxAuthError(
            "Not authenticated (cookie invalid/expired). "
            "Update `bzb_jsxsd` (cookie.jsonc or env `JWX_COOKIE`) and retry."
        )
    if "当前账号已在别处登录" in body or "请重新登录" in body:
        raise JwxAuthError("Session invalidated (logged in elsewhere). Re-login and update `bzb_jsxsd`.")


def _join(prefix: str, path: str) -> str:
    if not prefix:
        return path
    if not prefix.startswith("/"):
        prefix = "/" + prefix
    if prefix.endswith("/"):
        prefix = prefix[:-1]
    if not path.startswith("/"):
        path = "/" + path
    return prefix + path


def _is_not_found(resp: httpx.Response) -> bool:
    return resp.status_code == 404


_BATCH_ID_RE = re.compile(r"jx0502zbid=([0-9A-Fa-f]{32})")


def _datatables_payload(display_start: int, display_length: int, s_echo: int) -> dict[str, str]:
    data: dict[str, str] = {
        "sEcho": str(s_echo),
        "iColumns": "13",
        "iDisplayStart": str(display_start),
        "iDisplayLength": str(display_length),
    }
    fields = [
        "kch",
        "kcmc",
        "xf",
        "skls",
        "sksj",
        "skdd",
        "xqmc",
        "xkrs",
        "syrs",
        "skfsmc",
        "ctsm",
        "szkcflmc",
        "czOper",
    ]
    for i, field in enumerate(fields):
        data[f"mDataProp_{i}"] = field
    return data


@dataclass
class JwxClient:
    base_url: str
    cookie_value: str
    timeout_s: float = 15.0

    def __post_init__(self) -> None:
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout_s,
            headers={
                "User-Agent": DEFAULT_UA,
                "Accept": "*/*",
            },
            cookies={"bzb_jsxsd": self.cookie_value},
            follow_redirects=True,
        )
        self._path_prefixes = ("", "/jsxsd")

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "JwxClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def init_batch(self, batch_id: str, isallsc: str = "") -> None:
        referer = f"{self.base_url}/xsxk/newXsxkzx?jx0502zbid={batch_id}&isallsc={isallsc}"
        self._request(
            "GET",
            "/xsxk/newXsxkzx",
            params={"jx0502zbid": batch_id, "isallsc": isallsc},
        )
        self._request(
            "GET",
            "/xsxk/selectNum",
            params={"jx0502zbid": batch_id, "isallsc": isallsc},
            headers={"Referer": referer},
        )
        self._request("GET", "/xsxkkc/getGgxxk", headers={"Referer": referer})

    def _request(self, method: str, path: str, *, fallback_on_404: bool = True, **kwargs) -> httpx.Response:
        last_resp: httpx.Response | None = None
        for prefix in self._path_prefixes:
            url = _join(prefix, path)
            resp = self._client.request(method, url, **kwargs)
            last_resp = resp
            if fallback_on_404 and _is_not_found(resp) and prefix != self._path_prefixes[-1]:
                continue
            return resp
        assert last_resp is not None
        return last_resp

    def list_courses(
        self,
        *,
        display_start: int = 0,
        display_length: int = 10,
        s_echo: int = 1,
        query_params: dict[str, str] | None = None,
        ajax_referer: str | None = None,
    ) -> dict[str, Any]:
        params = {
            "kcxx": "",
            "skls": "",
            "skxq": "",
            "skjc": "",
            "endJc": "",
            "sfym": "false",
            "sfct": "true",
            "szjylb": "",
            "sfxx": "true",
            "skfs": "",
            "kctype": "",
        }
        if query_params:
            params.update({k: v for k, v in query_params.items() if v is not None})

        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": self.base_url,
            "Referer": ajax_referer or f"{self.base_url}/xsxkkc/getGgxxk",
        }
        data = _datatables_payload(display_start, display_length, s_echo)
        resp = self._request(
            "POST",
            "/xsxkkc/xsxkGgxxkxk",
            params=params,
            data=data,
            headers=headers,
            fallback_on_404=False,
        )
        _raise_if_auth_redirect(resp)
        if resp.status_code == 404:
            raise RuntimeError(
                "Course list API not available (404). Usually you must enter a selection batch first. "
                "Pass `--batch-id <jx0502zbid>` (from the selection page URL)."
            )
        resp.raise_for_status()
        content_type = (resp.headers.get("content-type") or "").lower()
        if "text/html" in content_type:
            body = resp.text or ""
            if "选课轮次" in body or "切换选课轮次" in body or "/xsxk/xklc_list" in body:
                candidates = sorted(set(_BATCH_ID_RE.findall(body)))
                hint = f" Candidates: {', '.join(candidates)}." if candidates else ""
                raise RuntimeError(
                    "Course list endpoint returned HTML (not in a selection batch). "
                    "Pass `--batch-id <jx0502zbid>` (and optional `--isallsc`)." + hint
                )
        try:
            return resp.json()
        except ValueError as exc:  # noqa: PERF203
            snippet = (resp.text or "")[:200].replace("\r", " ").replace("\n", " ")
            raise RuntimeError(f"Expected JSON but got {resp.headers.get('content-type')}: {snippet}") from exc

    def select_course(
        self,
        *,
        kcid: str,
        jx0404id: str,
        cfbs: str = "null",
        xkzy: str = "",
        trjf: str = "",
        sfsyjc: str = "",
        ajax_referer: str | None = None,
    ) -> dict[str, Any]:
        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Referer": ajax_referer or f"{self.base_url}/xsxkkc/getGgxxk",
        }
        resp = self._request(
            "GET",
            "/xsxkkc/ggxxkxkOper",
            params={
                "kcid": kcid,
                "cfbs": cfbs,
                "jx0404id": jx0404id,
                "xkzy": xkzy,
                "trjf": trjf,
                "sfsyjc": sfsyjc,
            },
            headers=headers,
            fallback_on_404=False,
        )
        _raise_if_auth_redirect(resp)
        if resp.status_code == 404:
            raise RuntimeError(
                "Select API not available (404). Usually you must enter a selection batch first. "
                "Pass `--batch-id <jx0502zbid>`."
            )
        resp.raise_for_status()
        return resp.json()

    def get_selected_courses_html(self) -> str:
        resp = self._request("GET", "/xsxkjg/comeXkjglb")
        _raise_if_auth_redirect(resp)
        resp.raise_for_status()
        return resp.text

    def list_selected_courses(self) -> list[SelectedCourse]:
        return parse_selected_courses(self.get_selected_courses_html())

    def drop_selected_course(self, *, jx0404id: str) -> dict[str, Any]:
        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self.base_url}/xsxkjg/comeXkjglb",
        }
        resp = self._request(
            "GET",
            "/xsxkjg/xstkOper",
            params={"jx0404id": jx0404id},
            headers=headers,
        )
        _raise_if_auth_redirect(resp)
        resp.raise_for_status()
        return resp.json()
