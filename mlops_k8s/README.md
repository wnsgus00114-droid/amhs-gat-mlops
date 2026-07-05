# AMHS Streamlit MLOps App

이 폴더는 AMHS 병목 분석 Streamlit 앱과 배포 파일을 담고 있습니다.

## 주요 파일

- `app.py`: Streamlit 대시보드
- `gat_inference.py`: GAT 기반 병목 점수화와 EC2용 fallback
- `run_ec2_streamlit.sh`: EC2 실행 스크립트
- `requirements.txt`: Docker/Kubernetes용 PyTorch 포함 의존성
- `requirements_ec2.txt`: 작은 EC2 인스턴스용 경량 의존성
- `Dockerfile`: 컨테이너 이미지 빌드
- `k8s/`: Kubernetes manifest

## EC2 실행

```bash
cd ~/opensource_st_4/amhs
./mlops_k8s/run_ec2_streamlit.sh
```

기본 접속:

```text
http://EC2_PUBLIC_IP:8501
```

8501이 막혀 있으면 상위 폴더의 `scripts/install_ec2_nginx.sh`로 80번 포트 프록시를 설정합니다.

## Docker 실행

```bash
docker build -f mlops_k8s/Dockerfile -t amhs-gat-mlops:latest .
docker run --rm -p 8501:8501 amhs-gat-mlops:latest
```

## Kubernetes 실행

```bash
kubectl apply -f mlops_k8s/k8s/
kubectl -n amhs-mlops get pods,svc,hpa
kubectl -n amhs-mlops port-forward svc/amhs-gat-streamlit 8501:8501
```
