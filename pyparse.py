"""
Parse Excel files and analyze the TIME column.
python pyparse.py --debug --limit 180
"""

from __future__ import annotations

import argparse
import re
import statistics
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Tuple

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

import openpyxl

TIME_VALUE_PATTERN = re.compile(r"([-+]?\d+(?:\.\d+)?)")


def parse_time_value(value) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None

    match = TIME_VALUE_PATTERN.search(text)
    if not match:
        return None

    try:
        return float(match.group(1))
    except ValueError:
        return None


def find_time_column(header_row) -> Optional[int]:
    for index, cell in enumerate(header_row):
        if cell is None:
            continue
        if str(cell).strip().upper() == "TIME":
            return index
    return None


def parse_times_from_xlsx(file_path: Path, time_limit: Optional[float] = None) -> List[float]:
    workbook = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    sheet = workbook.worksheets[0]

    header_row_index = None
    time_col_index = None

    for row_index, row in enumerate(sheet.iter_rows(min_row=1, max_row=10, values_only=True), start=1):
        time_col_index = find_time_column(row)
        if time_col_index is not None:
            header_row_index = row_index
            break

    if time_col_index is None:
        raise ValueError(f"No TIME column found in {file_path.name}")

    times: List[float] = []
    for row in sheet.iter_rows(min_row=header_row_index + 1, values_only=True):
        cell_value = row[time_col_index] if time_col_index < len(row) else None
        time_value = parse_time_value(cell_value)
        if time_value is None:
            continue

        if time_limit is not None and time_value > time_limit:
            break

        times.append(time_value)

    return times


def get_xlsx_files(folder: Path) -> Iterator[Path]:
    yield from sorted(folder.glob("*.xlsx"))


def compute_deltas(times: Iterable[float]) -> List[float]:
    time_list = list(times)
    return [time_list[i] - time_list[i - 1] for i in range(1, len(time_list))]


def find_negative_deltas(times: Iterable[float]) -> List[tuple[float, float, float]]:
    time_list = list(times)
    negative_pairs: List[tuple[float, float, float]] = []
    for previous, current in zip(time_list, time_list[1:]):
        delta = current - previous
        if delta < 0:
            negative_pairs.append((previous, current, delta))
    return negative_pairs


def compute_statistics(values: Iterable[float]) -> Tuple[Optional[float], Optional[float]]:
    values_list = list(values)
    if not values_list:
        return None, None
    if len(values_list) == 1:
        return values_list[0], 0.0
    return statistics.mean(values_list), statistics.pstdev(values_list)


def format_value(value: Optional[float]) -> str:
    return "n/a" if value is None else f"{value:.6f}"


def plot_deltas(times: List[float], deltas: List[float], title: str, output_path: Path, yzoom: Optional[float] = None) -> None:
    if plt is None:
        print("matplotlib is not installed; cannot create plot.")
        return

    x_values = times[1:]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(x_values, deltas, marker="o", linestyle="-", color="tab:blue")
    ax.axhline(0.0, color="tab:red", linestyle="--", linewidth=0.8)
    ax.set_xlabel("TIME (sec)")
    ax.set_ylabel("Delta TIME (sec)")
    ax.set_title(title)

    mean_delta, deviation = compute_statistics(deltas)
    if mean_delta is None:
        mean_delta = 0.0
    if deviation is None:
        deviation = 0.0

    if yzoom is not None:
        span = float(yzoom)
    else:
        span = max(5 * (deviation or 0.0), 0.002)

    ax.set_ylim(mean_delta - span, mean_delta + span)
    try:
        import matplotlib.ticker as mticker
        ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.6f"))
        ax.yaxis.set_minor_locator(mticker.AutoMinorLocator())
    except Exception:
        pass

    ax.grid(True, linestyle="--", alpha=0.5)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    print(f"  Plot saved to {output_path}")


def analyze_file(file_path: Path, time_limit: Optional[float], debug: bool, plot: bool, plot_dir: Optional[Path], yzoom: Optional[float]) -> None:
    print(f"\nAnalyzing {file_path.name}")
    times = parse_times_from_xlsx(file_path, time_limit=time_limit)
    if not times:
        print("  No TIME values found.")
        return

    deltas = compute_deltas(times)
    mean_delta, deviation = compute_statistics(deltas)

    print(f"  Parsed {len(times)} TIME entries")
    print(f"  First TIME: {format_value(times[0])} sec")
    print(f"  Last TIME: {format_value(times[-1])} sec")
    print(f"  Mean delta: {format_value(mean_delta)} sec")
    print(f"  Delta deviation: {format_value(deviation)} sec")

    if deltas:
        print(f"  Min delta: {format_value(min(deltas))} sec")
        print(f"  Max delta: {format_value(max(deltas))} sec")

    if debug:
        negative_pairs = find_negative_deltas(times)
        if not negative_pairs:
            print("  No negative deltas found.")
        else:
            print("  Negative deltas:")
            for prev_time, current_time, delta in negative_pairs:
                print(f"    previous={format_value(prev_time)} sec, current={format_value(current_time)} sec, delta={format_value(delta)} sec")

    if plot:
        if plot_dir is None:
            output_path = file_path.with_suffix("").with_name(f"{file_path.stem}-delta.png")
        else:
            plot_dir.mkdir(parents=True, exist_ok=True)
            output_path = plot_dir / f"{file_path.stem}-delta.png"
        plot_deltas(times, deltas, f"Delta over time for {file_path.name}", output_path, yzoom=yzoom)


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse Excel files and analyze the TIME column.")
    parser.add_argument("folder", type=Path, nargs="?", default=Path("python-tests-no-zaber/post-conversion-code/"), help="Folder containing .xlsx files to analyze.")
    parser.add_argument("--limit", type=float, default=None, help="Optional TIME limit in seconds.")
    parser.add_argument("--debug", action="store_true", help="Print negative TIME deltas for each file.")
    parser.add_argument("--plot", action="store_true", help="Save plots of delta over time for each file.")
    parser.add_argument("--yzoom", type=float, default=None, help="Half-range for y-axis in seconds (e.g. 0.001). Overrides automatic scaling.")
    parser.add_argument("--plot-dir", type=Path, default=None, help="Optional directory to save plot files.")
    args = parser.parse_args()

    folder = args.folder
    if not folder.exists() or not folder.is_dir():
        raise SystemExit(f"Folder not found: {folder}")

    files = list(get_xlsx_files(folder))
    if not files:
        raise SystemExit(f"No .xlsx files found in {folder}")

    for file_path in files:
        analyze_file(file_path, time_limit=args.limit, debug=args.debug, plot=args.plot, plot_dir=args.plot_dir, yzoom=args.yzoom)


if __name__ == "__main__":
    main()
