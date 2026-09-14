"""Build the offline, dependency-free HTML manuals for core NanoDevice functions."""

from collections import defaultdict
from html import escape
import os
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
TOOLKIT = HERE.parent
ROOT = TOOLKIT.parents[2]
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path[:0] = [str(TOOLKIT), str(ROOT)]

import nanodevice_toolkit as gui  # noqa: E402
from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402


TOOLS = [
    gui.NANODEVICE_FET_TOOL,
    gui.GDSFACTORY_TEXT_TOOL,
    gui.MOSFET_COMPONENT_TOOL,
    gui.MOSFET_PCELL_TOOL,
    gui.WOODPILE_COMPONENT_TOOL,
    gui.CROSSBAR_COMPONENT_TOOL,
    gui.HEMT_COMPONENT_TOOL,
    gui.HALL_COMPONENT_TOOL,
    gui.TLM_COMPONENT_TOOL,
    gui.SENSE_LATCH_ARRAY_TOOL,
    gui.WRITE_READ_ARRAY_TOOL,
]

INFO = {
    "nanodevice_fet": ("交指 FET", "用交错的源漏指、电极母线与独立栅极构成可快速扫描尺寸的 FET。", ["channel_width", "finger_width", "finger_spacing", "gate_margin_x"]),
    "gdsfactory_text": ("版图文字", "将文字转换为所选工艺层上的真实多边形，并控制字体、字号、字距和锚点。", ["size_um", "spacing_um", "justify", "anchor"]),
    "mosfet_component": ("MOSFET 静态结构", "生成四端 MOSFET、介质包围、扇出 Pad 和可选套刻标记；插入后为普通几何。", ["channel_width", "channel_length", "gate_overlap", "outer_pad_size"]),
    "mosfet_pcell": ("MOSFET PCell", "结构与 MOSFET 相同，但以可再次编辑参数的 KLayout PCell 实例插入。", ["channel_width", "channel_length", "gate_overlap", "outer_pad_size"]),
    "woodpile_component": ("Woodpile 十字器件", "一条横向背栅与一条纵向顶栅交叉，通过落脚区、梯形扇出和外部 Pad 引出。", ["bottom_bar_width", "top_bar_width", "fanout_length", "outer_pad_width"]),
    "crossbar_component": ("Cross Bar 阵列", "共享横向背栅行与纵向顶栅列，在每个交点形成器件并以 N+M 个 Pad 引出。", ["x_num", "y_num", "x_pitch", "horizontal_bar_width"]),
    "hemt_component": ("HEMT 器件", "支持 S-G-D 与 S-G-D-G-S 核心、Mesa、介质、粗细 EBL 分层扇出及对准标记。", ["gate_length", "source_gate_spacing", "gate_drain_spacing", "mesa_width"]),
    "hall_component": ("Hall Bar", "在电流主通道两侧布置成对电压探针，并可生成细/粗 EBL 过渡和完整扇出。", ["bar_length", "bar_width", "v_contact_pairs", "dist_v"]),
    "tlm_component": ("TLM", "生成一组具有线性、对数、指数或倒数间距的电极，用于提取接触与片电阻。", ["num_electrodes", "min_spacing", "max_spacing", "channel_width"]),
    "sense_latch_array": ("Sense / Latch 阵列", "将感测 FET 与锁存 FET 组合为像素，再扩展为方形或行列可独立设置的阵列。", ["rows", "cols", "pixel_size", "fet_gap"]),
    "write_read_array": ("Write / Read 阵列", "将写入与读取晶体管、耦合 Via、门线和共享接触组合成可扇出的像素阵列。", ["rows", "cols", "pixel_size", "coupling_via_size"]),
}

