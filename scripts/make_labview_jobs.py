"""Write the jobs for scripts/capture-labview-xml.ps1 and the input files of its load jobs.

The values and inputs are hand-chosen (labelled as such); what LabVIEW writes and reads back
from them is the ground truth the tests check. Load inputs are written by lvxml itself or by
hand to probe how LabVIEW reads one spelling.

    python scripts/make_labview_jobs.py tests/fixtures/labview2026
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from lvxml import Cluster, Document, LVEnum, Node, dump, to_lv_xml, to_node

LV = Path(r"C:\Program Files\National Instruments\LabVIEW 2026")
CORE = LV / "ProjectTemplates" / "Source" / "Core"
CONT = CORE / "Continuous Measurement" / "Settings"
SINGLE = CORE / "Single Shot Measurement" / "subVIs"
SAVE_SINGLE = SINGLE / "Save Configuration Settings to XML.vi"
EXAMPLE = LV / "examples" / "File IO" / "XML" / "Flatten and Unflatten XML"
# The capture script expands %USERPROFILE%, so the jobs file names no user folder.
EXAMPLE_FILE = Path("%USERPROFILE%/Documents/LabVIEW Data/Example Flattened XML File.xml")
HEAD = "<?xml version='1.0' standalone='yes' ?>\r\n<LVData xmlns=\"http://www.ni.com/LVData\">\r\n"


def s(v: str) -> dict[str, object]:
    return {"t": "str", "v": v}


def cluster(*items: dict[str, object]) -> dict[str, object]:
    return {"t": "cluster", "v": list(items)}


def cont(text: str, signal: int, path: str) -> dict[str, object]:
    hw = cluster(s(text), {"t": "u16", "v": signal})
    return cluster(hw, cluster(s(path), {"t": "i32", "v": 0}))


def single(text: str, signal: int, stats: bool, behaviour: int) -> dict[str, object]:
    hw = cluster(s(text), {"t": "u16", "v": signal})
    return cluster(hw, cluster({"t": "bool", "v": stats}), {"t": "u16", "v": behaviour})


SAVES = {
    "save-cont-escapes": cont(
        "a&b<c>d \"q\" 'p' ]]> tab\tend cr\rlf\ncrlf\r\nx ", 1, "C:\\d\\a&b<c>.tdms"
    ),
    "save-cont-paths": cont("  spaces  ", 0, "\\\\server\\share\\run 1.tdms"),
    "save-cont-relative": cont("", 1, "sub\\file.tdms"),
    "save-cont-codepage": cont("caf\u00e9 \u20ac5", 0, "C:\\caf\u00e9.tdms"),
    "save-cont-control": cont("bell\x07 unit\x1f", 0, ""),
    "save-single-false": single("Dev1/ai0", 1, False, 2),
    "save-single-true": single("x", 0, True, 1),
}


def user_config(stats: str, behaviour: str, text: str = "Dev1/ai0") -> str:
    return (
        "<Cluster>\r\n<Name>User Configuration</Name>\r\n<NumElts>3</NumElts>\r\n"
        "<Cluster>\r\n<Name>Hardware Configuration</Name>\r\n<NumElts>2</NumElts>\r\n"
        "<String>\r\n<Name>HW Refnum &lt;Replace Me&gt;</Name>\r\n"
        f"<Val>{text}</Val>\r\n</String>\r\n"
        "<EW>\r\n<Name>Signal Type &lt;Replace Me&gt;</Name>\r\n<Choice>Sine Wave</Choice>\r\n"
        "<Choice>Square Wave</Choice>\r\n<Val>1</Val>\r\n</EW>\r\n</Cluster>\r\n"
        "<Cluster>\r\n<Name>Analysis Configuration</Name>\r\n<NumElts>1</NumElts>\r\n"
        f"<Boolean>\r\n<Name>Statistics</Name>\r\n<Val>{stats}</Val>\r\n</Boolean>\r\n</Cluster>\r\n"
        "<EW>\r\n<Name>New Data Behavior</Name>\r\n<Choice>Replace</Choice>\r\n"
        f"<Choice>Overlay</Choice>\r\n<Choice>Append</Choice>\r\n<Val>{behaviour}</Val>\r\n</EW>\r\n"
        "</Cluster>\r\n"
    )


VERSION_LINE = "<Version>26.3.1f1</Version>\r\n"


def wrap(body: str, head: str = HEAD) -> str:
    return f"{head}<Version>26.3.1f1</Version>\r\n{body}</LVData>"


LOADS_SINGLE = {
    "load-single-plain": wrap(user_config("0", "2")),
    "load-single-bare": user_config("1", "1"),
    "load-single-true-word": wrap(user_config("true", "0")),
    "load-single-true-upper": wrap(user_config("TRUE", "0")),
    "load-single-bool-two": wrap(user_config("2", "0")),
    "load-single-bool-space": wrap(user_config(" 1 ", "0")),
    "load-single-enum-past": wrap(user_config("1", "3")),
    "load-single-enum-negative": wrap(user_config("1", "-1")),
    "load-single-entities": wrap(user_config("1", "0", "&quot;&apos;&#13;&#x41;&#65;")),
    "load-single-crlf-text": wrap(user_config("1", "0", "a\r\nb\rc\nd")),
    "load-single-xsd-namespace": wrap(user_config("1", "0"), HEAD.replace('LVData"', 'labview"')),
    "load-single-no-namespace": wrap(
        user_config("1", "0"), HEAD.replace(' xmlns="http://www.ni.com/LVData"', "")
    ),
    "load-single-indented": wrap(user_config("1", "0").replace("\r\n<", "\n  <")),
    "load-single-numelts-wrong": wrap(user_config("1", "0").replace("<NumElts>3", "<NumElts>4")),
    "load-single-lone-amp": wrap(user_config("1", "0", "a & b &c; &#;")),
    "load-single-bool-minus": wrap(user_config("-1", "0")),
    "load-single-no-version": wrap(user_config("1", "0")).replace(VERSION_LINE, ""),
}


def lvxml_written() -> dict[str, str]:
    """The same configuration written by lvxml's own writers."""
    schema = Cluster(
        {
            "Hardware Configuration": Cluster(
                {
                    "HW Refnum <Replace Me>": "String",
                    "Signal Type <Replace Me>": LVEnum(("Sine Wave", "Square Wave")),
                }
            ),
            "Analysis Configuration": Cluster({"Statistics": "Boolean"}),
            "New Data Behavior": LVEnum(("Replace", "Overlay", "Append")),
        }
    )
    value = {
        "Hardware Configuration": {
            "HW Refnum <Replace Me>": 'a&b <"q">',
            "Signal Type <Replace Me>": 1,
        },
        "Analysis Configuration": {"Statistics": False},
        "New Data Behavior": "Append",
    }
    node = to_node(value, schema, name="User Configuration")
    return {
        "load-single-lvxml-to-lv-xml": to_lv_xml(value, schema, name="User Configuration"),
        "load-single-lvxml-dump": dump(Document((node,))),
        "load-single-lvxml-dump-version": dump(Document((Node("Version", val="26.3.1f1"), node))),
    }


