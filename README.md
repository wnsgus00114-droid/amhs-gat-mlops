# AMHS GAT Bottleneck MLOps

AMHS(Automated Material Handling System) 시뮬레이션 데이터를 이용해 병목 노드와 병목 엣지를 분석하는 과제용 MLOps 프로젝트입니다.

이 레포는 과제 시연에 실제로 사용한 파일만 담았습니다.

- Streamlit 병목 분석 대시보드
- GAT 기반 병목 점수화 코드와 EC2용 경량 fallback
- AMHS run CSV 데이터
- OHT 3D FAB 시뮬레이션 뷰어
- Docker/Kubernetes 배포 파일

## 빠른 실행

로컬에서 바로 확인하려면 아래 명령만 실행합니다.

```bash
bash scripts/run_local.sh
```

브라우저:

```text
http://127.0.0.1:8501
```

`3D 시뮬레이션` 탭까지 같이 보이도록 `scripts/run_local.sh`가 3D 정적 서버와 Streamlit 서버를 함께 실행합니다.

## EC2 실행

EC2에 이 레포를 받은 뒤 실행합니다.

```bash
cd ~/opensource_st_4/amhs
./mlops_k8s/run_ec2_streamlit.sh
```

8501 포트를 보안 그룹에서 열었다면:

```text
http://EC2_PUBLIC_IP:8501
```

보안 그룹에서 80번 포트만 열려 있다면 Nginx 프록시를 설정합니다.

```bash
bash scripts/install_ec2_nginx.sh
```

그 다음:

```text
http://EC2_PUBLIC_IP/
```

## Kubernetes 실행

Docker 이미지를 빌드합니다.

```bash
docker build -f mlops_k8s/Dockerfile -t amhs-gat-mlops:latest .
```

kind로 테스트할 경우:

```bash
kind create cluster --name amhs-mlops-test
kind load docker-image amhs-gat-mlops:latest --name amhs-mlops-test
kubectl apply -f mlops_k8s/k8s/
kubectl -n amhs-mlops get pods,svc,hpa
kubectl -n amhs-mlops port-forward svc/amhs-gat-streamlit 8501:8501
```

HPA CPU 지표를 확인하려면 metrics-server가 필요합니다.

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
kubectl -n kube-system patch deployment metrics-server --type=json \
  -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
```

## 폴더 구조

```text
mlops_k8s/          Streamlit 앱, GAT 병목 분석, Docker/K8s 파일
pororo/             앱이 사용하는 AMHS run CSV 데이터
oht_3d/             OHT 3D FAB 시뮬레이션 정적 페이지
outputs/            Streamlit에 표시되는 혼잡 시각화 GIF
scripts/            로컬/EC2 실행 보조 스크립트
deploy/nginx/       EC2 Nginx 프록시 예시 설정
```

## GitHub 제출 제외 파일

아래 파일과 폴더는 의도적으로 포함하지 않았습니다.

- 로컬 과제 문서
- 영상 촬영용 개인 문서
- EC2 접속 키와 IP 메모
- 로컬 가상환경과 캐시 파일

## 검증된 기능

- Streamlit 앱 health check
- EC2 systemd + Nginx 프록시 배포
- kind Kubernetes Deployment/Service/HPA 적용
- 3D 시뮬레이션 iframe 렌더링