EN_INFO = {
    "nanodevice_fet": "An interdigitated source/drain FET with independent channel, finger, bus, pad, and gate controls.",
    "gdsfactory_text": "Converts text into real polygons on the selected process layer with font, size, spacing, alignment, and anchor controls.",
    "mosfet_component": "Creates a static four-terminal MOSFET with dielectric enclosure, fanout pads, labels, and optional alignment marks.",
    "mosfet_pcell": "Creates the same four-terminal MOSFET as an editable KLayout PCell instance.",
    "woodpile_component": "Crosses a horizontal bottom-gate bar and vertical top-gate bar, each connected through a landing, taper, and probe pad.",
    "crossbar_component": "Creates shared horizontal bottom-gate rows and vertical top-gate columns with N x M crossings and only N + M pads.",
    "hemt_component": "Creates S-G-D or S-G-D-G-S HEMTs with mesa, dielectric, split fine/coarse EBL fanout, and alignment marks.",
    "hall_component": "Places paired voltage probes along a current channel with optional split-EBL transitions and full pad fanout.",
    "tlm_component": "Creates electrodes with linear, logarithmic, exponential, or inverse spacing for contact and sheet-resistance extraction.",
    "sense_latch_array": "Combines sense and latch FETs into a pixel and expands it into a square or independently sized row-column array.",
    "write_read_array": "Combines write/read transistors, coupling vias, gate lines, shared contacts, and array fanout.",
}


def _bi(zh, en):
    return '<span class="lang zh">{}</span><span class="lang en">{}</span>'.format(escape(zh), escape(en))


def _scene(key):
    common = 'stroke="#263442" stroke-width="3" vector-effect="non-scaling-stroke"'
    if key == "nanodevice_fet":
        fingers = "".join(f'<rect x="{270+i*38}" y="{185 if i%2==0 else 260}" width="18" height="150" fill="#ef6473"/>' for i in range(7))
        return f'<rect x="245" y="180" width="300" height="240" rx="10" fill="#f0ca53"/>{fingers}<rect x="235" y="155" width="320" height="30" fill="#ef6473"/><rect x="235" y="415" width="320" height="30" fill="#ef6473"/><rect x="585" y="255" width="90" height="90" rx="8" fill="#38c9a5"/><path d="M555 300H585" {common}/>'
    if key == "gdsfactory_text":
        return f'<path d="M300 420L405 170L510 420M345 320H465" fill="none" stroke="#43a9e6" stroke-width="32"/><rect x="250" y="145" width="310" height="310" rx="8" fill="none" {common} stroke-dasharray="8 8"/><circle cx="250" cy="455" r="8" fill="#ef6473"/>'
    if key.startswith("mosfet"):
        return '<rect x="335" y="245" width="130" height="110" rx="10" fill="#f0ca53"/><path d="M160 220H300L335 260V340L300 380H160Z" fill="#ef6473"/><path d="M640 220H500L465 260V340L500 380H640Z" fill="#ef6473"/><path d="M330 100H470L445 240H355Z" fill="#38c9a5"/><path d="M330 500H470L445 360H355Z" fill="#43a9e6"/><rect x="315" y="225" width="170" height="150" rx="12" fill="none" stroke="#ad72cf" stroke-width="12"/>'
    if key == "woodpile_component":
        return '<rect x="365" y="120" width="70" height="360" fill="#38c9a5"/><rect x="220" y="265" width="360" height="70" fill="#43a9e6"/><rect x="335" y="235" width="130" height="130" fill="#f0ca53" opacity=".88"/><path d="M365 120L300 70H500L435 120M580 265L665 220V380L580 335" fill="#efad45"/><rect x="270" y="30" width="260" height="45" fill="#efad45"/><rect x="660" y="190" width="70" height="220" fill="#efad45"/>'
    if key == "crossbar_component":
        rows = "".join(f'<rect x="220" y="{190+i*70}" width="380" height="20" fill="#43a9e6"/>' for i in range(4))
        cols = "".join(f'<rect x="{285+i*80}" y="130" width="22" height="340" fill="#38c9a5" opacity=".88"/>' for i in range(4))
        return rows + cols + '<path d="M220 190H145V210H220M307 130V75H329V130" fill="#efad45" stroke="#efad45" stroke-width="18"/>'
    if key == "hemt_component":
        return '<rect x="220" y="230" width="380" height="140" rx="8" fill="#f0ca53"/><rect x="245" y="245" width="90" height="110" fill="#ef6473"/><rect x="465" y="245" width="90" height="110" fill="#ef6473"/><rect x="378" y="205" width="44" height="190" fill="#38c9a5"/><path d="M290 245V120H170M510 355V480H630M400 205V90" fill="none" stroke="#efad45" stroke-width="34" stroke-linejoin="round"/><rect x="205" y="215" width="410" height="170" fill="none" stroke="#ad72cf" stroke-width="6" stroke-dasharray="10 7"/>'
    if key == "hall_component":
        return '<rect x="200" y="260" width="400" height="80" rx="8" fill="#f0ca53"/><rect x="115" y="225" width="110" height="150" fill="#ef6473"/><rect x="575" y="225" width="110" height="150" fill="#ef6473"/><path d="M300 260V165H255M300 340V435H255M410 260V165H455M410 340V435H455M520 260V165H565M520 340V435H565" fill="none" stroke="#ef6473" stroke-width="24"/>'
    if key == "tlm_component":
        bars = "".join(f'<rect x="{220+x}" y="190" width="28" height="220" fill="#ef6473"/>' for x in (0, 55, 135, 245, 390))
        return '<rect x="185" y="235" width="480" height="130" fill="#f0ca53"/>' + bars + '<path d="M220 190V100M665 410V500" stroke="#efad45" stroke-width="42"/>'
    # Array tools: show the array and a magnified two-device pixel.
    cells = "".join(f'<rect x="{170+c*72}" y="{145+r*72}" width="52" height="52" rx="5" fill="#e7edf2" stroke="#7d8b97" stroke-width="2"/>' for r in range(4) for c in range(5))
    accent = "#38c9a5" if key == "sense_latch_array" else "#43a9e6"
    return cells + f'<rect x="520" y="180" width="180" height="220" rx="18" fill="#f8fbfd" stroke="{accent}" stroke-width="5"/><rect x="555" y="225" width="110" height="42" rx="6" fill="#f0ca53"/><rect x="555" y="315" width="110" height="42" rx="6" fill="#f0ca53"/><path d="M545 246H505M665 336H720M610 267V315" stroke="#ef6473" stroke-width="14" fill="none"/>'


