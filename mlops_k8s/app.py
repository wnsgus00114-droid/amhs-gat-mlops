from __future__ import annotations

import os

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

try:
    from .gat_inference import PROJECT_ROOT, score_run, train_gat_surrogate
except ImportError:
    from gat_inference import PROJECT_ROOT, score_run, train_gat_surrogate


st.set_page_config(page_title="AMHS GAT Bottleneck MLOps", page_icon=":factory:", layout="wide")


@st.cache_resource(show_spinner="GAT surrogate 모델을 학습하는 중입니다...")
def get_trained_artifacts():
    return train_gat_surrogate()


def _format_metric(value: float) -> str:
    return f"{value:,.2f}"


def _render_3d_simulation() -> None:
    simulation_url = os.environ.get("AMHS_3D_URL", "/oht3d/index.html")
    components.iframe(simulation_url, height=720, scrolling=False)


def main() -> None:
    trained = get_trained_artifacts()

    st.title("AMHS 병목 분석 MLOps 대시보드")
    st.caption("AMHS 시뮬레이션 로그를 기반으로 경량 GAT surrogate가 병목 노드와 엣지를 점수화합니다.")

    with st.sidebar:
        st.header("실행 설정")
        run_id = st.selectbox("분석할 run_id", trained.run_ids, index=0)
        top_k = st.slider("상위 병목 개수", min_value=5, max_value=20, value=10)

    node_scores, edge_scores, run_summary = score_run(trained, int(run_id))
    top_nodes = node_scores.head(top_k)
    top_edges = edge_scores.head(top_k)

    metric_columns = st.columns(4)
    metric_columns[0].metric("예측 1위 노드", str(top_nodes.iloc[0]["node"]))
    metric_columns[1].metric("최고 GAT 점수", _format_metric(float(top_nodes.iloc[0]["gat_score"])))
    metric_columns[2].metric("Run Duration", f"{int(run_summary['duration']):,}")
    metric_columns[3].metric("고위험 엣지", f"{top_edges.iloc[0]['edge_source']} -> {top_edges.iloc[0]['edge_target']}")

    overview_tab, node_tab, edge_tab, simulation_tab = st.tabs(["개요", "노드 분석", "엣지 분석", "3D 시뮬레이션"])

    with overview_tab:
        st.subheader("Run 요약")
        summary_df = pd.DataFrame(
            {
                "항목": ["edge_count", "avg_edge_weight", "oht_event_count", "foup_event_count", "duration"],
                "값": [
                    int(run_summary["edge_count"]),
                    float(run_summary["avg_edge_weight"]),
                    int(run_summary["oht_event_count"]),
                    int(run_summary["foup_event_count"]),
                    int(run_summary["duration"]),
                ],
            }
        )
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
        st.subheader("Top 병목 노드")
        st.bar_chart(top_nodes.set_index("node")["gat_score"], use_container_width=True)

    with node_tab:
        st.subheader("노드별 GAT 병목 점수")
        st.dataframe(
            top_nodes[["node", "gat_score", "touch_count", "inbound_traverse", "outbound_traverse", "weight_mean", "risk_level"]],
            use_container_width=True,
            hide_index=True,
        )
        st.line_chart(
            node_scores.head(20).set_index("node")[["touch_count", "gat_score"]],
            use_container_width=True,
        )

    with edge_tab:
        st.subheader("엣지별 병목 리스크")
        st.dataframe(
            top_edges[["edge_source", "edge_target", "traverse_count", "weight", "pressure", "risk_score"]],
            use_container_width=True,
            hide_index=True,
        )
        edge_chart = top_edges.assign(edge=lambda frame: frame["edge_source"] + "->" + frame["edge_target"]).set_index("edge")
        st.bar_chart(edge_chart[["pressure", "risk_score"]], use_container_width=True)

        gif_path = PROJECT_ROOT / "outputs" / "fab_oht_blue_congestion_original_layout_1600x900_no_overlap_v3.gif"
        if gif_path.exists():
            st.image(str(gif_path), caption="AMHS 혼잡 시각화", use_container_width=True)

    with simulation_tab:
        st.subheader("OHT 3D FAB Simulator")
        _render_3d_simulation()


if __name__ == "__main__":
    main()
