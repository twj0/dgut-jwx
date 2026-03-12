from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


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

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "JwxClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def init_batch(self, batch_id: str, isallsc: str = "") -> None:
        referer = f"{self.base_url}/xsxk/newXsxkzx?jx0502zbid={batch_id}&isallsc={isallsc}"
        self._client.get(
            "/xsxk/newXsxkzx",
            params={"jx0502zbid": batch_id, "isallsc": isallsc},
        )
        self._client.get(
            "/xsxk/selectNum",
            params={"jx0502zbid": batch_id, "isallsc": isallsc},
            headers={"Referer": referer},
        )
        self._client.get("/xsxkkc/getGgxxk", headers={"Referer": referer})

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
        resp = self._client.post("/xsxkkc/xsxkGgxxkxk", params=params, data=data, headers=headers)
        resp.raise_for_status()
        return resp.json()

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
        resp = self._client.get(
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
        )
        resp.raise_for_status()
        return resp.json()

    def get_selected_courses_html(self) -> str:
        resp = self._client.get("/xsxkjg/comeXkjglb")
        resp.raise_for_status()
        return resp.text