def _diagram(tool, keys):
    params = {param.key: param for param in tool.params}
    anchors = {
        "nanodevice_fet": [(455, 290), (505, 330), (535, 330), (630, 300)],
        "gdsfactory_text": [(500, 280), (590, 330), (360, 335), (420, 385)],
        "mosfet_component": [(500, 315), (540, 315), (500, 255), (760, 315)],
        "mosfet_pcell": [(500, 315), (540, 315), (500, 255), (760, 315)],
        "woodpile_component": [(500, 330), (500, 260), (630, 330), (760, 330)],
        "crossbar_component": [(515, 220), (365, 330), (530, 330), (610, 420)],
        "hemt_component": [(500, 315), (440, 315), (560, 315), (500, 365)],
        "hall_component": [(500, 325), (500, 350), (610, 250), (610, 325)],
        "tlm_component": [(500, 315), (445, 315), (610, 315), (500, 370)],
        "sense_latch_array": [(420, 290), (575, 290), (500, 325), (500, 365)],
        "write_read_array": [(420, 290), (575, 290), (500, 325), (535, 345)],
    }[tool.key]
    labels = [(24, 30), (736, 30), (24, 708), (736, 708)]
    lines = []
    for index, key in enumerate(keys):
        param = params[key]
        ax, ay = anchors[index]
        lx, ly = labels[index]
        end_x = lx + (235 if index % 2 == 0 else 0)
        end_y = ly + (22 if index < 2 else -8)
        lines.append(f'<path d="M{end_x} {end_y} L{ax} {ay}" stroke="#56b8f0" stroke-width="3" fill="none" marker-end="url(#arrow)"/>')
        lines.append(f'<rect x="{lx-10}" y="{ly-26}" width="250" height="52" rx="8" fill="#ffffff" fill-opacity=".96" stroke="#75bde5"/>')
        lines.append(f'<text x="{lx}" y="{ly-6}" class="anno">{escape(param.symbol)} · {escape(param.label)}</text><text x="{lx}" y="{ly+13}" class="key">{escape(param.key)}</text>')
    return f'''<svg class="diagram" viewBox="0 0 1000 760" role="img" aria-label="{escape(tool.title)} real canvas preview with parameter annotations">
<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0L8 4L0 8Z" fill="#2f77a7"/></marker></defs>
<style>.anno{{font:600 13px Segoe UI,Arial,sans-serif;fill:#20303c}}.key{{font:11px Consolas,monospace;fill:#596b78}}</style>
<rect width="1000" height="760" rx="18" fill="#101010"/><image href="assets/{escape(tool.key)}-canvas.png" x="0" y="55" width="1000" height="650" preserveAspectRatio="none"/>{''.join(lines)}</svg>'''


