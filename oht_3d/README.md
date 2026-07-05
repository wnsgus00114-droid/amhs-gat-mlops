# OHT 3D Web Simulator

GIF 기반 OHT 시뮬레이션을 HTML/Three.js로 재구성한 3D 뷰어입니다.

## 생성

```bash
cd /Users/baegjunhyeon/OHT/amhs/oht_3d
python3 generate_scene_data.py \
  --run-id 1 \
  --notebook ../AMHS_realistic_sim.ipynb \
  --data-dir ../data/fab \
  --event-stride 25 \
  --max-ohts 37 \
  --output scene_data_run1.json
```

## 실행

```bash
cd /Users/baegjunhyeon/OHT/amhs/oht_3d
python3 -m http.server 8091
```

브라우저: `http://localhost:8091`

## 참고

- 현재 데이터만으로는 "CAD급 완벽 설비 치수/높이"는 불가합니다.
- 하지만 GIF에서 사용한 레이아웃 `pos` + 실제 `trail*.pickle` 이벤트를 써서 레일/OHT 시뮬레이션 형태로 재현합니다.
- CAD 수준으로 올리려면 추가 데이터가 필요합니다:
  - 설비별 크기/높이/회전
  - 레일의 실제 고도/곡률
  - 층 정보(메자닌, 클린룸 단차)
  - 설비간 물리 간격 기준