def dbl_file(mean: str, low: str, high: str) -> str:
    body = "".join(
        f"<DBL>\r\n<Name>{n}</Name>\r\n<Val>{v}</Val>\r\n</DBL>\r\n"
        for n, v in (("", high), ("Min", low), ("mean", mean))
    )
    graph = (
        "<Cluster>\r\n<Name>Random Graph Data</Name>\r\n<NumElts>3</NumElts>\r\n"
        "<DBL>\r\n<Name>Initial X</Name>\r\n<Val>0</Val>\r\n</DBL>\r\n"
        "<DBL>\r\n<Name>Delta X</Name>\r\n<Val>0.25</Val>\r\n</DBL>\r\n"
        "<Array>\r\n<Name>Values</Name>\r\n<Dimsize>1</Dimsize>\r\n"
        "<DBL>\r\n<Name>Numeric</Name>\r\n<Val>1</Val>\r\n</DBL>\r\n</Array>\r\n</Cluster>\r\n"
    )
    return wrap(body + graph)


LOADS_DBL = {
    "load-dbl-shortest": dbl_file("0.1", "1e-07", "1e+300"),
    "load-dbl-nonfinite": dbl_file("NaN", "-Inf", "Inf"),
    "load-dbl-nonfinite-lower": dbl_file("nan", "-inf", "Infinity"),
    "load-dbl-exponent": dbl_file("1.5E3", "-2.5e-3", "5E+0"),
    "load-dbl-comma": dbl_file("1,5", "2", "3"),
    "load-dbl-space": dbl_file(" 2.5 ", "+1", ".5"),
    "load-dbl-negzero": dbl_file("-0.0", "123456789012345680.0", "5e-324"),
    "load-dbl-overflow": dbl_file("1e400", "-1e400", "1e-400"),
    "load-dbl-signed-nonfinite": dbl_file("+Inf", "+NaN", "-NaN"),
    "load-dbl-hex": dbl_file("0x10", "1.5.2", "1_0"),
    "load-dbl-empty": dbl_file("", "1e5", "INF"),
}


def job(name: str, kind: str, vi: Path, **fields: object) -> dict[str, object]:
    return {"name": name, "kind": kind, "vi": str(vi), **fields}


def main(folder: Path) -> None:
    inputs = folder / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    jobs: list[dict[str, object]] = []
    for name, value in SAVES.items():
        cont = "cont" in name
        vi = CONT / "Save Settings to XML.vi" if cont else SAVE_SINGLE
        control = "Settings" if cont else "User Configuration"
        target = str(vi.parent / "Settings.xml")
        jobs.append(job(name, "save", vi, control=control, value=value, file=target))
    loads = [(n, t, SINGLE) for n, t in {**LOADS_SINGLE, **lvxml_written()}.items()]
    loads += [(n, t, EXAMPLE) for n, t in LOADS_DBL.items()]
    for name, text, folder_vi in loads:
        (inputs / f"{name}.xml").write_bytes(text.encode("cp1252"))
        if folder_vi == SINGLE:
            target, outputs = SINGLE / "Settings.xml", ["User Configuration out", "error out"]
            vi = SINGLE / "Load Configuration Settings from XML.vi"
        else:
            target, outputs = EXAMPLE_FILE, ["Max", "Min", "Mean", "Retrieved XML"]
            vi = EXAMPLE / "Read from XML File and Unflatten Data.vi"
        jobs.append(
            job(name, "load", vi, input=f"inputs/{name}.xml", file=str(target), outputs=outputs)
        )
    for entry in jobs:
        entry["out"] = f"{entry['name']}.{'xml' if entry['kind'] == 'save' else 'json'}"
    (folder / "jobs.json").write_text(json.dumps(jobs, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
