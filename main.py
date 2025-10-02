import flet as ft
import pandas as pd
import webbrowser
import json
from datetime import datetime
from pathlib import Path

# === storage ===
APP_DIR = Path.cwd()
HISTORY_PATH = APP_DIR / "history.json"

def load_history() -> list[dict]:
    if HISTORY_PATH.exists():
        try:
            return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []

def save_history(items: list[dict]) -> None:
    try:
        HISTORY_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

try:
    from parser.core import Scraper, ScrapeResult
    HAVE_SCRAPER = True
except Exception as e:
    HAVE_SCRAPER = False
    SCRAPER_IMPORT_ERR = str(e)

# ==== Theme ====
PRIMARY = "#5561ff"
ACCENT  = "#7af0ff"
BG      = "#0f1117"
CARD_BG = "#15192b"
BORDER  = "#2a2f42"
TEXT    = "#e3e7ff"
MUTED   = "#8690b0"
OK      = "#65d38f"
WARN    = "#ffb454"

def format_money(p):
    try:
        return f"{int(p):,} ₸".replace(",", " ")
    except:
        return "—"

def kpi_card(title: str, value: str, icon):
    return ft.Container(
        bgcolor=CARD_BG,
        border=ft.border.all(1, BORDER),
        border_radius=18,
        padding=16,
        shadow=ft.BoxShadow(blur_radius=18, color="#00000040"),
        content=ft.Column(
            spacing=8,
            controls=[
                ft.Row(
                    alignment="spaceBetween",
                    controls=[
                        ft.Text(title, size=13, color=MUTED),
                        ft.Icon(icon, color=ACCENT, size=20),
                    ],
                ),
                ft.Text(value, size=22, weight="w700", color=TEXT),
            ],
        ),
    )

def timeline_row(url: str, rows: int, ts: str):
    dot = ft.Container(width=8, height=8, bgcolor=OK if rows>0 else WARN, border_radius=50)
    return ft.Row(
        spacing=10,
        alignment="start",
        controls=[
            dot,
            ft.Column(
                spacing=1,
                controls=[
                    ft.Text(url, color=TEXT, size=12, selectable=True, overflow=ft.TextOverflow.ELLIPSIS, max_lines=1),
                    ft.Text(f"{rows} строк • {ts}", color=MUTED, size=10),
                ],
            ),
            ft.IconButton(
                ft.icons.OPEN_IN_NEW, tooltip="Открыть ссылку",
                on_click=lambda e, u=url: webbrowser.open_new_tab(u)
            ),
            ft.IconButton(
                ft.icons.CONTENT_PASTE_GO, tooltip="Подставить в поле ввода",
                on_click=lambda e, u=url: e.page.session.set("fill_url", u)
            ),
        ],
    )

