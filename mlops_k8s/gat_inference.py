from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    nn = None
    F = None
    TORCH_AVAILABLE = False


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PORORO_DIR = PROJECT_ROOT / "pororo"
ARTIFACT_DIR = PROJECT_ROOT / "tableau_mlops" / "artifacts"


@dataclass(frozen=True)
class RunArtifacts:
    node_activity: pd.DataFrame
    edge_activity: pd.DataFrame
    oht_edges: pd.DataFrame
    run_summary: pd.DataFrame


def _first_existing_path(filename: str) -> Path:
    for base_dir in (PORORO_DIR, ARTIFACT_DIR):
        candidate = base_dir / filename
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Required artifact not found: {filename}")


def load_artifacts() -> RunArtifacts:
    return RunArtifacts(
        node_activity=pd.read_csv(_first_existing_path("node_activity.csv")),
        edge_activity=pd.read_csv(_first_existing_path("edge_activity.csv")),
        oht_edges=pd.read_csv(_first_existing_path("oht_edges.csv")),
        run_summary=pd.read_csv(_first_existing_path("run_summary.csv")),
    )


def _minmax(series: pd.Series) -> pd.Series:
    minimum = float(series.min())
    maximum = float(series.max())
    scale = maximum - minimum
    if scale == 0:
        return pd.Series(0.0, index=series.index)
    return (series - minimum) / scale


def _build_node_frame(artifacts: RunArtifacts) -> pd.DataFrame:
    node_stats = artifacts.node_activity.groupby(["run_id", "node"], as_index=False)["touch_count"].sum()

    graph_edges = (
        artifacts.oht_edges[["source_node", "target_node"]]
        .drop_duplicates()
        .rename(columns={"source_node": "source", "target_node": "target"})
    )

    degree_out = graph_edges.groupby("source").size().rename("out_degree")
    degree_in = graph_edges.groupby("target").size().rename("in_degree")
    degree = pd.concat([degree_out, degree_in], axis=1).fillna(0.0)
    degree.index.name = "node"
    degree = degree.reset_index()

    edge_weights = (
        artifacts.oht_edges.groupby(["run_id", "source_node", "target_node"], as_index=False)["weight"].mean()
    )
    edge_traverse = (
        artifacts.edge_activity.groupby(["run_id", "edge_source", "edge_target"], as_index=False)["traverse_count"].sum()
    )

    outbound_traverse = edge_traverse.groupby(["run_id", "edge_source"], as_index=False)["traverse_count"].sum()
    outbound_traverse = outbound_traverse.rename(columns={"edge_source": "node", "traverse_count": "outbound_traverse"})
    inbound_traverse = edge_traverse.groupby(["run_id", "edge_target"], as_index=False)["traverse_count"].sum()
    inbound_traverse = inbound_traverse.rename(columns={"edge_target": "node", "traverse_count": "inbound_traverse"})

    source_weight = edge_weights.groupby(["run_id", "source_node"], as_index=False)["weight"].mean()
    source_weight = source_weight.rename(columns={"source_node": "node", "weight": "avg_out_weight"})
    target_weight = edge_weights.groupby(["run_id", "target_node"], as_index=False)["weight"].mean()
    target_weight = target_weight.rename(columns={"target_node": "node", "weight": "avg_in_weight"})

    node_frame = node_stats.merge(degree, on="node", how="left")
    node_frame = node_frame.merge(outbound_traverse, on=["run_id", "node"], how="left")
    node_frame = node_frame.merge(inbound_traverse, on=["run_id", "node"], how="left")
    node_frame = node_frame.merge(source_weight, on=["run_id", "node"], how="left")
    node_frame = node_frame.merge(target_weight, on=["run_id", "node"], how="left")
    node_frame = node_frame.fillna(0.0)
    node_frame["weight_mean"] = (node_frame["avg_out_weight"] + node_frame["avg_in_weight"]) / 2.0

    thresholds = node_frame.groupby("run_id")["touch_count"].transform(lambda values: values.quantile(0.75))
    node_frame["is_bottleneck"] = (node_frame["touch_count"] >= thresholds).astype(float)

    feature_columns = [
        "touch_count",
        "in_degree",
        "out_degree",
        "inbound_traverse",
        "outbound_traverse",
        "weight_mean",
    ]
    for column in feature_columns:
        node_frame[f"{column}_norm"] = node_frame.groupby("run_id")[column].transform(_minmax)

    return node_frame