def render_canvas_images():
    """Capture exactly the same PreviewView used by the NanoDevice GUI."""
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    assets = HERE / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for tool in TOOLS:
        view = gui.PreviewView()
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        view.resize(1000, 650)
        values = {parameter.key: parameter.default for parameter in tool.params}
        error = view.draw_tool_preview(tool, values, preserve_view=False)
        if error:
            raise RuntimeError("{} preview failed: {}".format(tool.key, error))
        view.show()
        app.processEvents()
        if not view.grab().save(str(assets / (tool.key + "-canvas.png"))):
            raise RuntimeError("unable to save canvas preview for {}".format(tool.key))
        view.close()


def _default(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def build_page(tool):
    cn_title, summary, annotated = INFO[tool.key]
    groups = defaultdict(list)
    for parameter in tool.params:
        groups[parameter.group].append(parameter)
    sections = []
    for group, parameters in groups.items():
        rows = []
        for parameter in parameters:
            condition = parameter.visible_if or parameter.enabled_if
            condition_text = escape(str(condition)) if condition else None
            condition_html = _bi(condition_text, condition_text) if condition_text else _bi("始终", "Always")
            effect_en = parameter.tooltip or f"Controls {parameter.label} in the {group} part of the structure."
            effect_zh = f"控制“{parameter.label}”，作用于 {group} 结构区域。"
            rows.append(f"<tr><td><code>{escape(parameter.symbol or '-')}</code></td><td><code>{escape(parameter.key)}</code><br>{escape(parameter.label)}</td><td><code>{escape(_default(parameter.default))}</code></td><td>{_bi(effect_zh, effect_en)}</td><td><code>{condition_html}</code></td></tr>")
        sections.append(f'<section><h2>{escape(group)}</h2><div class="table-wrap"><table><thead><tr><th>{_bi("符号", "Symbol")}</th><th>{_bi("GUI 参数", "GUI parameter")}</th><th>{_bi("默认值", "Default")}</th><th>{_bi("如何改变结构", "Structural effect")}</th><th>{_bi("显示/启用条件", "Visible / enabled when")}</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div></section>')
    insert_zh = "生成可再次编辑的 PCell 实例。" if tool.key == "mosfet_pcell" else "生成当前参数对应的版图几何。"
    insert_en = "Creates an editable PCell instance." if tool.key == "mosfet_pcell" else "Creates layout geometry from the current parameters."
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"><title>{escape(tool.title)} · NanoDevice Manual</title><link rel="stylesheet" href="assets/manual.css"></head><body><main>
<nav><a href="index.html">{_bi("← 全部 Function", "← All functions")}</a><span class="nav-right"><span>{_bi("离线 HTML", "Offline HTML")} · {escape(tool.key)}</span><span class="lang-switch"><button type="button" data-lang="zh">中文</button><button type="button" data-lang="en">English</button></span></span></nav>
<header><p class="eyebrow">NANODEVICE FUNCTION MANUAL</p><h1>{escape(tool.title)}</h1><p class="lead">{_bi(cn_title + "：" + summary, EN_INFO[tool.key])}</p></header>
<section class="hero"><h2>{_bi("参数如何控制结构", "How parameters control the structure")}</h2><p>{_bi("下图是该 Function 默认参数在 NanoDevice Canvas 中的真实预览。蓝色引线标出主要参数控制的区域；完整参数见下方分组表。", "The image is the real NanoDevice Canvas preview at default settings. Blue leaders identify the regions controlled by key parameters; the complete parameter list follows below.")}</p>{_diagram(tool, annotated)}</section>
<section><h2>{_bi("使用流程", "Workflow")}</h2><div class="lang zh"><ol><li>在 Function 中选择 <b>{escape(tool.title)}</b>。</li><li>先设置主体尺寸，再设置 Pad、扇出、标记和显示选项。</li><li>检查预览与 Layers 开关；按底部状态提示修正无效参数。</li><li>需要复用时使用 Export Config 保存全部参数。</li></ol><ul><li><b>插入方式：</b>{insert_zh}</li><li><b>单位：</b>带 <code>um</code> 后缀的长度均为微米；角度为度。</li></ul></div><div class="lang en"><ol><li>Select <b>{escape(tool.title)}</b> in Function.</li><li>Set the main dimensions first, then pads, fanout, marks, and display options.</li><li>Inspect the preview and Layers controls; correct invalid values reported in the bottom status line.</li><li>Use Export Config to preserve a reusable parameter set.</li></ol><ul><li><b>Insertion:</b> {insert_en}</li><li><b>Units:</b> lengths ending in <code>um</code> are micrometres; angles are degrees.</li></ul></div></section>
{''.join(sections)}
<footer>{_bi("本页由实际 ToolSpec 参数与真实 Canvas 生成。", "This page is generated from the actual ToolSpec and real Canvas preview.")}</footer>
</main><script src="assets/manual.js"></script></body></html>'''


CSS = '''*{box-sizing:border-box}body{margin:0;background:#eef3f6;color:#1f2c35;font:15px/1.55 "Segoe UI","Microsoft YaHei",Arial,sans-serif}main{max-width:1120px;margin:0 auto;padding:28px 22px 54px}nav,.nav-right{display:flex;justify-content:space-between;align-items:center;gap:16px;color:#667985;font-size:13px}.lang.en,body.lang-en .lang.zh{display:none}body.lang-en .lang.en{display:initial}div.lang.en,body.lang-en div.lang.zh{display:none}body.lang-en div.lang.en{display:block}.lang-switch{display:inline-flex;border:1px solid #b8ccd8;border-radius:7px;overflow:hidden}.lang-switch button{border:0;background:#fff;color:#426072;padding:5px 10px;cursor:pointer}.lang-switch button.active{background:#2379a8;color:#fff}a{color:#17699a;text-decoration:none}a:hover{text-decoration:underline}header{padding:52px 0 26px}.eyebrow{color:#3180ad;font-weight:700;letter-spacing:.14em;font-size:12px}h1{font-size:42px;line-height:1.12;margin:7px 0 13px}h2{font-size:23px;margin:0 0 13px}.lead{max-width:820px;font-size:18px;color:#4c5e69}.hero,section{background:#fff;border:1px solid #d8e2e8;border-radius:14px;padding:24px;margin:18px 0;box-shadow:0 4px 18px rgba(35,60,75,.05)}.diagram{display:block;width:100%;max-width:900px;margin:18px auto 0;border-radius:12px}.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:13px}th,td{border-bottom:1px solid #dfe7ec;padding:10px 9px;text-align:left;vertical-align:top}th{background:#f3f7f9;position:sticky;top:0}td:nth-child(1),td:nth-child(3){white-space:nowrap}code{font-family:Consolas,"Cascadia Mono",monospace;color:#184d6c;background:#edf4f8;border-radius:4px;padding:1px 4px}footer{color:#6d7b84;text-align:center;padding:28px 0}@media(max-width:700px){main{padding:16px 10px 32px}nav{align-items:flex-start}.nav-right{align-items:flex-end;flex-direction:column}h1{font-size:32px}.hero,section{padding:16px}.diagram{min-width:650px}.hero{overflow-x:auto}}@media print{body{background:#fff}main{max-width:none}.hero,section{box-shadow:none;break-inside:avoid}nav{display:none}}'''

JS = '''(function(){function setLanguage(lang){lang=lang==='en'?'en':'zh';document.body.classList.toggle('lang-en',lang==='en');document.documentElement.lang=lang==='en'?'en':'zh-CN';try{localStorage.setItem('nanodevice-manual-language',lang)}catch(e){}document.querySelectorAll('[data-lang]').forEach(function(button){button.classList.toggle('active',button.dataset.lang===lang)})}document.querySelectorAll('[data-lang]').forEach(function(button){button.addEventListener('click',function(){setLanguage(button.dataset.lang)})});var saved='zh';try{saved=localStorage.getItem('nanodevice-manual-language')||((navigator.language||'').toLowerCase().indexOf('zh')===0?'zh':'en')}catch(e){}setLanguage(saved);window.setManualLanguage=setLanguage})();'''


def main():
    assets = HERE / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (assets / "manual.css").write_text(CSS, encoding="utf-8")
    (assets / "manual.js").write_text(JS, encoding="utf-8")
    cards = []
    for tool in TOOLS:
        (HERE / (tool.key + ".html")).write_text(build_page(tool), encoding="utf-8")
        cn_title, summary, _ = INFO[tool.key]
        cards.append(f'<a class="card" href="{escape(tool.key)}.html"><b>{escape(tool.title)}</b><span>{_bi(cn_title, tool.title)}</span><p>{_bi(summary, EN_INFO[tool.key])}</p></a>')
    index = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"><title>NanoDevice Function Manuals</title><link rel="stylesheet" href="assets/manual.css"><style>.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}}.card{{display:block;background:#fff;border:1px solid #d8e2e8;border-radius:12px;padding:18px;color:#1f2c35}}.card:hover{{border-color:#62a4ca;text-decoration:none;box-shadow:0 5px 18px rgba(35,60,75,.09)}}.card b,.card span{{display:block}}.card span{{color:#3180ad;margin-top:3px}}.card p{{color:#596b76;margin-bottom:0}}</style></head><body><main><nav><span></span><span class="lang-switch"><button type="button" data-lang="zh">中文</button><button type="button" data-lang="en">English</button></span></nav><header><p class="eyebrow">OFFLINE DOCUMENTATION</p><h1>NanoDevice Function Manuals</h1><p class="lead">{_bi("每个 GUI Function 都有独立的真实 Canvas 图、参数标注、完整默认值与结构作用表。页面无需联网。", "Every GUI function has a real Canvas image, parameter annotations, complete defaults, and a structural-effect table. All pages work offline.")}</p></header><div class="cards">{''.join(cards)}</div><footer>{_bi("入口：NanoDevice GUI → 选择 Function → Manual", "Open: NanoDevice GUI → select Function → Manual")}</footer></main><script src="assets/manual.js"></script></body></html>'''
    (HERE / "index.html").write_text(index, encoding="utf-8")
    render_canvas_images()
    print("Generated {} function manuals in {}".format(len(TOOLS), HERE))


if __name__ == "__main__":
    main()
