"""Command line interface."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from PIL import Image
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .advice import get_advice
from .calibration import evaluate_records
from .config import Paths
from .labels import parse_label
from .model import ModelNotReady, PlantDiseaseModel

app = typer.Typer(add_completion=False, help="Offline crop-disease diagnosis for smallholder farmers.")
console = Console()


@app.callback(invoke_without_command=True)
def _root(
    version: bool = typer.Option(False, "--version", is_eager=True, help="Show the version and exit."),
) -> None:
    if version:
        console.print(__version__)
        raise typer.Exit()



def _load_model(model_path: Path | None) -> PlantDiseaseModel:
    try:
        return PlantDiseaseModel(model_path=model_path, config_path=None)
    except ModelNotReady as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc


@app.command()
def diagnose(
    image: Path = typer.Argument(..., exists=True, readable=True, help="Leaf photo (JPG/PNG)."),
    top_k: int = typer.Option(3, min=1, max=5, help="How many candidates to show."),
    as_json: bool = typer.Option(False, "--json", help="Machine-readable output."),
    model_path: Path | None = typer.Option(None, help="Override the ONNX model path."),
) -> None:
    """Diagnose a leaf photo and print a treatment plan."""
    model = _load_model(model_path)
    predictions = model.predict(Image.open(image), top_k=top_k)
    best = predictions[0]
    advice = get_advice(best)

    if as_json:
        payload = {
            "predictions": [p.as_dict() for p in predictions],
            "advice": advice,
        }
        typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    table = Table(title=f"shamba · {image.name}", show_lines=False)
    table.add_column("Rank", justify="right")
    table.add_column("Crop")
    table.add_column("Disease")
    table.add_column("Confidence", justify="right")
    for rank, prediction in enumerate(predictions, start=1):
        table.add_row(
            str(rank),
            prediction.info.crop,
            prediction.info.disease,
            f"{prediction.confidence:.1%}",
        )
    console.print(table)

    if advice.get("confidence_note"):
        console.print(Panel(advice["confidence_note"], title="Low confidence", border_style="yellow"))

    console.print(Panel(advice["summary"], title=f"{advice['crop']} · {advice['disease']}", border_style="green"))
    for section, label in (
        ("act_now", "Do now"),
        ("organic", "Low-cost / organic"),
        ("chemical", "Chemical (only if needed)"),
        ("prevent", "Prevent next season"),
    ):
        items = advice.get(section) or []
        if items:
            console.print(f"\n[bold]{label}[/bold]")
            for item in items:
                console.print(f"  • {item}")
    if advice.get("escalate"):
        console.print(Panel(advice["escalate"], title="When to escalate", border_style="red"))
    console.print(f"\n[dim]{advice['disclaimer']}[/dim]")


@app.command()
def evaluate(
    folder: Path = typer.Argument(..., exists=True, file_okay=False),
    model_path: Path | None = typer.Option(None, help="Override the ONNX model path."),
    as_json: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Measure accuracy and calibration on a folder named by class."""
    model = _load_model(model_path)
    known = {label.key: label for label in model.labels.values()}
    files: list[tuple[Path, str]] = []
    for class_dir in sorted(folder.iterdir()):
        if not class_dir.is_dir():
            continue
        info = parse_label(class_dir.name)
        if info.key not in known:
            console.print(f"[yellow]skip unknown class: {class_dir.name}[/yellow]")
            continue
        for image in sorted(class_dir.iterdir()):
            if image.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
                files.append((image, info.raw))
    if not files:
        console.print("[red]no labeled images found[/red]")
        raise typer.Exit(code=1)

    records = []
    for image, true_label in files:
        prediction = model.predict(Image.open(image), top_k=1)[0]
        records.append(
            {
                "true": true_label,
                "predicted": prediction.info.raw,
                "confidence": prediction.confidence,
                "correct": prediction.info.raw == true_label,
            }
        )
    result = evaluate_records(records)
    if as_json:
        typer.echo(json.dumps(result.as_dict(), indent=2))
        return
    console.print(f"{result.count} images · accuracy {result.accuracy:.1%} · ECE {result.ece:.3f} · Brier {result.brier:.3f}")
    table = Table("Class", "Recall")
    table.add_column("Class")
    table.add_column("Recall", justify="right")
    for key, value in result.per_class_recall.items():
        table.add_row(key, f"{value:.1%}")
    console.print(table)
    thresholds = Table("Confidence", "Coverage", "Accuracy")
    for threshold, values in result.thresholds.items():
        thresholds.add_row(f"≥ {threshold}", f"{values['coverage']:.1%}", f"{values['accuracy']:.1%}")
    console.print(thresholds)


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Bind address."),
    port: int = typer.Option(8787, help="Port."),
) -> None:
    """Start the local web UI."""
    import uvicorn

    uvicorn.run("shamba.server:app", host=host, port=port, log_level="info")


@app.command()
def doctor() -> None:
    """Check that the model and runtime are ready."""
    import onnxruntime as ort

    paths = Paths.default()
    console.print(f"onnxruntime: [bold]{ort.__version__}[/bold]")
    console.print(f"model: {paths.model} ({'found' if paths.model.exists() else 'missing'})")
    console.print(f"config: {paths.config} ({'found' if paths.config.exists() else 'missing'})")
    if not paths.model.exists():
        console.print("\nRun: [bold]python scripts/download_model.py[/bold]")
        raise typer.Exit(code=1)
    model = PlantDiseaseModel()
    console.print(f"labels: [bold]{len(model.labels)}[/bold]")
    console.print("[green]ready[/green]")


if __name__ == "__main__":
    app()