def app_view(page: ft.Page):
    page.title = "KZ Scraper"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 18
    page.bgcolor = BG
    page.window.min_width = 1100
    page.window.min_height = 700
    page.scroll = ft.ScrollMode.ADAPTIVE

    header = ft.Container(
        border_radius=18,
        padding=18,
        shadow=ft.BoxShadow(blur_radius=24, color="#00000055"),
        gradient=ft.LinearGradient(
            begin=ft.alignment.top_left,
            end=ft.alignment.bottom_right,
            colors=[PRIMARY, ACCENT],
        ),
        content=ft.Row(
            alignment="spaceBetween",
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Row(
                    spacing=14,
                    controls=[
                        ft.Icon(ft.icons.EXPLORE, color="white"),
                        ft.Text("KZ Marketplace Parser", color="white", weight="w700", size=18),
                        ft.Text("market.kz • krisha.kz", color="#ffffffcc", size=12),
                    ],
                ),
            ],
        ),
    )

    url_in = ft.TextField(
        label="Ссылка на страницу с объявлениями",
        hint_text="https://krisha.kz/arenda/kvartiry/almaty/?...",
        border_radius=14,
        bgcolor=CARD_BG,
        border_color=BORDER,
        color=TEXT,
        prefix_icon=ft.icons.LINK,
        autofocus=True,
    )
    ssl_toggle = ft.Switch(label="Проверять SSL", value=True)
    run_btn = ft.FilledButton(
        "Спарсить",
        icon=ft.icons.DOWNLOAD,
        style=ft.ButtonStyle(
            bgcolor={ft.ControlState.DEFAULT: PRIMARY},
            color={ft.ControlState.DEFAULT: "white"},
            shape=ft.RoundedRectangleBorder(radius=12)
        ),
    )
    progress = ft.ProgressBar(width=220, visible=False)
    status_text = ft.Text("", size=12, color=MUTED)

    # KPI
    kpi_total = kpi_card("Найдено", "—", ft.icons.TABLE_ROWS)
    kpi_min   = kpi_card("Мин. цена", "—", ft.icons.ARROW_DOWNWARD)
    kpi_max   = kpi_card("Макс. цена", "—", ft.icons.ARROW_UPWARD)
    kpi_city  = kpi_card("Города", "—", ft.icons.LOCATION_CITY)

    # Таблица результатов
    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Площадка")),
            ft.DataColumn(ft.Text("Категория")),
            ft.DataColumn(ft.Text("Название")),
            ft.DataColumn(ft.Text("Цена")),
            ft.DataColumn(ft.Text("Локация")),
            ft.DataColumn(ft.Text("URL")),
            ft.DataColumn(ft.Text("Опубл.")),
            ft.DataColumn(ft.Text("Действие")),
        ],
        rows=[],
        heading_row_color="#1a1f2e",
        data_row_color={"hovered": "#1a2030"},
        column_spacing=20,
        divider_thickness=0,
        show_checkbox_column=False,
    )

    # FilePicker
    fp_save = ft.FilePicker()
    page.overlay.append(fp_save)

    # История
    history: list[dict] = load_history()
    recent_urls = ft.Dropdown(
        label="Недавние ссылки",
        options=[ft.dropdown.Option(item["url"]) for item in history[:20]],
        width=420,
        on_change=lambda e: setattr(url_in, "value", e.control.value) or page.update(),
    )

    # Action-кнопки (правый сайдбар)
    export_csv_btn  = ft.OutlinedButton("Скачать CSV",  icon=ft.icons.DOWNLOAD, disabled=True)
    export_xlsx_btn = ft.OutlinedButton("Скачать XLSX", icon=ft.icons.DOWNLOAD, disabled=True)
    open_site_btn   = ft.FilledTonalButton("Открыть сайт", icon=ft.icons.OPEN_IN_NEW, disabled=True)
    clear_history_btn = ft.TextButton("Очистить историю", icon=ft.icons.DELETE_SWEEP)

    # state
    state_df: pd.DataFrame | None = None
    state_files = {"csv": None, "xlsx": None}

    def set_loading(v: bool, label: str = ""):
        progress.visible = v
        status_text.value = label
        status_text.color = ACCENT if v else MUTED

    def reset_results():
        table.rows.clear()
        for card in (kpi_total, kpi_min, kpi_max, kpi_city):
            card.content.controls[1] = ft.Text("—", size=22, weight="w700", color=TEXT)
        export_csv_btn.disabled = True
        export_xlsx_btn.disabled = True
        open_site_btn.disabled = True

    def fill_table(df: pd.DataFrame):
        table.rows.clear()
        for _, r in df.iterrows():
            url_text = r.get("url", "—") or "—"
            table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(r.get("marketplace","")))),
                        ft.DataCell(ft.Text(str(r.get("category","")))),
                        ft.DataCell(ft.Text(str(r.get("title","")))),
                        ft.DataCell(ft.Text(format_money(r.get("price",0)))),
                        ft.DataCell(ft.Text(str(r.get("location","")))),
                        ft.DataCell(ft.Text(url_text, selectable=True)),
                        ft.DataCell(ft.Text(str(r.get("date_posted","")))),
                        ft.DataCell(
                            ft.TextButton(
                                "Открыть", icon=ft.icons.OPEN_IN_NEW,
                                on_click=lambda e, _u=url_text: webbrowser.open_new_tab(_u) if _u and _u!="N/A" else None
                            )
                        ),
                    ]
                )
            )

    def update_kpis(df: pd.DataFrame):
        total = len(df)
        pmin = df["price"].min() if total else 0
        pmax = df["price"].max() if total else 0
        cities = df["location"].nunique() if total else 0
        kpi_total.content.controls[1] = ft.Text(f"{total}", size=22, weight="w700", color=TEXT)
        kpi_min.content.controls[1]   = ft.Text(format_money(pmin), size=22, weight="w700", color=TEXT)
        kpi_max.content.controls[1]   = ft.Text(format_money(pmax), size=22, weight="w700", color=TEXT)
        kpi_city.content.controls[1]  = ft.Text(f"{cities}", size=22, weight="w700", color=TEXT)

    def on_export(kind: str):
        nonlocal state_df
        if state_df is None or state_df.empty:
            return
        default_name = state_files.get(kind) or f"export_{kind}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{kind}"
        fp_save.save_file(
            dialog_title=f"Сохранить {kind.upper()}",
            file_name=Path(default_name).name,
            allowed_extensions=["csv"] if kind == "csv" else ["xlsx"],
        )
        def after_save(e: ft.FilePickerResultEvent):
            if e.path:
                if kind == "csv":
                    state_df.to_csv(e.path, index=False, encoding="utf-8-sig")
                else:
                    state_df.to_excel(e.path, index=False)
                page.snack_bar = ft.SnackBar(ft.Text(f"{kind.upper()} сохранён"), bgcolor=CARD_BG)
                page.snack_bar.open = True
                page.update()
        fp_save.on_result = after_save
        page.update()

    export_csv_btn.on_click  = lambda e: on_export("csv")
    export_xlsx_btn.on_click = lambda e: on_export("xlsx")
    open_site_btn.on_click   = lambda e: webbrowser.open_new_tab(url_in.value.strip()) if url_in.value else None

    def do_scrape():
        reset_results()
        url = (url_in.value or "").strip()
        if not url:
            page.snack_bar = ft.SnackBar(ft.Text("Вставь ссылку"), bgcolor="#2b2f45")
            page.snack_bar.open = True
            page.update()
            return

        if not HAVE_SCRAPER:
            page.dialog = ft.AlertDialog(
                title=ft.Text("Скрапер не найден"),
                content=ft.Text(f"Импорт не удался: {SCRAPER_IMPORT_ERR}\n"
                                f"Положи свой модуль в /parser (core/adapters/utils) или "
                                f"замени импорт в main.py."),
            )
            page.dialog.open = True
            page.update()
            return

        set_loading(True, "Загружаю страницу…"); page.update()
        try:
            s = Scraper(verify_ssl=ssl_toggle.value)
            res = s.scrape_url(url)
            nonlocal state_df, state_files, history
            state_df = res.df if res.df is not None else pd.DataFrame()
            state_files = {"csv": res.file_csv, "xlsx": res.file_xlsx}

            if state_df is None or state_df.empty:
                set_loading(False, "Ничего не найдено 😕"); return

            fill_table(state_df)
            update_kpis(state_df)
            export_csv_btn.disabled = False
            export_xlsx_btn.disabled = False
            open_site_btn.disabled = False

            entry = {"url": url, "rows": int(len(state_df)), "ts": datetime.now().strftime("%Y-%m-%d %H:%M")}
            history.insert(0, entry)
            # dedup
            seen, deduped = set(), []
            for h in history:
                if h["url"] in seen: continue
                seen.add(h["url"]); deduped.append(h)
            history = deduped[:100]; save_history(history)
            refresh_history()
            recent_urls.options = [ft.dropdown.Option(item["url"]) for item in history[:20]]

            set_loading(False, "Готово ✅"); page.update()
        except Exception as ex:
            set_loading(False, "")
            page.dialog = ft.AlertDialog(title=ft.Text("Ошибка"), content=ft.Text(str(ex)))
            page.dialog.open = True; page.update()

    run_btn.on_click = lambda e: do_scrape()

    # ===== history =====
    history_list = ft.Column(spacing=8, scroll=ft.ScrollMode.ALWAYS, expand=True)

    def refresh_history():
        items = []
        for item in history[:120]:
            items.append(timeline_row(item["url"], item["rows"], item["ts"]))
        history_list.controls = items
        page.update()

    def clear_history(_=None):
        nonlocal history
        history = []; save_history(history); refresh_history()
        recent_urls.options = []; page.update()

    clear_history_btn.on_click = clear_history

    page.session.set("fill_url", None)
    def on_global_route(_):
        value = page.session.get("fill_url")
        if value:
            url_in.value = value
            page.session.set("fill_url", None)
            page.update()
    page.on_route_change = on_global_route

    # ==== Layout ====

    input_card = ft.Container(
        bgcolor=CARD_BG, border=ft.border.all(1, BORDER), border_radius=18, padding=16,
        content=ft.Column(
            spacing=12,
            controls=[
                ft.Text("Ввод", size=14, color=MUTED),
                url_in,
                recent_urls,
                ft.Row([ssl_toggle, run_btn, progress], alignment="start", spacing=16),
                ft.Row([ft.Text("Готово", color=MUTED), ft.Icon(ft.icons.CHECK_BOX, color=OK, size=18)], spacing=10),
                status_text,
            ],
        ),
    )

    kpis = ft.ResponsiveRow(
        columns=12,
        controls=[
            ft.Container(kpi_total, col={'xs':12,'md':3}),
            ft.Container(kpi_min,   col={'xs':12,'md':3}),
            ft.Container(kpi_max,   col={'xs':12,'md':3}),
            ft.Container(kpi_city,  col={'xs':12,'md':3}),
        ],
    )

    results_card = ft.Container(
        bgcolor=CARD_BG, border=ft.border.all(1, BORDER), border_radius=18, padding=16,
        shadow=ft.BoxShadow(blur_radius=18, color="#00000040"),
        content=ft.Column(
            spacing=12,
            controls=[
                ft.Text("Результаты", size=14, color=MUTED),
                ft.Container(
                    height=480,  
                    border=ft.border.all(1, BORDER),
                    border_radius=12,
                    padding=0,
                    content=ft.Column(
                        controls=[table],
                        expand=True,
                        scroll=ft.ScrollMode.ALWAYS,  
                    ),
                ),
            ],
        ),
    )

    left_col = ft.Column(spacing=16, controls=[header, input_card, kpis, results_card], expand=3)

    actions_card = ft.Container(
        bgcolor=CARD_BG, border=ft.border.all(1, BORDER), border_radius=18, padding=16,
        shadow=ft.BoxShadow(blur_radius=18, color="#00000040"),
        content=ft.Column(
            spacing=12,
            controls=[
                ft.Text("Действия", size=14, color=MUTED),
                export_csv_btn,
                export_xlsx_btn,
                open_site_btn,
                ft.Divider(height=1, color=BORDER),
                ft.Row([clear_history_btn], alignment="end"),
            ],
        ),
    )

    history_card = ft.Container(
        bgcolor=CARD_BG, border=ft.border.all(1, BORDER), border_radius=18, padding=16,
        shadow=ft.BoxShadow(blur_radius=18, color="#00000040"),
        content=ft.Column(
            spacing=12,
            controls=[
                ft.Row(
                    [ft.Text("История ссылок", color=MUTED),],
                    alignment="spaceBetween"
                ),
                ft.Container(height=540, content=history_list),  
            ],
        ),
    )

    right_col = ft.Column(spacing=16, controls=[actions_card, history_card], expand=1)

    page.add(ft.Row([left_col, right_col], vertical_alignment=ft.CrossAxisAlignment.START))
    refresh_history()

def main():
    ft.app(target=app_view)

if __name__ == "__main__":
    main()