def _build_edge_index(artifacts: RunArtifacts, node_to_index: dict[str, int]) -> torch.Tensor:
    edges = (
        artifacts.oht_edges[["source_node", "target_node"]]
        .drop_duplicates()
        .assign(
            source_idx=lambda frame: frame["source_node"].map(node_to_index),
            target_idx=lambda frame: frame["target_node"].map(node_to_index),
        )
    )
    tensor = torch.tensor(edges[["source_idx", "target_idx"]].to_numpy().T, dtype=torch.long)
    return tensor


if TORCH_AVAILABLE:

    class SingleHeadGAT(nn.Module):
        def __init__(self, in_features: int, hidden_features: int = 16):
            super().__init__()
            self.proj = nn.Linear(in_features, hidden_features, bias=False)
            self.attn_src = nn.Linear(hidden_features, 1, bias=False)
            self.attn_dst = nn.Linear(hidden_features, 1, bias=False)
            self.classifier = nn.Linear(hidden_features + in_features, 1)

        def forward(self, features: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
            transformed = self.proj(features)
            src_index = edge_index[0]
            dst_index = edge_index[1]

            src_repr = transformed[src_index]
            dst_repr = transformed[dst_index]
            attention_logits = F.leaky_relu(self.attn_src(src_repr) + self.attn_dst(dst_repr), negative_slope=0.2).squeeze(-1)

            aggregated = torch.zeros_like(transformed)
            node_count = transformed.size(0)
            for node_idx in range(node_count):
                mask = dst_index == node_idx
                if not torch.any(mask):
                    aggregated[node_idx] = transformed[node_idx]
                    continue
                weights = torch.softmax(attention_logits[mask], dim=0).unsqueeze(-1)
                aggregated[node_idx] = torch.sum(weights * src_repr[mask], dim=0)

            logits = self.classifier(torch.cat([features, aggregated], dim=1)).squeeze(-1)
            return logits

else:

    class SingleHeadGAT:
        pass


@dataclass(frozen=True)
class TrainedArtifacts:
    model: SingleHeadGAT | None
    node_frame: pd.DataFrame
    run_ids: list[int]
    node_order: list[str]
    edge_index: object | None


def _score_without_torch(run_frame: pd.DataFrame, artifacts: RunArtifacts) -> pd.Series:
    base_score = (
        0.34 * run_frame["touch_count_norm"]
        + 0.12 * run_frame["in_degree_norm"]
        + 0.10 * run_frame["out_degree_norm"]
        + 0.18 * run_frame["inbound_traverse_norm"]
        + 0.18 * run_frame["outbound_traverse_norm"]
        + 0.08 * run_frame["weight_mean_norm"]
    )
    graph_edges = artifacts.oht_edges[["source_node", "target_node"]].drop_duplicates()
    source_scores = base_score.reindex(graph_edges["source_node"]).reset_index(drop=True)
    neighbor_scores = (
        pd.DataFrame({"node": graph_edges["target_node"].to_numpy(), "source_score": source_scores.to_numpy()})
        .groupby("node")["source_score"]
        .mean()
    )
    neighbor_scores = run_frame.index.to_series().map(neighbor_scores).fillna(base_score)
    return _minmax((0.76 * base_score) + (0.24 * neighbor_scores))


def train_gat_surrogate(epochs: int = 80, learning_rate: float = 0.03) -> TrainedArtifacts:
    artifacts = load_artifacts()
    node_frame = _build_node_frame(artifacts)
    node_order = sorted(node_frame["node"].unique())
    node_to_index = {node: index for index, node in enumerate(node_order)}
    edge_index = _build_edge_index(artifacts, node_to_index) if TORCH_AVAILABLE else None

    feature_columns = [
        "touch_count_norm",
        "in_degree_norm",
        "out_degree_norm",
        "inbound_traverse_norm",
        "outbound_traverse_norm",
        "weight_mean_norm",
    ]

    run_ids = sorted(node_frame["run_id"].unique())
    if not TORCH_AVAILABLE:
        return TrainedArtifacts(
            model=None,
            node_frame=node_frame,
            run_ids=run_ids,
            node_order=node_order,
            edge_index=edge_index,
        )

    run_tensors: list[tuple[torch.Tensor, torch.Tensor]] = []
    for run_id in run_ids:
        run_frame = node_frame[node_frame["run_id"] == run_id].set_index("node").reindex(node_order).fillna(0.0)
        features = torch.tensor(run_frame[feature_columns].to_numpy(), dtype=torch.float32)
        labels = torch.tensor(run_frame["is_bottleneck"].to_numpy(), dtype=torch.float32)
        run_tensors.append((features, labels))

    torch.manual_seed(7)
    model = SingleHeadGAT(in_features=len(feature_columns))
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

    for _ in range(epochs):
        optimizer.zero_grad()
        losses = []
        for features, labels in run_tensors:
            logits = model(features, edge_index)
            losses.append(F.binary_cross_entropy_with_logits(logits, labels))
        loss = torch.stack(losses).mean()
        loss.backward()
        optimizer.step()

    model.eval()
    return TrainedArtifacts(
        model=model,
        node_frame=node_frame,
        run_ids=run_ids,
        node_order=node_order,
        edge_index=edge_index,
    )


def score_run(trained: TrainedArtifacts, run_id: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    run_frame = trained.node_frame[trained.node_frame["run_id"] == run_id].set_index("node").reindex(trained.node_order).fillna(0.0)
    feature_columns = [
        "touch_count_norm",
        "in_degree_norm",
        "out_degree_norm",
        "inbound_traverse_norm",
        "outbound_traverse_norm",
        "weight_mean_norm",
    ]
    if trained.model is None:
        artifacts = load_artifacts()
        scores = _score_without_torch(run_frame, artifacts).to_numpy()
    else:
        features = torch.tensor(run_frame[feature_columns].to_numpy(), dtype=torch.float32)

        with torch.no_grad():
            scores = torch.sigmoid(trained.model(features, trained.edge_index)).numpy()

    node_scores = run_frame.reset_index().copy()
    node_scores["gat_score"] = scores
    node_scores["risk_level"] = pd.cut(
        node_scores["gat_score"],
        bins=[-0.01, 0.45, 0.7, 1.0],
        labels=["안정", "주의", "위험"],
    )
    node_scores = node_scores.sort_values(["gat_score", "touch_count"], ascending=[False, False]).reset_index(drop=True)

    edge_frame = load_artifacts().edge_activity
    weight_frame = load_artifacts().oht_edges[["run_id", "source_node", "target_node", "weight"]]
    edge_scores = edge_frame[edge_frame["run_id"] == run_id].merge(
        weight_frame[weight_frame["run_id"] == run_id],
        left_on=["run_id", "edge_source", "edge_target"],
        right_on=["run_id", "source_node", "target_node"],
        how="left",
    )
    score_lookup = node_scores.set_index("node")["gat_score"]
    edge_scores["source_score"] = edge_scores["edge_source"].map(score_lookup).fillna(0.0)
    edge_scores["target_score"] = edge_scores["edge_target"].map(score_lookup).fillna(0.0)
    edge_scores["pressure"] = edge_scores["traverse_count"] * edge_scores["weight"].fillna(0.0)
    edge_scores["risk_score"] = (
        0.45 * _minmax(edge_scores["pressure"]).to_numpy()
        + 0.35 * edge_scores["source_score"].to_numpy()
        + 0.20 * edge_scores["target_score"].to_numpy()
    )
    edge_scores = edge_scores.sort_values(["risk_score", "pressure"], ascending=[False, False]).reset_index(drop=True)

    run_summary = load_artifacts().run_summary.set_index("run_id").loc[run_id]
    return node_scores, edge_scores, run_summary
