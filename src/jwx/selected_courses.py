from __future__ import annotations

from dataclasses import dataclass
from html import unescape
import re


_TR_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.DOTALL | re.IGNORECASE)
_CELL_RE = re.compile(
    r'<div\s+class="layui-table-cell[^"]*"[^>]*>(.*?)</div>',
    re.DOTALL | re.IGNORECASE,
)
_JX0404ID_DIV_RE = re.compile(r'id="div_(\d+)"', re.IGNORECASE)
_JX0404ID_JS_RE = re.compile(r"xstkOper\('?(?P<id>\d+)'?\)", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class SelectedCourse:
    jx0404id: str
    kch: str = ""
    kcmc: str = ""
    skfs: str = ""
    xf: str = ""
    kcxz: str = ""
    skls: str = ""
    sksj: str = ""
    skdd: str = ""
    xqmc: str = ""


def _clean_html_text(text: str) -> str:
    text = _TAG_RE.sub("", text)
    text = unescape(text)
    text = text.replace("\xa0", " ")
    return " ".join(text.split())


def parse_selected_courses(html: str) -> list[SelectedCourse]:
    courses: list[SelectedCourse] = []
    for tr in _TR_RE.findall(html):
        jx0404id = None
        m = _JX0404ID_DIV_RE.search(tr) or _JX0404ID_JS_RE.search(tr)
        if m:
            jx0404id = m.group(1)
        if not jx0404id:
            continue

        cells = [_clean_html_text(v) for v in _CELL_RE.findall(tr)]
        if len(cells) < 9:
            courses.append(SelectedCourse(jx0404id=str(jx0404id)))
            continue

        courses.append(
            SelectedCourse(
                jx0404id=str(jx0404id),
                kch=cells[0],
                kcmc=cells[1],
                skfs=cells[2],
                xf=cells[3],
                kcxz=cells[4],
                skls=cells[5],
                sksj=cells[6],
                skdd=cells[7],
                xqmc=cells[8],
            )
        )
    return courses
